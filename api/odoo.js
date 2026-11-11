const url = process.env.ODOO_URL + "/jsonrpc";
const baseDatos = process.env.ODOO_DB;
const usuario = process.env.ODOO_USER;
const clave = process.env.ODOO_API_KEY;

let uid = null;

async function llamar(servicio, metodo, argumentos) {
    const respuesta = await fetch(url, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
            jsonrpc: "2.0",
            method: "call",
            params: { service: servicio, method: metodo, args: argumentos }
        })
    });
    const datos = await respuesta.json();

    if (datos.error) {
        throw new Error(datos.error.data ? datos.error.data.message : datos.error.message);
    }
    return datos.result;
}

async function conectar() {
    uid = await llamar("common", "login", [baseDatos, usuario, clave]);

    if (!uid) {
        throw new Error("Odoo ha rechazado el usuario o la clave");
    }
}

function ejecutar(modelo, metodo, argumentos, opciones = {}) {
    return llamar("object", "execute_kw", [baseDatos, uid, clave, modelo, metodo, argumentos, opciones]);
}

async function buscarUno(modelo, condiciones) {
    const ids = await ejecutar(modelo, "search", [condiciones], { limit: 1 });
    return ids.length > 0 ? ids[0] : null;
}

module.exports = { conectar, ejecutar, buscarUno };