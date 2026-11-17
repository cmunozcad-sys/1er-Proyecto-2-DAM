const cuerpoPedidos = document.querySelector(".panel__pedidos");
const mensajePedidos = document.querySelector(".panel__mensaje--pedidos");
const formularioBusqueda = document.querySelector(".panel__busqueda");
const botonLimpiar = document.querySelector(".panel__limpiar");
const botonExportar = document.querySelector(".panel__exportar");
const formularioReponer = document.querySelector(".panel__reponer");
const selectReponerModelo = document.querySelector("#reponer-modelo");
const selectReponerTalla = document.querySelector("#reponer-talla");
const botonGuardarReponer = document.querySelector(".panel__guardar");
const mensajeReponer = document.querySelector(".panel__mensaje--reponer");

const nombresEstado = {
    BORRADOR: "Pendiente",
    CONFIRMADO: "Confirmado",
    CANCELADO: "Cancelado"
};

let pedidos = [];
let modelos = [];

function precioEnEuros(precio) {
    return precio.toFixed(2).replace(".", ",") + " €";
}

function crearFila(pedido) {
    const tipo = pedido.tipo === "CUSTOM" ? "Custom" : "Estándar";
    const acciones = pedido.estado === "BORRADOR" ? `
        <button class="boton boton--naranja panel__accion" type="button" data-id="${pedido.id_pedido}" data-accion="aprobar">Aprobar</button>
        <button class="boton boton--secundario panel__accion" type="button" data-id="${pedido.id_pedido}" data-accion="cancelar">Cancelar</button>` : "";

    return `
        <tr class="panel__fila">
            <td class="panel__celda"><strong>${pedido.referencia}</strong><span class="panel__detalle">${pedido.fecha}</span></td>
            <td class="panel__celda">${pedido.cliente}<span class="panel__detalle">${tipo}</span></td>
            <td class="panel__celda panel__celda--articulos">${pedido.articulos || "Sin artículos"}</td>
            <td class="panel__celda">${precioEnEuros(pedido.total)}</td>
            <td class="panel__celda"><span class="panel__estado panel__estado--${pedido.estado.toLowerCase()}">${nombresEstado[pedido.estado]}</span></td>
            <td class="panel__celda"><div class="panel__acciones">${acciones}</div></td>
        </tr>`;
}

function pintarPedidos() {
    if (pedidos.length === 0) {
        cuerpoPedidos.innerHTML = '<tr><td class="panel__vacio" colspan="6">No hay resultados con estos filtros</td></tr>';
        return;
    }

    cuerpoPedidos.innerHTML = pedidos.map(crearFila).join("");
}

function parametrosBusqueda() {
    const parametros = new URLSearchParams();

    new FormData(formularioBusqueda).forEach((valor, clave) => {
        if (valor.trim() !== "") {
            parametros.append(clave, valor.trim());
        }
    });

    return parametros.toString();
}

function fechasCorrectas() {
    const desde = formularioBusqueda.desde.value;
    const hasta = formularioBusqueda.hasta.value;

    if (desde && hasta && desde > hasta) {
        mensajePedidos.textContent = "La fecha «Desde» no puede ser posterior a «Hasta»";
        return false;
    }

    return true;
}

async function cargarPedidos(limpiar) {
    mensajePedidos.textContent = "";

    if (!fechasCorrectas()) {
        return;
    }

    try {
        const respuesta = await fetch("/api/pedidos?" + (limpiar ? "limpiar=1" : parametrosBusqueda()));
        const datos = await respuesta.json();

        if (!respuesta.ok) {
            mensajePedidos.textContent = datos.error;
            return;
        }

        pedidos = datos;
        pintarPedidos();
    } catch (error) {
        console.error("No se pudieron cargar los pedidos:", error);
        mensajePedidos.textContent = "No se ha podido conectar. Inténtalo más tarde";
    }
}

async function cargarIndicadores() {
    if (!tienePermiso("INDICADORES_VER")) {
        document.querySelectorAll(".panel__resumen").forEach((seccion) => {
            seccion.style.display = "none";
        });
        return;
    }

    try {
        const respuesta = await fetch("/api/indicadores");
        const datos = await respuesta.json();

        if (!respuesta.ok) {
            mensajePedidos.textContent = datos.error;
            return;
        }

        document.querySelector('[data-indicador="total_pedidos"]').textContent = datos.total_pedidos;
        document.querySelector('[data-indicador="pares_solicitados"]').textContent = datos.pares_solicitados;
        document.querySelector('[data-indicador="importe_ventas"]').textContent = precioEnEuros(datos.importe_ventas);

        document.querySelectorAll(".panel__numero[data-estado]").forEach((numero) => {
            numero.textContent = datos.por_estado[numero.dataset.estado] || 0;
        });
    } catch (error) {
        console.error("No se pudieron cargar los indicadores:", error);
    }
}

async function exportarCsv() {
    mensajePedidos.textContent = "";

    if (!fechasCorrectas()) {
        return;
    }

    botonExportar.disabled = true;

    try {
        const respuesta = await fetch("/api/pedidos/csv?" + parametrosBusqueda());

        if (!respuesta.ok) {
            const datos = await respuesta.json();
            mensajePedidos.textContent = datos.error;
            return;
        }

        const enlace = document.createElement("a");
        enlace.href = URL.createObjectURL(await respuesta.blob());
        enlace.download = "pedidos_filtrados.csv";
        enlace.click();
        URL.revokeObjectURL(enlace.href);
        mensajePedidos.textContent = "CSV exportado con los filtros actuales";
    } catch (error) {
        console.error("No se pudo exportar el CSV:", error);
        mensajePedidos.textContent = "No se ha podido conectar. Inténtalo más tarde";
    } finally {
        botonExportar.disabled = false;
    }
}

async function cambiarEstadoPedido(boton) {
    const pedido = pedidos.find((pedido) => pedido.id_pedido === Number(boton.dataset.id));
    const accion = boton.dataset.accion;

    if (accion === "cancelar" && !confirm("¿Seguro que quieres cancelar el pedido " + pedido.referencia + "?")) {
        return;
    }

    boton.disabled = true;
    mensajePedidos.textContent = "";

    try {
        const respuesta = await fetch(`/api/pedidos/${pedido.id_pedido}/${accion}`, { method: "POST" });
        const datos = await respuesta.json();

        if (!respuesta.ok) {
            mensajePedidos.textContent = datos.error;
            boton.disabled = false;
            return;
        }

        await cargarPedidos();
        cargarIndicadores();
        mensajePedidos.textContent = `Pedido ${pedido.referencia} ${accion === "aprobar" ? "aprobado" : "cancelado"}`;
    } catch (error) {
        console.error("No se pudo cambiar el estado del pedido:", error);
        mensajePedidos.textContent = "No se ha podido conectar. Inténtalo más tarde";
        boton.disabled = false;
    }
}

function cargarSelectModelos() {
    categorias.forEach((categoria) => {
        const opciones = modelos
            .filter((modelo) => modelo.categoria === categoria.clave)
            .map((modelo) => `<option value="${modelo.id}">${modelo.nombre}</option>`);

        selectReponerModelo.innerHTML += `<optgroup label="${categoria.nombre}">${opciones.join("")}</optgroup>`;
    });
}

function cargarSelectTallas() {
    const modelo = modelos.find((modelo) => modelo.id === Number(selectReponerModelo.value));

    if (!modelo) {
        selectReponerTalla.innerHTML = '<option value="">Elige primero un modelo</option>';
        return;
    }

    selectReponerTalla.innerHTML = modelo.tallas.map((talla) => `<option value="${talla}">${talla}</option>`).join("");
}

async function cargarModelosReponer() {
    try {
        const respuesta = await fetch("json/productos.json");
        modelos = await respuesta.json();
        cargarSelectModelos();
    } catch (error) {
        console.error("No se pudieron cargar los modelos:", error);
        mensajeReponer.textContent = "No se han podido cargar los modelos";
    }
}

async function reponerStock(evento) {
    evento.preventDefault();

    const modelo = selectReponerModelo.options[selectReponerModelo.selectedIndex].text;
    const talla = Number(selectReponerTalla.value);

    botonGuardarReponer.disabled = true;
    mensajeReponer.textContent = "";

    try {
        const respuesta = await fetch("/api/stock", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
                id: Number(selectReponerModelo.value),
                talla: talla,
                cantidad: Number(formularioReponer.cantidad.value)
            })
        });
        const datos = await respuesta.json();

        if (!respuesta.ok) {
            mensajeReponer.textContent = datos.error;
            return;
        }

        mensajeReponer.textContent = `${modelo}, talla ${talla}: ahora hay ${datos.cantidad} pares`;
        formularioReponer.cantidad.value = 1;
    } catch (error) {
        console.error("No se pudo añadir al stock:", error);
        mensajeReponer.textContent = "No se ha podido conectar. Inténtalo más tarde";
    } finally {
        botonGuardarReponer.disabled = false;
    }
}

if (!tienePermiso("PEDIDO_VER")) {
    window.location.href = "login.html";
} else {
    document.querySelector(".panel__saludo").textContent = "Hola, " + usuarioSesion.nombre + " (" + usuarioSesion.rol + ")";

    if (!tienePermiso("USUARIOS_GESTIONAR")) {
        document.querySelector('.header__boton[href="usuarios.html"]').remove();
    }

    cargarPedidos();
    cargarIndicadores();
    cargarModelosReponer();

    cuerpoPedidos.addEventListener("click", (evento) => {
        if (evento.target.classList.contains("panel__accion")) {
            cambiarEstadoPedido(evento.target);
        }
    });

    formularioBusqueda.addEventListener("submit", (evento) => {
        evento.preventDefault();
        cargarPedidos(false);
    });

    botonLimpiar.addEventListener("click", () => {
        formularioBusqueda.reset();
        cargarPedidos(true);
    });

    botonExportar.addEventListener("click", exportarCsv);

    document.querySelector(".panel__actualizar").addEventListener("click", () => {
        cargarPedidos();
        cargarIndicadores();
    });

    selectReponerModelo.addEventListener("change", cargarSelectTallas);
    formularioReponer.addEventListener("submit", reponerStock);
}
