const iconoCarrito = document.querySelector('.header__icono[aria-label="Carrito"]');
const contadorCarrito = document.querySelector(".header__contador");
let carrito = JSON.parse(localStorage.getItem("carrito")) || [];

iconoCarrito.insertAdjacentHTML("afterend", `
    <div class="carrito">
        <p class="cuenta__etiqueta">Mi carrito</p>
        <div class="carrito__lista"></div>
        <p class="carrito__total"></p>
        <button class="boton boton--naranja carrito__comprar" type="button">Comprar</button>
    </div>`);

const desplegableCarrito = document.querySelector(".carrito");
const listaCarrito = document.querySelector(".carrito__lista");
const totalCarrito = document.querySelector(".carrito__total");
const botonComprar = document.querySelector(".carrito__comprar");

function formatearPrecio(precio) {
    return precio.toFixed(2).replace(".", ",") + " €";
}

function pintarCarrito() {
    let unidades = 0;
    let suma = 0;

    listaCarrito.innerHTML = "";
    carrito.forEach((articulo) => {
        unidades += articulo.cantidad;
        suma += articulo.precio * articulo.cantidad;

        listaCarrito.innerHTML += `
            <div class="carrito__articulo">
                <img class="carrito__img" src="${articulo.imagen}" alt="">
                <div>
                    <p class="carrito__nombre">${articulo.nombre}</p>
                    <p class="cuenta__dato">Talla ${articulo.talla} · ${articulo.cantidad} ud.</p>
                    <p class="cuenta__dato"><strong>${formatearPrecio(articulo.precio * articulo.cantidad)}</strong></p>
                </div>
            </div>`;
    });

    contadorCarrito.textContent = unidades;
    totalCarrito.textContent = "Total: " + formatearPrecio(suma);
    totalCarrito.hidden = carrito.length === 0;
    botonComprar.hidden = carrito.length === 0;

    if (carrito.length === 0) {
        listaCarrito.innerHTML = '<p class="cuenta__dato">Tu carrito está vacío</p>';
    }
}

function guardarCarrito() {
    localStorage.setItem("carrito", JSON.stringify(carrito));
    pintarCarrito();
}

function anadirAlCarrito(producto, talla) {
    const articulo = carrito.find((articulo) => articulo.id === producto.id && articulo.talla === talla);

    if (articulo) {
        articulo.cantidad++;
    } else {
        carrito.push({
            id: producto.id,
            nombre: producto.nombre,
            imagen: producto.imagen,
            precio: producto.precio,
            talla: talla,
            cantidad: 1
        });
    }

    guardarCarrito();
    desplegableCarrito.classList.add("carrito--abierto");
}

iconoCarrito.addEventListener("click", (evento) => {
    evento.preventDefault();
    desplegableCarrito.classList.toggle("carrito--abierto");

    const desplegableCuenta = document.querySelector(".cuenta");
    if (desplegableCuenta) {
        desplegableCuenta.classList.remove("cuenta--abierta");
    }
});

botonComprar.addEventListener("click", () => {
    carrito = [];
    guardarCarrito();
    listaCarrito.innerHTML = '<p class="cuenta__dato">¡Gracias por tu compra!</p>';
});

pintarCarrito();
