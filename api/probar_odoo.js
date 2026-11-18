// Comprueba la conexión con Odoo: docker compose exec api node probar_odoo.js

const odoo = require("./odoo");

// Busca hasta 3 registros de un modelo y los enseña por consola
async function mostrar(titulo, modelo, condiciones, campos) {
    const filas = await odoo.ejecutar(modelo, "search_read", [condiciones], { fields: campos, limit: 3 });
    console.log(titulo, filas);
}

// Se conecta y prueba a leer clientes y la Cometa en talla 41 de varias formas
async function probar() {
    await odoo.conectar();
    console.log("Conexión correcta con Odoo");

    await mostrar("Clientes:", "res.partner", [["customer_rank", ">", 0]], ["name", "email", "ref"]);
    await mostrar("Cometa 41 por código:", "product.product",
        [["product_tmpl_id.default_code", "=", "SF-001"], ["product_template_attribute_value_ids.name", "=", "41"]],
        ["display_name", "default_code"]);
    await mostrar("Cometa 41 por nombre:", "product.product",
        [["product_tmpl_id.name", "=", "Cometa"], ["product_template_attribute_value_ids.name", "=", "41"]],
        ["display_name", "default_code"]);
    await mostrar("SF-002 sin tallas:", "product.product",
        [["product_tmpl_id.default_code", "=", "SF-002"], ["product_tmpl_id.attribute_line_ids", "=", false]],
        ["display_name", "default_code"]);
}

// Si algo falla se muestra el mensaje
probar().catch((error) => console.error("Error: " + error.message));