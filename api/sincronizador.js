const pool = require("./db");
const odoo = require("./odoo");

const MAX_INTENTOS = 5;
let trabajando = false;

const consultaPendientes = `
    SELECT p.id_pedido, p.ref_odoo, p.observaciones,
           c.ref_odoo AS ref_cliente, c.nombre, c.email, c.telefono, c.direccion, c.tipo
      FROM pedido p
      JOIN cliente c ON c.id_cliente = p.id_cliente
     WHERE p.estado = 'CONFIRMADO'
       AND p.estado_odoo IN ('PENDIENTE', 'ERROR')
       AND p.intentos_odoo < $1
     ORDER BY p.id_pedido`;

const consultaLineas = `
    SELECT l.talla::float AS talla, l.cantidad, l.precio_unitario::float AS precio,
           l.personalizacion, l.texto_bordado, m.ref_odoo AS ref_modelo, m.nombre AS modelo
      FROM linea_pedido l
      JOIN variante v ON v.id_variante = l.id_variante
      JOIN modelo m ON m.id_modelo = v.id_modelo
     WHERE l.id_pedido = $1
     ORDER BY l.id_linea`;

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

async function enviarPedido(pedido) {
    const existente = await odoo.buscarUno("sale.order", [["client_order_ref", "=", pedido.ref_odoo]]);

    if (existente) {
        return existente;
    }

    const idCliente = await buscarOCrearCliente(pedido);
    const lineas = (await pool.query(consultaLineas, [pedido.id_pedido])).rows;
    const lineasOdoo = [];

    for (const linea of lineas) {
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
            await odoo.conectar();
        } catch (error) {
            console.error("Odoo no disponible, se reintentará: " + error.message);
            return;
        }

        for (const pedido of pendientes) {
            try {
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

function arrancar() {
    const segundos = Number(process.env.SINCRONIZACION_SEGUNDOS) || 30;
    sincronizar();
    setInterval(sincronizar, segundos * 1000);
}

module.exports = { arrancar, sincronizar };