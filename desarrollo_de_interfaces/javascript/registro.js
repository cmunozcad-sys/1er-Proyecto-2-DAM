const formularioRegistro = document.querySelector(".registro__formulario");
const botonRegistro = document.querySelector(".registro__boton");
const mensajeRegistro = document.querySelector(".registro__mensaje");

function mostrarMensajeRegistro(texto, tipo) {
    mensajeRegistro.textContent = texto;
    mensajeRegistro.className = "login__mensaje registro__mensaje login__mensaje--" + tipo;
}

function validarRegistro(datos, repetir) {
    if (datos.nombre_completo === "" || datos.username === "" || datos.password === "") {
        return "Rellena todos los campos";
    }
    if (!/^[a-zA-Z0-9._-]{3,40}$/.test(datos.username)) {
        return "El usuario debe tener entre 3 y 40 letras, números, puntos o guiones";
    }
    if (datos.password.length < 8) {
        return "La contraseña debe tener al menos 8 caracteres";
    }
    if (datos.password !== repetir) {
        return "Las contraseñas no coinciden";
    }
    return null;
}

async function crearCuenta(evento) {
    evento.preventDefault();

    const datos = {
        nombre_completo: formularioRegistro.nombre.value.trim(),
        username: formularioRegistro.username.value.trim(),
        password: formularioRegistro.password.value
    };
    const errorValidacion = validarRegistro(datos, formularioRegistro.repetir.value);

    if (errorValidacion) {
        mostrarMensajeRegistro(errorValidacion, "error");
        return;
    }

    botonRegistro.disabled = true;

    try {
        const respuesta = await fetch("/api/registro", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(datos)
        });
        const resultado = await respuesta.json();

        if (!respuesta.ok) {
            mostrarMensajeRegistro(resultado.error, "error");
            botonRegistro.disabled = false;
            return;
        }

        mostrarMensajeRegistro(`Cuenta ${resultado.username} creada. Ya puedes iniciar sesión`, "exito");
        formularioRegistro.reset();

        setTimeout(() => {
            window.location.href = "login.html";
        }, 1500);
    } catch (error) {
        console.error("No se pudo crear la cuenta:", error);
        mostrarMensajeRegistro("No se ha podido conectar. Inténtalo más tarde", "error");
        botonRegistro.disabled = false;
    }
}

if (usuarioSesion) {
    window.location.href = "index.html";
} else {
    formularioRegistro.addEventListener("submit", crearCuenta);
}
