const cuerpoPedidos = document.querySelector(".panel__pedidos");
const mensajePedidos = document.querySelector(".panel__mensaje--pedidos");
const botonesFiltro = document.querySelectorAll(".panel__filtro");
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
let filtroActual = "BORRADOR";

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
    const visibles = filtroActual === "TODOS"
        ? pedidos
        : pedidos.filter((pedido) => pedido.estado === filtroActual);

    document.querySelectorAll(".panel__numero").forEach((numero) => {
        numero.textContent = pedidos.filter((pedido) => pedido.estado === numero.dataset.estado).length;
    });

    if (visibles.length === 0) {
        cuerpoPedidos.innerHTML = '<tr><td class="panel__vacio" colspan="6">No hay pedidos en este estado</td></tr>';
        return;
    }

    cuerpoPedidos.innerHTML = visibles.map(crearFila).join("");
}

async function cargarPedidos() {
    mensajePedidos.textContent = "";

    try {
        const respuesta = await fetch("/api/pedidos");
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

        pedido.estado = datos.estado;
        mensajePedidos.textContent = `Pedido ${pedido.referencia} ${accion === "aprobar" ? "aprobado" : "cancelado"}`;
        pintarPedidos();
    } catch (error) {
        console.error("No se pudo cambiar el estado del pedido:", error);
        mensajePedidos.textContent = "No se ha podido conectar. Inténtalo más tarde";
        boton.disabled = false;
    }
}

function elegirFiltro(botonElegido) {
    filtroActual = botonElegido.dataset.estado;

    botonesFiltro.forEach((boton) => {
        boton.classList.toggle("boton--principal", boton === botonElegido);
        boton.classList.toggle("boton--secundario", boton !== botonElegido);
    });

    pintarPedidos();
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

if (!esAdmin(usuarioSesion)) {
    window.location.href = "login.html";
} else {
    document.querySelector(".panel__saludo").textContent = "Hola, " + usuarioSesion.nombre;

    cargarPedidos();
    cargarModelosReponer();

    cuerpoPedidos.addEventListener("click", (evento) => {
        if (evento.target.classList.contains("panel__accion")) {
            cambiarEstadoPedido(evento.target);
        }
    });

    botonesFiltro.forEach((boton) => {
        boton.addEventListener("click", () => elegirFiltro(boton));
    });

    document.querySelector(".panel__actualizar").addEventListener("click", cargarPedidos);
    selectReponerModelo.addEventListener("change", cargarSelectTallas);
    formularioReponer.addEventListener("submit", reponerStock);
}
