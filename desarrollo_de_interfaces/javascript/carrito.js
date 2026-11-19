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
                <!-- Botones de cada artículo: data-accion dice qué hace y data-indice a qué artículo afecta -->
                <div class="carrito__botones">
                    <button class="carrito__boton" type="button" data-accion="menos" data-indice="${indice}" aria-label="Quitar uno">−</button>
                    <button class="carrito__boton" type="button" data-accion="mas" data-indice="${indice}" aria-label="Añadir uno">+</button>
                    <button class="carrito__boton" type="button" data-accion="borrar" data-indice="${indice}" aria-label="Eliminar">
                        <svg class="carrito__papelera" viewBox="0 0 24 24"><path d="M4 7h16"></path><path d="M9 7V4h6v3"></path><path d="M6 7l1 13h10l1-13"></path></svg>
                    </button>
                </div>
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

    // Cada vez que cambia el carrito se vuelve a mirar si hay stock suficiente
    if (carrito.length > 0) {
        comprobarStock();
    }
}

// Pregunta al servidor cuántos pares quedan de cada artículo en su talla.
// Si en el carrito hay más pares que stock, desactiva el botón Comprar y avisa de cuáles faltan
async function comprobarStock() {
    const sinStock = [];
    botonComprar.disabled = true;

    try {
        for (const articulo of carrito) {
            const respuesta = await fetch(`/api/stock?id=${articulo.id}&talla=${articulo.talla}`);
            const datos = await respuesta.json();

            if (articulo.cantidad > datos.cantidad) {
                sinStock.push(`${articulo.nombre} talla ${articulo.talla} (quedan ${datos.cantidad})`);
            }
        }
    } catch (error) {
        console.error("No se pudo comprobar el stock:", error);
    }

    botonComprar.disabled = sinStock.length > 0;

    if (sinStock.length > 0) {
        mensajeCompra.textContent = "No hay stock suficiente de: " + sinStock.join(", ");
    }
}

function guardarCarrito() {
    localStorage.setItem("carrito", JSON.stringify(carrito));
    pintarCarrito();
}

// Botones del artículo: "mas" suma un par, "menos" resta uno y "borrar" lo quita entero.
// Si la cantidad llega a 0 también se quita del carrito
function cambiarCantidad(indice, accion) {
    if (accion === "mas") {
        carrito[indice].cantidad++;
    } else if (accion === "menos") {
        carrito[indice].cantidad--;
    }

    if (accion === "borrar" || carrito[indice].cantidad === 0) {
        carrito.splice(indice, 1);
    }

    guardarCarrito();
}

// Un solo listener para toda la lista; closest encuentra el botón aunque se pulse el dibujo de la papelera
listaCarrito.addEventListener("click", (evento) => {
    const boton = evento.target.closest(".carrito__boton");

    if (boton) {
        cambiarCantidad(Number(boton.dataset.indice), boton.dataset.accion);
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
