const header = document.querySelector(".header__container");

window.addEventListener("scroll", () => {
    header.classList.toggle("header__container--scroll", window.scrollY > 50);
});

const menu = document.querySelector(".lateral__check");
const contenido = document.querySelector(".contenido");

menu.addEventListener("change", () => {
    contenido.classList.toggle("contenido--desplazado", menu.checked);
});

const formularioCustom = document.querySelector(".custom__formulario");
const selectModelo = document.querySelector("#custom-modelo");
const selectTalla = document.querySelector("#custom-talla");
const inputCantidad = document.querySelector("#custom-cantidad");
const total = document.querySelector(".custom__total");
const mensaje = document.querySelector(".custom__mensaje");

let productos = [];

const categorias = [
    { clave: "correr", nombre: "Correr" },
    { clave: "botas", nombre: "Botas" },
    { clave: "futbol", nombre: "Fútbol" },
    { clave: "baloncesto", nombre: "Baloncesto" }
];

function cargarModelos() {
    categorias.forEach((categoria) => {
        let grupo = `<optgroup label="${categoria.nombre}">`;

        productos
            .filter((producto) => producto.categoria === categoria.clave)
            .forEach((producto) => {
                grupo += `<option value="${producto.id}">${producto.nombre}</option>`;
            });

        grupo += "</optgroup>";
        selectModelo.innerHTML += grupo;
    });
}

function buscarProducto() {
    const id = Number(selectModelo.value);
    return productos.find((producto) => producto.id === id);
}

function mostrarPrecio() {
    const producto = buscarProducto();
    const precio = producto ? producto.precio : 0;
    const cantidad = Number(inputCantidad.value);

    total.textContent = (precio * cantidad).toFixed(2).replace(".", ",") + " €";
}

function mostrarTallas() {
    const producto = buscarProducto();

    if (!producto) {
        selectTalla.innerHTML = '<option value="">Elige primero un modelo</option>';
        selectTalla.disabled = true;
        return;
    }

    selectTalla.innerHTML = '<option value="">Selecciona una talla</option>';
    producto.tallas.forEach((talla) => {
        selectTalla.innerHTML += `<option value="${talla}">${talla}</option>`;
    });
    selectTalla.disabled = false;
}

async function cargarProductos() {
    try {
        const respuesta = await fetch("productos.json");
        productos = await respuesta.json();
        cargarModelos();
    } catch (error) {
        console.error("No se pudieron cargar los productos:", error);
    }
}

cargarProductos();

selectModelo.addEventListener("change", () => {
    mostrarTallas();
    mostrarPrecio();
});
inputCantidad.addEventListener("input", mostrarPrecio);

formularioCustom.addEventListener("submit", (evento) => {
    evento.preventDefault();
    mensaje.textContent = "Solicitud enviada. Precio total: " + total.textContent;
});