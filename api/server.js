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

const consultaPermisos = `
    SELECT count(*)::int AS concedidos
      FROM usuario u
      JOIN rol_permiso rp ON rp.id_rol = u.id_rol
      JOIN permiso p ON p.id_permiso = rp.id_permiso
     WHERE u.id_usuario = $1 AND u.activo AND p.codigo = ANY($2)`;

function exigirPermisos(codigos, permitirSinSesion) {
    return async (peticion, respuesta, siguiente) => {
        const usuario = peticion.session.usuario;

        if (!usuario) {
            if (permitirSinSesion) {
                siguiente();
            } else {
                respuesta.status(401).json({ error: "Tu sesión ha caducado. Cierra sesión y vuelve a entrar" });
            }
            return;
        }

        try {
            const resultado = await pool.query(consultaPermisos, [usuario.id_usuario, codigos]);

            if (resultado.rows[0].concedidos < codigos.length) {
                respuesta.status(403).json({ error: "No tienes permiso para hacer esto" });
                return;
            }
        } catch (error) {
            console.error(error.message);
            respuesta.status(500).json({ error: "No se pudieron comprobar los permisos" });
            return;
        }

        siguiente();
    };
}

async function identificarUsuario(conexion, peticion) {
    const usuario = peticion.session.usuario;
    const idUsuario = usuario ? String(usuario.id_usuario) : "";

    await conexion.query("SELECT set_config('app.id_usuario', $1, true)", [idUsuario]);
}

const consultaLogin = `
    SELECT u.id_usuario, u.username, u.nombre_completo, u.activo, r.nombre AS rol,
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
    UPDATE stock
       SET cantidad = cantidad + $3, ultima_actualizacion = now()
     WHERE talla = $2
       AND id_variante = (SELECT id_variante FROM variante
                           WHERE id_modelo = $1 AND activo
                           ORDER BY id_variante LIMIT 1)
    RETURNING id_variante, cantidad`;

const registrarReposicion = `
    INSERT INTO log_eventos (tabla, operacion, registro_id, accion, resumen, id_usuario)
    VALUES ('stock', 'UPDATE', $1, 'REPOSICION STOCK',
            jsonb_build_object('talla', $2::numeric, 'anadidos', $3::int, 'total', $4::int),
            NULLIF(current_setting('app.id_usuario', true), '')::INTEGER)`;

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
            peticion.session.usuario = { id_usuario: usuario.id_usuario };
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

app.post("/api/stock", exigirPermisos(["STOCK_REPONER"], false), async (peticion, respuesta) => {
    const { id, talla, cantidad } = peticion.body || {};

    if (!Number.isInteger(id) || !(talla >= 30 && talla <= 48)
        || !Number.isInteger(cantidad) || cantidad < 1 || cantidad > 10000) {
        respuesta.status(400).json({ error: "Los datos no son válidos" });
        return;
    }

    const conexion = await pool.connect();

    try {
        await conexion.query("BEGIN");
        await identificarUsuario(conexion, peticion);

        const resultado = await conexion.query(sumarStock, [id, talla, cantidad]);

        if (resultado.rows.length === 0) {
            await conexion.query("ROLLBACK");
            respuesta.status(404).json({ error: "Esa zapatilla o talla no está en la base de datos" });
            return;
        }

        const { id_variante, cantidad: total } = resultado.rows[0];
        await conexion.query(registrarReposicion, [id_variante, talla, cantidad, total]);

        await conexion.query("COMMIT");
        respuesta.json({ cantidad: total });
    } catch (error) {
        await conexion.query("ROLLBACK");
        console.error(error.message);
        respuesta.status(500).json({ error: "No se pudo añadir al stock" });
    } finally {
        conexion.release();
    }
});

app.post("/api/pedidos", exigirPermisos(["PEDIDO_CREAR", "PEDIDO_CONFIRMAR"], true), async (peticion, respuesta) => {
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
        await identificarUsuario(conexion, peticion);

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
