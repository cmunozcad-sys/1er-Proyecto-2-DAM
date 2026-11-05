function prepararFichaAdmin(ficha) {
    const id = Number(ficha.id.replace("producto-", ""));
    const tallas = Array.from(ficha.querySelectorAll(".ficha__talla")).map((talla) => talla.textContent);
    const opciones = tallas.map((talla) => `<option value="${talla}">${talla}</option>`);

    ficha.querySelector(".ficha__info").insertAdjacentHTML("beforeend", `
        <button class="boton boton--secundario ficha__anadir" type="button">Añadir zapatillas</button>

        <form class="ficha__reponer">
            <div class="custom__campo">
                <label class="custom__label" for="reponer-talla-${id}">Talla</label>
                <select class="custom__input" id="reponer-talla-${id}" name="talla">${opciones.join("")}</select>
            </div>

            <div class="custom__campo">
                <label class="custom__label" for="reponer-cantidad-${id}">Pares a añadir</label>
                <input class="custom__input" type="number" id="reponer-cantidad-${id}" name="cantidad" min="1" max="10000" value="1" required>
            </div>

            <button class="boton boton--naranja ficha__guardar">Guardar</button>
            <p class="ficha__mensaje"></p>
        </form>`);

    const formulario = ficha.querySelector(".ficha__reponer");
    const botonGuardar = ficha.querySelector(".ficha__guardar");
    const mensaje = ficha.querySelector(".ficha__mensaje");

    ficha.querySelector(".ficha__anadir").addEventListener("click", () => {
        formulario.classList.toggle("ficha__reponer--abierta");
    });

    formulario.addEventListener("submit", async (evento) => {
        evento.preventDefault();

        const talla = Number(formulario.talla.value);

        botonGuardar.disabled = true;
        mensaje.textContent = "";

        try {
            const respuesta = await fetch("/api/stock", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({
                    id: id,
                    talla: talla,
                    cantidad: Number(formulario.cantidad.value)
                })
            });
            const datos = await respuesta.json();

            if (!respuesta.ok) {
                mensaje.textContent = datos.error;
                return;
            }

            mensaje.textContent = `Talla ${talla}: ahora hay ${datos.cantidad} pares`;
            formulario.cantidad.value = 1;
        } catch (error) {
            console.error("No se pudo añadir al stock:", error);
            mensaje.textContent = "No se ha podido conectar. Inténtalo más tarde";
        } finally {
            botonGuardar.disabled = false;
        }
    });
}

async function prepararFichasAdmin() {
    await fichasCargadas;
    document.querySelectorAll(".ficha").forEach(prepararFichaAdmin);
    irAlEnlace();
}

if (usuarioSesion && usuarioSesion.rol === "Administrador") {
    prepararFichasAdmin();
}
