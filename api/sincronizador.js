// Envía a Odoo como presupuestos los pedidos de la web que se confirman o se cancelan

const pool = require("./db");
const odoo = require("./odoo");

// Intentos máximos por pedido y bandera para que no se solapen dos pasadas
const MAX_INTENTOS = 5;
let trabajando = false;

// Pedidos confirmados o cancelados pendientes de enviar o con error, con menos de 5 intentos
const consultaPendientes = `
    SELECT p.id_pedido, p.ref_odoo, p.estado, p.observaciones,
        c.ref_odoo AS ref_cliente, c.nombre, c.email, c.telefono, c.direccion, c.tipo
    FROM pedido p
    JOIN cliente c ON c.id_cliente = p.id_cliente
    WHERE p.estado IN ('CONFIRMADO', 'CANCELADO')
    AND p.estado_odoo IN ('PENDIENTE', 'ERROR')
    AND p.intentos_odoo < $1
    ORDER BY p.id_pedido`;

// Líneas de un pedido con la referencia y el nombre del modelo
const consultaLineas = `
    SELECT l.talla::float AS talla, l.cantidad, l.precio_unitario::float AS precio,
        l.personalizacion, l.texto_bordado, m.ref_odoo AS ref_modelo, m.nombre AS modelo
    FROM linea_pedido l
    JOIN variante v ON v.id_variante = l.id_variante
    JOIN modelo m ON m.id_modelo = v.id_modelo
    WHERE l.id_pedido = $1
    ORDER BY l.id_linea`;

// Busca el cliente en Odoo por referencia y luego por email; si no está, lo crea
async function buscarOCrearCliente(pedido) {
    let idCliente = await odoo.buscarUno("res.partner", [["ref", "=", pedido.ref_cliente]]);

    if (!idCliente && pedido.email) {
        idCliente = await odoo.buscarUno("res.partner", [["email", "=", pedido.email]]);
    }
    if (!idCliente) {
        idCliente = await odoo.ejecutar("res.partner", "create", [{
            name: pedido.nombre,
            ref: pedido.ref_cliente,
            email: pedido.email,
            phone: pedido.telefono,
            street: pedido.direccion,
            is_company: pedido.tipo !== "PARTICULAR"
        }]);
    }
    return idCliente;
}

// Busca la variante por código o nombre del modelo y la talla; si el producto no tiene tallas, sin ella
async function buscarProducto(linea) {
    const porCodigo = ["product_tmpl_id.default_code", "=", linea.ref_modelo];
    const porNombre = ["product_tmpl_id.name", "=", linea.modelo];
    const conTalla = ["product_template_attribute_value_ids.name", "=", String(linea.talla)];
    const sinTallas = ["product_tmpl_id.attribute_line_ids", "=", false];

    for (const filtroTalla of [conTalla, sinTallas]) {
        for (const filtroProducto of [porCodigo, porNombre]) {
            const idProducto = await odoo.buscarUno("product.product", [filtroProducto, filtroTalla]);

            if (idProducto) {
                return idProducto;
            }
        }
    }
    throw new Error("El producto " + linea.ref_modelo + " talla " + linea.talla + " no existe en Odoo");
}

// Descripción de la línea con modelo, talla, personalización y bordado
function descripcionLinea(linea) {
    const partes = [linea.modelo + " (talla " + linea.talla + ")"];

    if (linea.personalizacion) {
        partes.push(linea.personalizacion);
    }
    if (linea.texto_bordado) {
        partes.push("Bordado: " + linea.texto_bordado);
    }
    return partes.join(" | ");
}

// Crea el presupuesto (sale.order) en Odoo con todas sus líneas
async function crearPedido(pedido) {
    const idCliente = await buscarOCrearCliente(pedido);
    const lineas = (await pool.query(consultaLineas, [pedido.id_pedido])).rows;
    const lineasOdoo = [];

    for (const linea of lineas) {
        // [0, 0, {...}] es la forma de Odoo de crear una línea nueva dentro del pedido
        lineasOdoo.push([0, 0, {
            product_id: await buscarProducto(linea),
            name: descripcionLinea(linea),
            product_uom_qty: linea.cantidad,
            price_unit: linea.precio
        }]);
    }

    return odoo.ejecutar("sale.order", "create", [{
        partner_id: idCliente,
        client_order_ref: pedido.ref_odoo,
        origin: "Web DACA",
        note: pedido.observaciones || "",
        order_line: lineasOdoo
    }]);
}

// Envía un pedido sin duplicarlo: si ya existe con esa referencia lo reutiliza; después lo confirma o lo cancela
async function enviarPedido(pedido) {
    const referencia = ["client_order_ref", "=", pedido.ref_odoo];
    let idOdoo = await odoo.buscarUno("sale.order", [referencia]);

    if (!idOdoo) {
        idOdoo = await crearPedido(pedido);
    }

    if (pedido.estado === "CONFIRMADO") {
        const sinConfirmar = await odoo.buscarUno("sale.order", [referencia, ["state", "in", ["draft", "sent"]]]);

        if (sinConfirmar) {
            await odoo.ejecutar("sale.order", "action_confirm", [[idOdoo]]);
        }
    } else {
        const sinCancelar = await odoo.buscarUno("sale.order", [referencia, ["state", "!=", "cancel"]]);

        if (sinCancelar) {
            await odoo.ejecutar("sale.order", "action_cancel", [[idOdoo]], { context: { disable_cancel_warning: true } });
        }
    }
    return idOdoo;
}

// Una pasada: coge los pendientes, se conecta a Odoo y envía cada uno guardando el resultado en PostgreSQL
async function sincronizar() {
    if (trabajando) {
        return;
    }
    trabajando = true;

    try {
        const pendientes = (await pool.query(consultaPendientes, [MAX_INTENTOS])).rows;

        if (pendientes.length === 0) {
            return;
        }

        try {
            // Si Odoo no responde no cuenta como intento y se vuelve a probar en la siguiente pasada
            await odoo.conectar();
        } catch (error) {
            console.error("Odoo no disponible, se reintentará: " + error.message);
            return;
        }

        for (const pedido of pendientes) {
            try {
                // Si va bien se marca SINCRONIZADO con el id de Odoo; si falla, ERROR con el mensaje
                const idOdoo = await enviarPedido(pedido);
                await pool.query(
                    `UPDATE pedido SET estado_odoo = 'SINCRONIZADO', odoo_id = $2, error_odoo = NULL,
                            intentos_odoo = intentos_odoo + 1
                    WHERE id_pedido = $1`,
                    [pedido.id_pedido, idOdoo]);
                console.log("Pedido " + pedido.ref_odoo + " enviado a Odoo (id " + idOdoo + ")");
            } catch (error) {
                await pool.query(
                    `UPDATE pedido SET estado_odoo = 'ERROR', error_odoo = left($2, 300),
                            intentos_odoo = intentos_odoo + 1
                    WHERE id_pedido = $1`,
                    [pedido.id_pedido, error.message]);
                console.error("Pedido " + pedido.ref_odoo + " con error: " + error.message);
            }
        }
    } catch (error) {
        console.error("Fallo en la sincronización: " + error.message);
    } finally {
        trabajando = false;
    }
}

// Hace una pasada al arrancar y luego una cada SINCRONIZACION_SEGUNDOS
function arrancar() {
    const segundos = Number(process.env.SINCRONIZACION_SEGUNDOS) || 30;
    sincronizar();
    setInterval(sincronizar, segundos * 1000);
}

// Lo arranca server.js
module.exports = { arrancar, sincronizar };