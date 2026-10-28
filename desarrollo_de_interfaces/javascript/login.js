const enlaceCuenta = document.querySelector('.header__icono[aria-label="Mi cuenta"]');
const usuarioSesion = JSON.parse(localStorage.getItem("usuario"));

function tienePermiso(codigo) {
    return usuarioSesion !== null && usuarioSesion.permisos.includes(codigo);
}

if (usuarioSesion) {
    enlaceCuenta.classList.add("header__icono--activo");

    enlaceCuenta.insertAdjacentHTML("afterend", `
        <div class="cuenta">
            <p class="cuenta__etiqueta">Mi perfil</p>
            <p class="cuenta__nombre">${usuarioSesion.nombre}</p>
            <p class="cuenta__dato">Usuario: <strong>${usuarioSesion.username}</strong></p>
            <p class="cuenta__dato">Rol: <strong>${usuarioSesion.rol}</strong></p>
            <button class="boton boton--naranja cuenta__salir" type="button">Cerrar sesión</button>
        </div>`);

    const desplegable = document.querySelector(".cuenta");

    enlaceCuenta.addEventListener("click", (evento) => {
        evento.preventDefault();
        desplegable.classList.toggle("cuenta--abierta");
    });

    document.querySelector(".cuenta__salir").addEventListener("click", () => {
        localStorage.removeItem("usuario");
        window.location.reload();
    });
}

const formularioLogin = document.querySelector(".login__formulario");
const inputUsuario = document.querySelector("#login-usuario");
const inputPassword = document.querySelector("#login-password");
const checkMostrar = document.querySelector("#login-mostrar");
const mensajeLogin = document.querySelector(".login__mensaje");

function mostrarMensaje(texto, tipo) {
    mensajeLogin.textContent = texto;
    mensajeLogin.className = "login__mensaje login__mensaje--" + tipo;
}

async function comprobarUsuario(username, password) {
    const respuesta = await fetch("json/usuarios.json");
    const usuarios = await respuesta.json();

    return usuarios.find((usuario) => usuario.username === username && usuario.password === password);
}

if (formularioLogin) {
    if (usuarioSesion) {
        window.location.href = "index.html";
    }

    checkMostrar.addEventListener("change", () => {
        inputPassword.type = checkMostrar.checked ? "text" : "password";
    });

    formularioLogin.addEventListener("submit", async (evento) => {
        evento.preventDefault();

        const username = inputUsuario.value.trim();
        const password = inputPassword.value;

        if (username === "" || password === "") {
            mostrarMensaje("Rellena el usuario y la contraseña", "error");
            return;
        }

        try {
            const usuario = await comprobarUsuario(username, password);

            if (!usuario) {
                mostrarMensaje("Usuario o contraseña incorrectos", "error");
                inputPassword.value = "";
                return;
            }

            if (!usuario.activo) {
                mostrarMensaje("Este usuario está desactivado", "error");
                return;
            }

            localStorage.setItem("usuario", JSON.stringify({
                username: usuario.username,
                nombre: usuario.nombre_completo,
                rol: usuario.rol,
                permisos: usuario.permisos
            }));

            mostrarMensaje("Bienvenido, " + usuario.nombre_completo, "exito");

            setTimeout(() => {
                window.location.href = "index.html";
            }, 1500);
        } catch (error) {
            console.error("No se pudo comprobar el usuario:", error);
            mostrarMensaje("No se ha podido conectar. Inténtalo más tarde", "error");
        }
    });
}
