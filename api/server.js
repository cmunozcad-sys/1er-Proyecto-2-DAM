const express = require("express");
const session = require("express-session");
const pool = require("./db");
const sincronizador = require("./sincronizador");

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

function exigirPermisos(codigos) {
    return async (peticion, respuesta, siguiente) => {
        const usuario = peticion.session.usuario;

        if (!usuario) {
            respuesta.status(401).json({ error: "Tienes que iniciar sesión. Si ya la tenías, ciérrala y vuelve a entrar" });
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
    await conexion.query("SELECT set_config('app.id_usuario', $1, true)", [String(peticion.session.usuario.id_usuario)]);
}

function validarCustom(solicitud, observaciones) {
    if (!solicitud.club || !solicitud.contacto || !solicitud.email || !solicitud.telefono) {
        return "Faltan los datos del club";
    }
    if (!Number.isInteger(solicitud.modelo)) {
        return "Elige un modelo";
    }
    if (!/^#[0-9a-fA-F]{6}$/.test(solicitud.color)) {
        return "El color no es válido";
    }
    if (solicitud.texto && solicitud.texto.length > 40) {
        return "El texto bordado admite 40 caracteres como máximo";
    }
    if (observaciones.length > 300) {
        return "Las observaciones son demasiado largas";
    }
    if (!Array.isArray(solicitud.tallas) || solicitud.tallas.length === 0
        || !solicitud.tallas.every((linea) => Number.isInteger(linea.cantidad) && linea.cantidad > 0)) {
        return "Indica al menos un par en las tallas";
    }
    return null;
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
    VALUES ($1, $2, $6, $3, $4, $5)
    ON CONFLICT (email) DO UPDATE SET email = EXCLUDED.email
    RETURNING id_cliente`;

const insertarLinea = `
    INSERT INTO linea_pedido (id_pedido, id_variante, talla, cantidad, precio_unitario,
                              personalizacion, texto_bordado, logo_club)
    SELECT $1::int, s.id_variante, s.talla, $4::int, m.precio_base + v.precio_extra,
           $5::varchar, $6::varchar, $7::boolean
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

const consultaPedidos = `
    SELECT p.id_pedido, p.ref_odoo AS referencia, p.tipo, p.estado,
           to_char(p.fecha_pedido, 'DD/MM/YYYY HH24:MI') AS fecha,
           p.total::float AS total, c.nombre AS cliente,
           string_agg(m.nombre || ' · T' || l.talla::float || ' x' || l.cantidad, ', ' ORDER BY l.id_linea) AS articulos
      FROM pedido p
      JOIN cliente c ON c.id_cliente = p.id_cliente
      LEFT JOIN linea_pedido l ON l.id_pedido = p.id_pedido
      LEFT JOIN variante v ON v.id_variante = l.id_variante
      LEFT JOIN modelo m ON m.id_modelo = v.id_modelo
     GROUP BY p.id_pedido, c.nombre
     ORDER BY p.fecha_pedido DESC`;

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

app.post("/api/pedidos/custom", exigirPermisos(["PEDIDO_CREAR"]), async (peticion, respuesta) => {
    const solicitud = peticion.body || {};
    const contacto = "Contacto: " + solicitud.contacto;
    const observaciones = solicitud.observaciones ? contacto + " | " + solicitud.observaciones : contacto;
    const errorValidacion = validarCustom(solicitud, observaciones);

    if (errorValidacion) {
        respuesta.status(400).json({ error: errorValidacion });
        return;
    }

    const referencia = "CUS-" + Date.now();
    const conexion = await pool.connect();

    try {
        await conexion.query("BEGIN");
        await identificarUsuario(conexion, peticion);

        const nuevoCliente = await conexion.query(insertarCliente,
            ["CLI-" + Date.now(), solicitud.club, solicitud.email, solicitud.telefono, null, "CLUB"]);

        const nuevoPedido = await conexion.query(
            `INSERT INTO pedido (ref_odoo, tipo, fecha_entrega_prevista, observaciones, id_cliente, id_usuario)
             VALUES ($1, 'CUSTOM', $2, $3, $4, $5) RETURNING id_pedido`,
            [referencia, solicitud.fecha || null, observaciones, nuevoCliente.rows[0].id_cliente, peticion.session.usuario.id_usuario]);
        const idPedido = nuevoPedido.rows[0].id_pedido;

        for (const linea of solicitud.tallas) {
            const nuevaLinea = await conexion.query(insertarLinea,
                [idPedido, solicitud.modelo, linea.talla, linea.cantidad,
                    "Color: " + solicitud.color, solicitud.texto || null, Boolean(solicitud.escudo)]);

            if (nuevaLinea.rowCount === 0) {
                throw new Error("Modelo o talla inexistente");
            }
        }

        const pedido = await conexion.query("SELECT total::float AS total FROM pedido WHERE id_pedido = $1", [idPedido]);

        await conexion.query("COMMIT");
        respuesta.status(201).json({ referencia: referencia, total: pedido.rows[0].total });
    } catch (error) {
        await conexion.query("ROLLBACK");
        console.error(error.message);

        if (error.code === "23514") {
            respuesta.status(400).json({ error: "Revisa la fecha deseada: no puede ser anterior a hoy" });
        } else if (error.message.includes("inexistente")) {
            respuesta.status(400).json({ error: "Ese modelo o talla no está en la base de datos" });
        } else {
            respuesta.status(500).json({ error: "No se pudo guardar la solicitud" });
        }
    } finally {
        conexion.release();
    }
});

app.post("/api/pedidos", exigirPermisos(["PEDIDO_CREAR"]), async (peticion, respuesta) => {
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
            ["CLI-" + Date.now(), cliente.nombre, cliente.email, cliente.telefono, cliente.direccion, "PARTICULAR"]);

        const nuevoPedido = await conexion.query(
            "INSERT INTO pedido (ref_odoo, tipo, id_cliente, id_usuario) VALUES ($1, 'ESTANDAR', $2, $3) RETURNING id_pedido",
            [referencia, nuevoCliente.rows[0].id_cliente, peticion.session.usuario.id_usuario]);
        const idPedido = nuevoPedido.rows[0].id_pedido;

        for (const articulo of articulos) {
            const linea = await conexion.query(insertarLinea,
                [idPedido, articulo.id, articulo.talla, articulo.cantidad, null, null, false]);

            if (linea.rowCount === 0) {
                throw new Error("Stock insuficiente: no existe esa talla");
            }
        }

        const pedido = await conexion.query("SELECT total::float AS total FROM pedido WHERE id_pedido = $1", [idPedido]);

        await conexion.query("COMMIT");
        respuesta.status(201).json({ referencia: referencia, total: pedido.rows[0].total });
    } catch (error) {
        await conexion.query("ROLLBACK");
        console.error(error.message);

        if (error.message.includes("Stock insuficiente")) {
            respuesta.status(409).json({ error: "Alguno de los artículos ya no está disponible en esa talla" });
        } else {
            respuesta.status(500).json({ error: "No se pudo guardar el pedido" });
        }
    } finally {
        conexion.release();
    }
});

app.get("/api/pedidos", exigirPermisos(["PEDIDO_VER"]), async (peticion, respuesta) => {
    try {
        const resultado = await pool.query(consultaPedidos);
        respuesta.json(resultado.rows);
    } catch (error) {
        console.error(error.message);
        respuesta.status(500).json({ error: "No se pudieron cargar los pedidos" });
    }
});

async function cambiarEstado(peticion, respuesta, estado) {
    const id = Number(peticion.params.id);

    if (!Number.isInteger(id)) {
        respuesta.status(400).json({ error: "El pedido no es válido" });
        return;
    }

    const conexion = await pool.connect();

    try {
        await conexion.query("BEGIN");
        await identificarUsuario(conexion, peticion);

        const resultado = await conexion.query(
            "UPDATE pedido SET estado = $2 WHERE id_pedido = $1 AND estado = 'BORRADOR' RETURNING ref_odoo",
            [id, estado]);

        if (resultado.rows.length === 0) {
            await conexion.query("ROLLBACK");
            respuesta.status(409).json({ error: "Este pedido ya no está pendiente" });
            return;
        }

        await conexion.query("COMMIT");
        respuesta.json({ referencia: resultado.rows[0].ref_odoo, estado: estado });
    } catch (error) {
        await conexion.query("ROLLBACK");
        console.error(error.message);

        if (error.message.includes("Stock insuficiente")) {
            respuesta.status(409).json({ error: "No hay stock suficiente para aprobar este pedido" });
        } else {
            respuesta.status(500).json({ error: "No se pudo cambiar el estado del pedido" });
        }
    } finally {
        conexion.release();
    }
}

app.post("/api/pedidos/:id/aprobar", exigirPermisos(["PEDIDO_CONFIRMAR"]), (peticion, respuesta) => {
    cambiarEstado(peticion, respuesta, "CONFIRMADO");
});

app.post("/api/pedidos/:id/cancelar", exigirPermisos(["PEDIDO_CANCELAR"]), (peticion, respuesta) => {
    cambiarEstado(peticion, respuesta, "CANCELADO");
});

app.listen(3000, () => sincronizador.arrancar());