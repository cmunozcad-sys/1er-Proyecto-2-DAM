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
const contenedorTallas = document.querySelector(".custom__tallas");
const inputEmail = document.querySelector("#custom-email");
const total = document.querySelector(".custom__total");
const pares = document.querySelector(".custom__pares");
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

function contarPares() {
    const inputsTalla = contenedorTallas.querySelectorAll("input");
    let suma = 0;

    inputsTalla.forEach((input) => {
        suma += Number(input.value);
    });

    return suma;
}

function mostrarPrecio() {
    const producto = buscarProducto();
    const precio = producto ? producto.precio : 0;
    const numeroPares = contarPares();

    total.textContent = (precio * numeroPares).toFixed(2).replace(".", ",") + " €";
    pares.textContent = numeroPares + " pares";
}

function mostrarTallas() {
    const producto = buscarProducto();

    if (!producto) {
        contenedorTallas.innerHTML = '<p class="custom__aviso">Elige primero un modelo</p>';
        return;
    }

    contenedorTallas.innerHTML = "";
    producto.tallas.forEach((talla) => {
        contenedorTallas.innerHTML += `
            <div class="custom__campo">
                <label class="custom__label" for="talla-${talla}">${talla}</label>
                <input class="custom__input custom__input--talla" type="number" id="talla-${talla}" name="talla-${talla}" min="0" value="0">
            </div>`;
    });
}

async function cargarProductos() {
    try {
        const respuesta = await fetch("json/productos.json");
        productos = await respuesta.json();
        cargarModelos();
    } catch (error) {
        console.error("No se pudieron cargar los productos:", error);
    }
}

if (formularioCustom) {
    cargarProductos();

    selectModelo.addEventListener("change", () => {
        mostrarTallas();
        mostrarPrecio();
    });
    contenedorTallas.addEventListener("input", mostrarPrecio);

    formularioCustom.addEventListener("submit", (evento) => {
        evento.preventDefault();

        if (contarPares() === 0) {
            mensaje.textContent = "Indica al menos un par en las tallas";
            return;
        }

        mensaje.textContent = "Solicitud enviada. Te enviaremos el presupuesto a " + inputEmail.value;
        formularioCustom.reset();
        mostrarTallas();
        mostrarPrecio();
    });
}

const paginaProducto = document.querySelector(".producto");

function pintarProducto(producto) {
    const categoria = categorias.find((categoria) => categoria.clave === producto.categoria);
    const referencia = String(producto.id).padStart(3, "0");
    const imagen = document.querySelector(".producto__img");

    document.title = producto.nombre;
    imagen.src = producto.imagen;
    imagen.alt = "Zapatilla " + producto.nombre;

    document.querySelector(".ficha__categoria").textContent = categoria.nombre + " · Ref. " + referencia;
    document.querySelector(".producto__nombre").textContent = producto.nombre;
    document.querySelector(".ficha__insignia").hidden = !producto.destacado;
    document.querySelector(".producto__precio").textContent = producto.precio.toFixed(2).replace(".", ",") + " €";
    document.querySelector(".ficha__descripcion").textContent = producto.descripcion;
    document.querySelector(".producto__volver").href = "detalle.html#producto-" + producto.id;

    const colores = document.querySelector(".producto__colores");
    producto.colores.forEach((color) => {
        colores.innerHTML += `<span class="tarjeta__muestra tarjeta__muestra--${color.replace("ó", "o")}"></span>`;
    });
    const nombresColores = producto.colores.map((color) => color.charAt(0).toUpperCase() + color.slice(1));
    colores.innerHTML += `<span class="tarjeta__texto-colores">${nombresColores.join(" / ")}</span>`;

    const tallas = document.querySelector(".producto__tallas");
    producto.tallas.forEach((talla) => {
        tallas.innerHTML += `
            <input class="producto__radio" type="radio" name="talla" id="talla-${talla}" value="${talla}">
            <label class="ficha__talla producto__talla" for="talla-${talla}">${talla}</label>`;
    });
}

async function cargarProducto() {
    const id = Number(new URLSearchParams(location.search).get("id"));

    try {
        const respuesta = await fetch("json/productos.json");
        const lista = await respuesta.json();
        const producto = lista.find((producto) => producto.id === id);

        if (!producto) {
            document.querySelector(".producto__contenido").innerHTML = '<p class="ficha__texto">No hemos encontrado esta zapatilla.</p>';
            return;
        }

        pintarProducto(producto);
    } catch (error) {
        console.error("No se pudo cargar el producto:", error);
    }
}

if (paginaProducto) {
    cargarProducto();
}