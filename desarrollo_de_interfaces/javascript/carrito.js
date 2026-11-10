const iconoCarrito = document.querySelector('.header__icono[aria-label="Carrito"]');
const contadorCarrito = document.querySelector(".header__contador");
let carrito = JSON.parse(localStorage.getItem("carrito")) || [];

iconoCarrito.insertAdjacentHTML("afterend", `
    <div class="carrito">
        <p class="cuenta__etiqueta">Mi carrito</p>
        <div class="carrito__lista"></div>
        <p class="carrito__total"></p>
        <button class="boton boton--naranja carrito__comprar" type="button">Comprar</button>
        <form class="carrito__formulario">
            <div class="custom__campo">
                <label class="custom__label" for="carrito-nombre">Nombre</label>
                <input class="custom__input" type="text" id="carrito-nombre" name="nombre" maxlength="100" autocomplete="name" required>
            </div>
            <div class="custom__campo">
                <label class="custom__label" for="carrito-email">Email</label>
                <input class="custom__input" type="email" id="carrito-email" name="email" maxlength="120" autocomplete="email" required>
            </div>
            <div class="custom__campo">
                <label class="custom__label" for="carrito-telefono">Teléfono</label>
                <input class="custom__input" type="tel" id="carrito-telefono" name="telefono" maxlength="20" autocomplete="tel" required>
            </div>
            <div class="custom__campo">
                <label class="custom__label" for="carrito-direccion">Dirección</label>
                <input class="custom__input" type="text" id="carrito-direccion" name="direccion" maxlength="150" autocomplete="street-address" required>
            </div>
            <button class="boton boton--naranja carrito__confirmar">Confirmar compra</button>
        </form>
        <p class="carrito__mensaje"></p>
    </div>`);

const desplegableCarrito = document.querySelector(".carrito");
const listaCarrito = document.querySelector(".carrito__lista");
const totalCarrito = document.querySelector(".carrito__total");
const botonComprar = document.querySelector(".carrito__comprar");
const formularioCompra = document.querySelector(".carrito__formulario");
const botonConfirmar = document.querySelector(".carrito__confirmar");
const mensajeCompra = document.querySelector(".carrito__mensaje");

function formatearPrecio(precio) {
    return precio.toFixed(2).replace(".", ",") + " €";
}

function pintarCarrito() {
    let unidades = 0;
    let suma = 0;

    listaCarrito.innerHTML = "";
    carrito.forEach((articulo, indice) => {
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
                <button class="carrito__quitar" type="button" data-indice="${indice}">Quitar</button>
            </div>`;
    });

    contadorCarrito.textContent = unidades;
    totalCarrito.textContent = "Total: " + formatearPrecio(suma);
    totalCarrito.hidden = carrito.length === 0;
    mensajeCompra.textContent = "";

    if (carrito.length === 0) {
        listaCarrito.innerHTML = '<p class="cuenta__dato">Tu carrito está vacío</p>';
        formularioCompra.classList.remove("carrito__formulario--abierto");
    }

    botonComprar.hidden = carrito.length === 0 || formularioCompra.classList.contains("carrito__formulario--abierto");
}

function guardarCarrito() {
    localStorage.setItem("carrito", JSON.stringify(carrito));
    pintarCarrito();
}

function quitarDelCarrito(indice) {
    carrito[indice].cantidad--;

    if (carrito[indice].cantidad === 0) {
        carrito.splice(indice, 1);
    }

    guardarCarrito();
}

listaCarrito.addEventListener("click", (evento) => {
    if (evento.target.classList.contains("carrito__quitar")) {
        quitarDelCarrito(Number(evento.target.dataset.indice));
    }
});

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
    if (!usuarioSesion) {
        mensajeCompra.innerHTML = '<a class="carrito__enlace" href="login.html">Inicia sesión</a> para comprar';
        return;
    }

    if (!tienePermiso("PEDIDO_CREAR")) {
        mensajeCompra.textContent = "Tu usuario no tiene permiso para comprar";
        return;
    }

    formularioCompra.classList.add("carrito__formulario--abierto");
    botonComprar.hidden = true;
});

async function enviarPedido() {
    const respuesta = await fetch("/api/pedidos", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
            cliente: {
                nombre: formularioCompra.nombre.value.trim(),
                email: formularioCompra.email.value.trim(),
                telefono: formularioCompra.telefono.value.trim(),
                direccion: formularioCompra.direccion.value.trim()
            },
            articulos: carrito
        })
    });
    const datos = await respuesta.json();

    if (!respuesta.ok) {
        throw new Error(datos.error);
    }

    return datos;
}

formularioCompra.addEventListener("submit", async (evento) => {
    evento.preventDefault();

    botonConfirmar.disabled = true;
    mensajeCompra.textContent = "";

    try {
        const pedido = await enviarPedido();

        carrito = [];
        guardarCarrito();
        formularioCompra.reset();
        listaCarrito.innerHTML = `<p class="cuenta__dato">¡Gracias por tu compra! Pedido <strong>${pedido.referencia}</strong> por ${formatearPrecio(pedido.total)}. Queda pendiente de aprobación</p>`;
    } catch (error) {
        console.error("No se pudo guardar el pedido:", error);
        mensajeCompra.textContent = error instanceof TypeError ? "No se ha podido conectar. Inténtalo más tarde" : error.message;
    } finally {
        botonConfirmar.disabled = false;
    }
});

pintarCarrito();
