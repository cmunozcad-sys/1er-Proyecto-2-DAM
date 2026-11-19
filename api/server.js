// Servidor de la web: sirve las páginas, gestiona las sesiones, comprueba los permisos y guarda pedidos, stock y usuarios

const fs = require("fs");
const path = require("path");
const express = require("express");
const session = require("express-session");
const pool = require("./db");
const sincronizador = require("./sincronizador");

// Fichero donde se apunta la actividad de los usuarios
const carpetaLogs = process.env.LOG_DIR || path.join(__dirname, "logs");
const archivoActividad = path.join(carpetaLogs, "actividad_sneaker.txt");
fs.mkdirSync(path.dirname(archivoActividad), { recursive: true });

// Añade una línea al log: fecha | usuario | rol | acción | resultado
function registrarActividad(usuario, accion, resultado) {
    const fecha = new Date().toLocaleString("es-ES", { timeZone: "Europe/Madrid" });
    const linea = `${fecha} | ${usuario} | ${accion} | ${resultado}\n`;

    try {
        fs.appendFileSync(archivoActividad, linea);
    } catch (error) {
        console.error("No se pudo escribir en el log: " + error.message);
    }
}

// Texto 'usuario | rol' para el log
function identidad(username, rol) {
    return (username || "anónimo") + " | " + (rol || "sin rol");
}

// Identidad del usuario que tiene la sesión iniciada
function usuarioDe(peticion) {
    const usuario = peticion.session.usuario;
    return usuario ? identidad(usuario.username, usuario.rol) : identidad();
}

// Fichero JSON donde se exportan los usuarios
const carpetaExportaciones = process.env.EXPORT_DIR || path.join(__dirname, "exportaciones");
const archivoUsuarios = path.join(carpetaExportaciones, "usuarios_sneaker.json");
fs.mkdirSync(path.dirname(archivoUsuarios), { recursive: true });

// Usuarios con su rol para la exportación
const consultaExportarUsuarios = `
    SELECT u.id_usuario, u.username, u.nombre_completo, r.nombre AS rol, u.activo,
        to_char(u.fecha_creacion, 'YYYY-MM-DD HH24:MI:SS') AS fecha_creacion,
        to_char(u.ultimo_acceso, 'YYYY-MM-DD HH24:MI:SS') AS ultimo_acceso
    FROM usuario u
    JOIN rol r ON r.id_rol = u.id_rol
    ORDER BY u.id_usuario`;

// Exporta los usuarios a JSON. Escribe un .tmp, comprueba que el JSON es válido y lo renombra para no dejar el fichero a medias
async function exportarUsuarios(usuario, motivo) {
    try {
        const resultado = await pool.query(consultaExportarUsuarios);
        const datos = {
            generado: new Date().toLocaleString("es-ES", { timeZone: "Europe/Madrid" }),
            motivo: motivo,
            total: resultado.rows.length,
            usuarios: resultado.rows
        };

        const temporal = archivoUsuarios + ".tmp";
        fs.writeFileSync(temporal, JSON.stringify(datos, null, 4), "utf8");
        JSON.parse(fs.readFileSync(temporal, "utf8"));
        fs.renameSync(temporal, archivoUsuarios);
        registrarActividad(usuario, "EXPORTAR USUARIOS", "OK - " + datos.total + " usuarios (" + motivo + ")");
        return datos;
    } catch (error) {
        console.error("No se pudieron exportar los usuarios: " + error.message);
        registrarActividad(usuario, "EXPORTAR USUARIOS", "ERROR - " + error.message);
        return null;
    }
}

// Express con JSON, sesiones y la carpeta web servida como estática
const app = express();

app.use(express.json());
app.use(session({
    secret: process.env.SESSION_SECRET,
    resave: false,
    saveUninitialized: false,
    cookie: { sameSite: "lax" }
}));
app.use(express.static("web"));

// Cuántos de los permisos pedidos tiene el usuario, si está activo
const consultaPermisos = `
    SELECT count(*)::int AS concedidos
    FROM usuario u
    JOIN rol_permiso rp ON rp.id_rol = u.id_rol
    JOIN permiso p ON p.id_permiso = rp.id_permiso
    WHERE u.id_usuario = $1 AND u.activo AND p.codigo = ANY($2)`;

// Middleware: sin sesión devuelve 401 y sin los permisos 403. Si todo va bien, deja pasar a la ruta
function exigirPermisos(codigos) {
    return async (peticion, respuesta, siguiente) => {
        const usuario = peticion.session.usuario;

        const ruta = peticion.method + " " + peticion.originalUrl;

        if (!usuario) {
            registrarActividad(identidad(), "PERMISO DENEGADO " + ruta, "RECHAZADO - sin sesión");
            respuesta.status(401).json({ error: "Tienes que iniciar sesión. Si ya la tenías, ciérrala y vuelve a entrar" });
            return;
        }

        try {
            const resultado = await pool.query(consultaPermisos, [usuario.id_usuario, codigos]);

            if (resultado.rows[0].concedidos < codigos.length) {
                registrarActividad(usuarioDe(peticion), "PERMISO DENEGADO " + ruta, "RECHAZADO - falta " + codigos.join(", "));
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

// Guarda el id del usuario en la transacción para que el trigger de auditoría sepa quién hizo el cambio
async function identificarUsuario(conexion, peticion) {
    await conexion.query("SELECT set_config('app.id_usuario', $1, true)", [String(peticion.session.usuario.id_usuario)]);
}

// Valida el formulario de pedido personalizado; devuelve el error o null
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

// Valida el usuario, el nombre y la contraseña de una cuenta nueva
function validarUsuario(usuario) {
    if (!usuario.username || !/^[a-zA-Z0-9._-]{3,40}$/.test(usuario.username)) {
        return "El usuario debe tener entre 3 y 40 letras, números, puntos o guiones";
    }
    if (!usuario.nombre_completo || usuario.nombre_completo.trim() === "" || usuario.nombre_completo.length > 100) {
        return "Escribe el nombre completo (100 caracteres como máximo)";
    }
    if (!usuario.password || usuario.password.length < 8) {
        return "La contraseña debe tener al menos 8 caracteres";
    }
    return null;
}

// Busca el usuario comprobando la contraseña con crypt y saca sus permisos
const consultaLogin = `
    SELECT u.id_usuario, u.username, u.nombre_completo, u.activo, r.nombre AS rol,
        array_remove(array_agg(p.codigo), NULL) AS permisos
    FROM usuario u
    JOIN rol r ON r.id_rol = u.id_rol
    LEFT JOIN rol_permiso rp ON rp.id_rol = r.id_rol
    LEFT JOIN permiso p ON p.id_permiso = rp.id_permiso
    WHERE u.username = $1 AND u.password_hash = crypt($2, u.password_hash)
    GROUP BY u.id_usuario, r.nombre`;

// Inserta el cliente o, si ya existe ese email, devuelve el que hay
const insertarCliente = `
    INSERT INTO cliente (ref_odoo, nombre, tipo, email, telefono, direccion)
    VALUES ($1, $2, $6, $3, $4, $5)
    ON CONFLICT (email) DO UPDATE SET email = EXCLUDED.email
    RETURNING id_cliente`;

// Inserta una línea con el precio del modelo más el extra de la variante, solo si existe esa talla.
// ORDER BY id_variante hace que elija siempre la misma variante que consultaStock
const insertarLinea = `
    INSERT INTO linea_pedido (id_pedido, id_variante, talla, cantidad, precio_unitario,
                            personalizacion, texto_bordado, logo_club)
    SELECT $1::int, s.id_variante, s.talla, $4::int, m.precio_base + v.precio_extra,
        $5::varchar, $6::varchar, $7::boolean
    FROM stock s
    JOIN variante v ON v.id_variante = s.id_variante
    JOIN modelo m ON m.id_modelo = v.id_modelo
    WHERE m.id_modelo = $2 AND s.talla = $3 AND m.activo AND v.activo
    ORDER BY s.id_variante
    LIMIT 1`;

// Pares que quedan de un modelo en una talla, en la misma variante que elige insertarLinea
const consultaStock = `
    SELECT s.cantidad
    FROM stock s
    JOIN variante v ON v.id_variante = s.id_variante
    JOIN modelo m ON m.id_modelo = v.id_modelo
    WHERE m.id_modelo = $1 AND s.talla = $2 AND m.activo AND v.activo
    ORDER BY s.id_variante
    LIMIT 1`;

// Suma pares al stock de la primera variante activa del modelo en esa talla
const sumarStock = `
    UPDATE stock
    SET cantidad = cantidad + $3, ultima_actualizacion = now()
    WHERE talla = $2
    AND id_variante = (SELECT id_variante FROM variante
                        WHERE id_modelo = $1 AND activo
                        ORDER BY id_variante LIMIT 1)
    RETURNING id_variante, cantidad`;

// Apunta la reposición en log_eventos
const registrarReposicion = `
    INSERT INTO log_eventos (tabla, operacion, registro_id, accion, resumen, id_usuario)
    VALUES ('stock', 'UPDATE', $1, 'REPOSICION STOCK',
            jsonb_build_object('talla', $2::numeric, 'anadidos', $3::int, 'total', $4::int),
            NULLIF(current_setting('app.id_usuario', true), '')::INTEGER)`;

// Pedidos con cliente y artículos; el WHERE depende de los filtros
function consultaPedidos(where) {
    return `
    SELECT p.id_pedido, p.ref_odoo AS referencia, p.tipo, p.estado,
        to_char(p.fecha_pedido, 'DD/MM/YYYY HH24:MI') AS fecha,
        p.total::float AS total, c.nombre AS cliente,
        string_agg(m.nombre || ' · T' || l.talla::float || ' x' || l.cantidad, ', ' ORDER BY l.id_linea) AS articulos
    FROM pedido p
    JOIN cliente c ON c.id_cliente = p.id_cliente
    LEFT JOIN linea_pedido l ON l.id_pedido = p.id_pedido
    LEFT JOIN variante v ON v.id_variante = l.id_variante
    LEFT JOIN modelo m ON m.id_modelo = v.id_modelo
    ${where}
    GROUP BY p.id_pedido, c.nombre
    ORDER BY p.fecha_pedido DESC`;
}

// Valores permitidos en los filtros
const estadosValidos = ["BORRADOR", "CONFIRMADO", "CANCELADO"];
const formatoFecha = /^\d{4}-\d{2}-\d{2}$/;

// Construye el WHERE con parámetros ($1, $2...) a partir de los filtros de la URL, para evitar inyección SQL
function filtrosPedidos(consulta) {
    const condiciones = [];
    const valores = [];
    const descripcion = [];

    if (consulta.cliente) {
        valores.push("%" + consulta.cliente + "%");
        condiciones.push(`c.nombre ILIKE $${valores.length}`);
        descripcion.push("cliente=" + consulta.cliente);
    }

    if (estadosValidos.includes(consulta.estado)) {
        valores.push(consulta.estado);
        condiciones.push(`p.estado = $${valores.length}`);
        descripcion.push("estado=" + consulta.estado);
    }

    if (formatoFecha.test(consulta.desde || "")) {
        valores.push(consulta.desde);
        condiciones.push(`p.fecha_pedido >= $${valores.length}::date`);
        descripcion.push("desde=" + consulta.desde);
    }

    if (formatoFecha.test(consulta.hasta || "")) {
        valores.push(consulta.hasta);
        condiciones.push(`p.fecha_pedido < $${valores.length}::date + 1`);
        descripcion.push("hasta=" + consulta.hasta);
    }

    const where = condiciones.length > 0 ? "WHERE " + condiciones.join(" AND ") : "";
    const filtros = descripcion.length > 0 ? descripcion.join(", ") : "sin filtros";
    return { where, valores, filtros };
}

// Indicadores del panel: total de pedidos, pares solicitados sin contar cancelados e importe de ventas confirmadas
const consultaIndicadores = `
    SELECT
        (SELECT COUNT(*) FROM pedido)::int AS total_pedidos,
        (SELECT COALESCE(SUM(l.cantidad), 0)
        FROM linea_pedido l
        JOIN pedido p ON p.id_pedido = l.id_pedido
        WHERE p.estado <> 'CANCELADO')::int AS pares_solicitados,
        (SELECT COALESCE(SUM(total), 0)
        FROM pedido
        WHERE estado = 'CONFIRMADO')::float AS importe_ventas`;

// Número de pedidos de cada estado
const consultaPorEstado = `SELECT estado, COUNT(*)::int AS num_pedidos FROM pedido GROUP BY estado`;

// Convierte los pedidos a CSV separado por ; con BOM para que Excel lea bien los acentos
function pedidosACsv(filas) {
    const columnas = ["referencia", "fecha", "cliente", "tipo", "estado", "total", "articulos"];
    const escapar = (valor) => `"${String(valor ?? "").replace(/"/g, '""')}"`;
    const lineas = filas.map((fila) => columnas.map((columna) => escapar(fila[columna])).join(";"));

    return "\uFEFF" + [columnas.join(";"), ...lineas].join("\r\n");
}

// Lista de usuarios para la gestión
const consultaUsuarios = `
    SELECT u.id_usuario, u.username, u.nombre_completo, u.activo, u.id_rol, r.nombre AS rol,
        to_char(u.ultimo_acceso, 'DD/MM/YYYY HH24:MI') AS ultimo_acceso
    FROM usuario u
    JOIN rol r ON r.id_rol = u.id_rol
    ORDER BY u.id_usuario`;

// Crea un usuario con la contraseña cifrada (bcrypt)
const insertarUsuario = `
    INSERT INTO usuario (username, password_hash, nombre_completo, id_rol)
    VALUES ($1, crypt($2, gen_salt('bf')), $3, $4)
    RETURNING id_usuario, username`;

// Registro desde la web: la cuenta nueva siempre es Comercial
const registrarComercial = `
    INSERT INTO usuario (username, password_hash, nombre_completo, id_rol)
    SELECT $1, crypt($2, gen_salt('bf')), $3, id_rol FROM rol WHERE nombre = 'Comercial'
    RETURNING id_usuario, username`;

// POST /api/login: comprueba usuario y contraseña y, si está activo, guarda la sesión
app.post("/api/login", async (peticion, respuesta) => {
    const { username, password } = peticion.body || {};

    try {
        const resultado = await pool.query(consultaLogin, [username, password]);

        if (resultado.rows.length === 0) {
            registrarActividad(identidad(username), "LOGIN", "RECHAZADO - usuario o contraseña incorrectos");
            respuesta.status(401).json({ error: "Usuario o contraseña incorrectos" });
            return;
        }

        const usuario = resultado.rows[0];
        if (usuario.activo) {
            await pool.query("UPDATE usuario SET ultimo_acceso = now() WHERE username = $1", [username]);
            peticion.session.usuario = { id_usuario: usuario.id_usuario, username: usuario.username, rol: usuario.rol };
            registrarActividad(identidad(usuario.username, usuario.rol), "LOGIN", "OK");
        } else {
            registrarActividad(identidad(usuario.username, usuario.rol), "LOGIN", "RECHAZADO - usuario desactivado");
        }

        respuesta.json(usuario);
    } catch (error) {
        console.error(error.message);
        registrarActividad(identidad(username), "LOGIN", "ERROR - " + error.message);
        respuesta.status(500).json({ error: "No se pudo comprobar el usuario" });
    }
});

// POST /api/logout: cierra la sesión
app.post("/api/logout", (peticion, respuesta) => {
    peticion.session.destroy(() => {
        respuesta.json({ estado: "ok" });
    });
});

// POST /api/registro: crea una cuenta Comercial y actualiza el JSON de usuarios
app.post("/api/registro", async (peticion, respuesta) => {
    const usuario = peticion.body || {};
    const errorValidacion = validarUsuario(usuario);

    if (errorValidacion) {
        respuesta.status(400).json({ error: errorValidacion });
        return;
    }

    try {
        const resultado = await pool.query(registrarComercial,
            [usuario.username, usuario.password, usuario.nombre_completo.trim()]);

        if (resultado.rows.length === 0) {
            respuesta.status(500).json({ error: "No existe el rol Comercial en la base de datos" });
            return;
        }

        await exportarUsuarios(identidad(resultado.rows[0].username, "Comercial"), "registro de " + resultado.rows[0].username);
        respuesta.status(201).json(resultado.rows[0]);
    } catch (error) {
        console.error(error.message);

        if (error.code === "23505") {
            respuesta.status(409).json({ error: "Ese nombre de usuario ya está cogido" });
        } else {
            respuesta.status(500).json({ error: "No se pudo crear la cuenta" });
        }
    }
});

// POST /api/stock: repone stock en una transacción y lo apunta en la auditoría (permiso STOCK_REPONER)
app.post("/api/stock",exigirPermisos(["STOCK_REPONER"], false), async (peticion, respuesta) => {
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

// GET /api/stock: pares que quedan de un modelo en una talla (lo usa el carrito antes de comprar)
app.get("/api/stock", async (peticion, respuesta) => {
    const id = Number(peticion.query.id);
    const talla = Number(peticion.query.talla);

    if (!Number.isInteger(id) || !(talla >= 30 && talla <= 48)) {
        respuesta.status(400).json({ error: "Los datos no son válidos" });
        return;
    }

    try {
        const resultado = await pool.query(consultaStock, [id, talla]);
        respuesta.json({ cantidad: resultado.rows.length > 0 ? resultado.rows[0].cantidad : 0 });
    } catch (error) {
        console.error(error.message);
        respuesta.status(500).json({ error: "No se pudo consultar el stock" });
    }
});

// POST /api/pedidos/custom: guarda un pedido personalizado (cliente, pedido CUS- y líneas) en una sola transacción
app.post("/api/pedidos/custom", exigirPermisos(["PEDIDO_CREAR"]), async (peticion, respuesta) => {
    const solicitud = peticion.body || {};
    const contacto = "Contacto: " + solicitud.contacto;
    const observaciones = solicitud.observaciones ? contacto + " | " + solicitud.observaciones : contacto;
    const errorValidacion = validarCustom(solicitud, observaciones);

    if (errorValidacion) {
        registrarActividad(usuarioDe(peticion), "CREAR PEDIDO CUSTOM", "RECHAZADO - " + errorValidacion);
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

        // Una línea por talla; si alguna no existe se deshace todo
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
        registrarActividad(usuarioDe(peticion), "CREAR PEDIDO CUSTOM", "OK - " + referencia + " por " + pedido.rows[0].total + " €");
        respuesta.status(201).json({ referencia: referencia, total: pedido.rows[0].total });
    } catch (error) {
        await conexion.query("ROLLBACK");
        console.error(error.message);
        registrarActividad(usuarioDe(peticion), "CREAR PEDIDO CUSTOM", "ERROR - " + error.message);

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

// POST /api/pedidos: guarda el pedido del carrito (WEB-) en una transacción
app.post("/api/pedidos", exigirPermisos(["PEDIDO_CREAR"]), async (peticion, respuesta) => {
    const { cliente, articulos } = peticion.body || {};

    if (!cliente || !cliente.nombre || !cliente.email || !cliente.telefono || !cliente.direccion
        || !Array.isArray(articulos) || articulos.length === 0) {
        registrarActividad(usuarioDe(peticion), "CREAR PEDIDO", "RECHAZADO - faltan datos del pedido");
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
            // Antes de guardar la línea se comprueba que haya pares suficientes; si no, se deshace todo el pedido
            const stock = await conexion.query(consultaStock, [articulo.id, articulo.talla]);

            if (stock.rows.length === 0 || stock.rows[0].cantidad < articulo.cantidad) {
                throw new Error("Stock insuficiente: no hay pares suficientes de esa talla");
            }

            const linea = await conexion.query(insertarLinea,
                [idPedido, articulo.id, articulo.talla, articulo.cantidad, null, null, false]);

            if (linea.rowCount === 0) {
                throw new Error("Stock insuficiente: no existe esa talla");
            }
        }

        const pedido = await conexion.query("SELECT total::float AS total FROM pedido WHERE id_pedido = $1", [idPedido]);

        await conexion.query("COMMIT");
        registrarActividad(usuarioDe(peticion), "CREAR PEDIDO", "OK - " + referencia + " por " + pedido.rows[0].total + " €");
        respuesta.status(201).json({ referencia: referencia, total: pedido.rows[0].total });
    } catch (error) {
        await conexion.query("ROLLBACK");
        console.error(error.message);
        registrarActividad(usuarioDe(peticion), "CREAR PEDIDO", "ERROR - " + error.message);

        if (error.message.includes("Stock insuficiente")) {
            respuesta.status(409).json({ error: "No hay stock suficiente de alguno de los artículos en esa talla" });
        } else {
            respuesta.status(500).json({ error: "No se pudo guardar el pedido" });
        }
    } finally {
        conexion.release();
    }
});

// GET /api/pedidos: lista los pedidos con los filtros del panel
app.get("/api/pedidos", exigirPermisos(["PEDIDO_VER"]), async (peticion, respuesta) => {
    const { where, valores, filtros } = filtrosPedidos(peticion.query);

    const accion = peticion.query.limpiar ? "LIMPIAR FILTROS" : "CONSULTA PEDIDOS (" + filtros + ")";

    try {
        const resultado = await pool.query(consultaPedidos(where), valores);
        registrarActividad(usuarioDe(peticion), accion, "OK - " + resultado.rows.length + " pedidos");
        respuesta.json(resultado.rows);
    } catch (error) {
        console.error(error.message);
        registrarActividad(usuarioDe(peticion), accion, "ERROR - " + error.message);
        respuesta.status(500).json({ error: "No se pudieron cargar los pedidos" });
    }
});

// GET /api/pedidos/csv: descarga en CSV los pedidos filtrados
app.get("/api/pedidos/csv", exigirPermisos(["EXPORTAR_CSV"]), async (peticion, respuesta) => {
    const { where, valores, filtros } = filtrosPedidos(peticion.query);

    try {
        const resultado = await pool.query(consultaPedidos(where), valores);
        registrarActividad(usuarioDe(peticion), "EXPORTAR CSV (" + filtros + ")", "OK - " + resultado.rows.length + " pedidos");
        respuesta.setHeader("Content-Type", "text/csv; charset=utf-8");
        respuesta.setHeader("Content-Disposition", 'attachment; filename="pedidos_filtrados.csv"');
        respuesta.send(pedidosACsv(resultado.rows));
    } catch (error) {
        console.error(error.message);
        registrarActividad(usuarioDe(peticion), "EXPORTAR CSV (" + filtros + ")", "ERROR - " + error.message);
        respuesta.status(500).json({ error: "No se pudo exportar el CSV" });
    }
});

// GET /api/indicadores: datos del panel de indicadores
app.get("/api/indicadores", exigirPermisos(["INDICADORES_VER"]), async (peticion, respuesta) => {
    try {
        const indicadores = await pool.query(consultaIndicadores);
        const porEstado = await pool.query(consultaPorEstado);
        const datos = indicadores.rows[0];

        datos.por_estado = {};
        porEstado.rows.forEach((fila) => {
            datos.por_estado[fila.estado] = fila.num_pedidos;
        });

        registrarActividad(usuarioDe(peticion), "CONSULTA INDICADORES", "OK - " + datos.total_pedidos + " pedidos, "
            + datos.pares_solicitados + " pares, " + datos.importe_ventas + " €");
        respuesta.json(datos);
    } catch (error) {
        console.error(error.message);
        registrarActividad(usuarioDe(peticion), "CONSULTA INDICADORES", "ERROR - " + error.message);
        respuesta.status(500).json({ error: "No se pudieron cargar los indicadores" });
    }
});

// Aprueba o cancela un pedido. Solo cambia si está en BORRADOR; el trigger de stock lo rechaza si no hay pares suficientes
async function cambiarEstado(peticion, respuesta, estado) {
    const id = Number(peticion.params.id);
    const accion = (estado === "CONFIRMADO" ? "APROBAR PEDIDO " : "CANCELAR PEDIDO ") + peticion.params.id;

    if (!Number.isInteger(id)) {
        registrarActividad(usuarioDe(peticion), accion, "RECHAZADO - el pedido no es válido");
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
            registrarActividad(usuarioDe(peticion), accion, "RECHAZADO - el pedido ya no está pendiente");
            respuesta.status(409).json({ error: "Este pedido ya no está pendiente" });
            return;
        }

        await conexion.query("COMMIT");
        registrarActividad(usuarioDe(peticion), accion, "OK - " + resultado.rows[0].ref_odoo + " pasa a " + estado);
        respuesta.json({ referencia: resultado.rows[0].ref_odoo, estado: estado });
    } catch (error) {
        await conexion.query("ROLLBACK");
        console.error(error.message);
        registrarActividad(usuarioDe(peticion), accion, "ERROR - " + error.message);

        if (error.message.includes("Stock insuficiente")) {
            respuesta.status(409).json({ error: "No hay stock suficiente para aprobar este pedido" });
        } else {
            respuesta.status(500).json({ error: "No se pudo cambiar el estado del pedido" });
        }
    } finally {
        conexion.release();
    }
}

// POST /api/pedidos/:id/aprobar y /cancelar
app.post("/api/pedidos/:id/aprobar", exigirPermisos(["PEDIDO_CONFIRMAR"]), (peticion, respuesta) => {
    cambiarEstado(peticion, respuesta, "CONFIRMADO");
});

app.post("/api/pedidos/:id/cancelar", exigirPermisos(["PEDIDO_CANCELAR"]), (peticion, respuesta) => {
    cambiarEstado(peticion, respuesta, "CANCELADO");
});

// GET /api/roles: roles para el desplegable de usuarios
app.get("/api/roles", exigirPermisos(["USUARIOS_GESTIONAR"]), async (peticion, respuesta) => {
    try {
        const resultado = await pool.query("SELECT id_rol, nombre FROM rol ORDER BY id_rol");
        registrarActividad(usuarioDe(peticion), "CONSULTA ROLES", "OK - " + resultado.rows.length + " roles");
        respuesta.json(resultado.rows);
    } catch (error) {
        console.error(error.message);
        registrarActividad(usuarioDe(peticion), "CONSULTA ROLES", "ERROR - " + error.message);
        respuesta.status(500).json({ error: "No se pudieron cargar los roles" });
    }
});

// GET /api/usuarios: lista de usuarios
app.get("/api/usuarios", exigirPermisos(["USUARIOS_GESTIONAR"]), async (peticion, respuesta) => {
    try {
        const resultado = await pool.query(consultaUsuarios);
        registrarActividad(usuarioDe(peticion), "CONSULTA USUARIOS", "OK - " + resultado.rows.length + " usuarios");
        respuesta.json(resultado.rows);
    } catch (error) {
        console.error(error.message);
        registrarActividad(usuarioDe(peticion), "CONSULTA USUARIOS", "ERROR - " + error.message);
        respuesta.status(500).json({ error: "No se pudieron cargar los usuarios" });
    }
});

// POST /api/usuarios: crea un usuario con el rol elegido
app.post("/api/usuarios", exigirPermisos(["USUARIOS_GESTIONAR"]), async (peticion, respuesta) => {
    const usuario = peticion.body || {};
    const errorValidacion = validarUsuario(usuario);

    if (errorValidacion) {
        respuesta.status(400).json({ error: errorValidacion });
        return;
    }

    if (!Number.isInteger(usuario.id_rol)) {
        respuesta.status(400).json({ error: "Elige un rol" });
        return;
    }

    try {
        const resultado = await pool.query(insertarUsuario,
            [usuario.username, usuario.password, usuario.nombre_completo.trim(), usuario.id_rol]);
        await exportarUsuarios(usuarioDe(peticion), "alta de " + resultado.rows[0].username);
        respuesta.status(201).json(resultado.rows[0]);
    } catch (error) {
        console.error(error.message);

        if (error.code === "23505") {
            respuesta.status(409).json({ error: "Ya existe un usuario con ese nombre" });
        } else if (error.code === "23503") {
            respuesta.status(400).json({ error: "Ese rol no existe" });
        } else {
            respuesta.status(500).json({ error: "No se pudo crear el usuario" });
        }
    }
});

// Lee el id de la URL y no deja que un usuario se modifique a sí mismo
function leerIdUsuario(peticion, respuesta) {
    const id = Number(peticion.params.id);

    if (!Number.isInteger(id)) {
        respuesta.status(400).json({ error: "El usuario no es válido" });
        return null;
    }

    if (id === peticion.session.usuario.id_usuario) {
        respuesta.status(400).json({ error: "No puedes modificar tu propio usuario" });
        return null;
    }

    return id;
}

// POST /api/usuarios/:id/rol: cambia el rol
app.post("/api/usuarios/:id/rol", exigirPermisos(["USUARIOS_GESTIONAR"]), async (peticion, respuesta) => {
    const id = leerIdUsuario(peticion, respuesta);
    const { id_rol } = peticion.body || {};

    if (id === null) {
        return;
    }

    if (!Number.isInteger(id_rol)) {
        respuesta.status(400).json({ error: "Elige un rol" });
        return;
    }

    try {
        const resultado = await pool.query(
            "UPDATE usuario SET id_rol = $2 WHERE id_usuario = $1 RETURNING id_rol", [id, id_rol]);

        if (resultado.rows.length === 0) {
            respuesta.status(404).json({ error: "Ese usuario no existe" });
            return;
        }

        await exportarUsuarios(usuarioDe(peticion), "cambio de rol del usuario " + id);
        respuesta.json(resultado.rows[0]);
    } catch (error) {
        console.error(error.message);

        if (error.code === "23503") {
            respuesta.status(400).json({ error: "Ese rol no existe" });
        } else {
            respuesta.status(500).json({ error: "No se pudo cambiar el rol" });
        }
    }
});

// POST /api/usuarios/:id/desactivar: desactiva el usuario sin borrarlo
app.post("/api/usuarios/:id/desactivar", exigirPermisos(["USUARIOS_GESTIONAR"]), async (peticion, respuesta) => {
    const id = leerIdUsuario(peticion, respuesta);

    if (id === null) {
        return;
    }

    try {
        const resultado = await pool.query(
            "UPDATE usuario SET activo = false WHERE id_usuario = $1 RETURNING activo", [id]);

        if (resultado.rows.length === 0) {
            respuesta.status(404).json({ error: "Ese usuario no existe" });
            return;
        }

        await exportarUsuarios(usuarioDe(peticion), "desactivación del usuario " + id);
        respuesta.json(resultado.rows[0]);
    } catch (error) {
        console.error(error.message);
        respuesta.status(500).json({ error: "No se pudo desactivar el usuario" });
    }
});

// POST /api/usuarios/exportar: exportación manual a JSON
app.post("/api/usuarios/exportar", exigirPermisos(["USUARIOS_EXPORTAR"]), async (peticion, respuesta) => {
    const datos = await exportarUsuarios(usuarioDe(peticion), "exportación manual");

    if (!datos) {
        respuesta.status(500).json({ error: "No se pudieron exportar los usuarios" });
        return;
    }

    respuesta.json(datos);
});

// Arranca en el puerto 3000 y pone en marcha el sincronizador con Odoo
app.listen(3000, () => sincronizador.arrancar());