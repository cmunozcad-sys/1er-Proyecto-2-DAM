const express = require("express");
const session = require("express-session");
const pool = require("./db");

const app = express();

app.use(express.json());
app.use(session({
    secret: process.env.SESSION_SECRET,
    resave: false,
    saveUninitialized: false,
    cookie: { sameSite: "lax" }
}));
app.use(express.static("web"));

function exigirAdmin(peticion, respuesta, siguiente) {
    const usuario = peticion.session.usuario;

    if (!usuario) {
        respuesta.status(401).json({ error: "Tu sesión ha caducado. Cierra sesión y vuelve a entrar" });
        return;
    }

    if (usuario.rol !== "Administrador") {
        respuesta.status(403).json({ error: "Solo un administrador puede hacer esto" });
        return;
    }

    siguiente();
}

const consultaLogin = `
    SELECT u.username, u.nombre_completo, u.activo, r.nombre AS rol,
           array_remove(array_agg(p.codigo), NULL) AS permisos
      FROM usuario u
      JOIN rol r ON r.id_rol = u.id_rol
      LEFT JOIN rol_permiso rp ON rp.id_rol = r.id_rol
      LEFT JOIN permiso p ON p.id_permiso = rp.id_permiso
     WHERE u.username = $1 AND u.password_hash = crypt($2, u.password_hash)
     GROUP BY u.id_usuario, r.nombre`;

const insertarCliente = `
    INSERT INTO cliente (ref_odoo, nombre, tipo, email, telefono, direccion)
    VALUES ($1, $2, 'PARTICULAR', $3, $4, $5)
    ON CONFLICT (email) DO UPDATE SET email = EXCLUDED.email
    RETURNING id_cliente`;

const insertarLinea = `
    INSERT INTO linea_pedido (id_pedido, id_variante, talla, cantidad, precio_unitario)
    SELECT $1::int, s.id_variante, s.talla, $4::int, m.precio_base + v.precio_extra
      FROM stock s
      JOIN variante v ON v.id_variante = s.id_variante
      JOIN modelo m ON m.id_modelo = v.id_modelo
     WHERE m.id_modelo = $2 AND s.talla = $3 AND m.activo AND v.activo
     LIMIT 1`;

const sumarStock = `
    INSERT INTO stock (id_variante, talla, cantidad)
    SELECT v.id_variante, $2::numeric, $3::int
      FROM variante v
     WHERE v.id_modelo = $1 AND v.activo
     LIMIT 1
    ON CONFLICT (id_variante, talla)
    DO UPDATE SET cantidad = stock.cantidad + EXCLUDED.cantidad, ultima_actualizacion = now()
    RETURNING cantidad`;

app.post("/api/login", async (peticion, respuesta) => {
    const { username, password } = peticion.body || {};

    try {
        const resultado = await pool.query(consultaLogin, [username, password]);

        if (resultado.rows.length === 0) {
            respuesta.status(401).json({ error: "Usuario o contraseña incorrectos" });
            return;
        }

        const usuario = resultado.rows[0];
        if (usuario.activo) {
            await pool.query("UPDATE usuario SET ultimo_acceso = now() WHERE username = $1", [username]);
            peticion.session.usuario = { username: usuario.username, rol: usuario.rol };
        }

        respuesta.json(usuario);
    } catch (error) {
        console.error(error.message);
        respuesta.status(500).json({ error: "No se pudo comprobar el usuario" });
    }
});

app.post("/api/logout", (peticion, respuesta) => {
    peticion.session.destroy(() => {
        respuesta.json({ estado: "ok" });
    });
});

app.post("/api/stock", exigirAdmin, async (peticion, respuesta) => {
    const { id, talla, cantidad } = peticion.body || {};

    if (!Number.isInteger(id) || !(talla >= 30 && talla <= 48)
        || !Number.isInteger(cantidad) || cantidad < 1 || cantidad > 10000) {
        respuesta.status(400).json({ error: "Los datos no son válidos" });
        return;
    }

    try {
        const resultado = await pool.query(sumarStock, [id, talla, cantidad]);

        if (resultado.rows.length === 0) {
            respuesta.status(404).json({ error: "Esa zapatilla no está en la base de datos" });
            return;
        }

        respuesta.json({ cantidad: resultado.rows[0].cantidad });
    } catch (error) {
        console.error(error.message);
        respuesta.status(500).json({ error: "No se pudo añadir al stock" });
    }
});

app.post("/api/pedidos", async (peticion, respuesta) => {
    const { cliente, articulos } = peticion.body || {};

    if (!cliente || !cliente.nombre || !cliente.email || !cliente.telefono || !cliente.direccion
        || !Array.isArray(articulos) || articulos.length === 0) {
        respuesta.status(400).json({ error: "Faltan datos del pedido" });
        return;
    }

    const referencia = "WEB-" + Date.now();
    const conexion = await pool.connect();

    try {
        await conexion.query("BEGIN");

        const nuevoCliente = await conexion.query(insertarCliente,
            ["CLI-" + Date.now(), cliente.nombre, cliente.email, cliente.telefono, cliente.direccion]);

        const nuevoPedido = await conexion.query(
            "INSERT INTO pedido (ref_odoo, tipo, id_cliente) VALUES ($1, 'ESTANDAR', $2) RETURNING id_pedido",
            [referencia, nuevoCliente.rows[0].id_cliente]);
        const idPedido = nuevoPedido.rows[0].id_pedido;

        for (const articulo of articulos) {
            const linea = await conexion.query(insertarLinea, [idPedido, articulo.id, articulo.talla, articulo.cantidad]);

            if (linea.rowCount === 0) {
                throw new Error("Stock insuficiente: no existe esa talla");
            }
        }

        const confirmado = await conexion.query(
            "UPDATE pedido SET estado = 'CONFIRMADO' WHERE id_pedido = $1 RETURNING total::float AS total",
            [idPedido]);

        await conexion.query("COMMIT");
        respuesta.status(201).json({ referencia: referencia, total: confirmado.rows[0].total });
    } catch (error) {
        await conexion.query("ROLLBACK");
        console.error(error.message);

        if (error.message.includes("Stock insuficiente")) {
            respuesta.status(409).json({ error: "No queda stock suficiente de algún artículo" });
        } else {
            respuesta.status(500).json({ error: "No se pudo guardar el pedido" });
        }
    } finally {
        conexion.release();
    }
});

app.listen(3000);
