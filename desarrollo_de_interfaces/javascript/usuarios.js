const cuerpoUsuarios = document.querySelector(".panel__usuarios");
const mensajeUsuarios = document.querySelector(".panel__mensaje--usuarios");
const formularioUsuario = document.querySelector(".panel__formulario");
const selectRolNuevo = document.querySelector("#usuario-rol");
const botonCrearUsuario = document.querySelector(".panel__guardar");
const mensajeCrear = document.querySelector(".panel__mensaje--crear");
const botonExportar = document.querySelector(".panel__exportar");

let usuarios = [];
let roles = [];

function opcionesRol(idSeleccionado) {
    return roles
        .map((rol) => `<option value="${rol.id_rol}" ${rol.id_rol === idSeleccionado ? "selected" : ""}>${rol.nombre}</option>`)
        .join("");
}

function crearFilaUsuario(usuario) {
    const esPropio = usuario.username === usuarioSesion.username;
    const estado = usuario.activo ? "activo" : "inactivo";
    const accion = usuario.activo && !esPropio
        ? `<button class="boton boton--secundario panel__accion" type="button" data-id="${usuario.id_usuario}">Desactivar</button>`
        : "";

    return `
        <tr class="panel__fila">
            <td class="panel__celda"><strong>${usuario.username}</strong><span class="panel__detalle">${usuario.nombre_completo}</span></td>
            <td class="panel__celda">
                <select class="custom__input panel__rol" data-id="${usuario.id_usuario}" ${esPropio ? "disabled" : ""}>${opcionesRol(usuario.id_rol)}</select>
            </td>
            <td class="panel__celda"><span class="panel__estado panel__estado--${estado}">${usuario.activo ? "Activo" : "Inactivo"}</span></td>
            <td class="panel__celda">${usuario.ultimo_acceso || "Nunca"}</td>
            <td class="panel__celda"><div class="panel__acciones">${accion}</div></td>
        </tr>`;
}

function pintarUsuarios() {
    if (usuarios.length === 0) {
        cuerpoUsuarios.innerHTML = '<tr><td class="panel__vacio" colspan="5">No hay usuarios</td></tr>';
        return;
    }

    cuerpoUsuarios.innerHTML = usuarios.map(crearFilaUsuario).join("");
}

async function cargarRoles() {
    try {
        const respuesta = await fetch("/api/roles");
        const datos = await respuesta.json();

        if (!respuesta.ok) {
            mensajeCrear.textContent = datos.error;
            return;
        }

        roles = datos;
        selectRolNuevo.innerHTML = '<option value="">Selecciona un rol</option>' + opcionesRol(null);
    } catch (error) {
        console.error("No se pudieron cargar los roles:", error);
        mensajeCrear.textContent = "No se han podido cargar los roles";
    }
}

async function cargarUsuarios() {
    mensajeUsuarios.textContent = "";

    try {
        const respuesta = await fetch("/api/usuarios");
        const datos = await respuesta.json();

        if (!respuesta.ok) {
            mensajeUsuarios.textContent = datos.error;
            return;
        }

        usuarios = datos;
        pintarUsuarios();
    } catch (error) {
        console.error("No se pudieron cargar los usuarios:", error);
        mensajeUsuarios.textContent = "No se ha podido conectar. Inténtalo más tarde";
    }
}

async function cambiarRol(select) {
    const usuario = usuarios.find((usuario) => usuario.id_usuario === Number(select.dataset.id));
    const idRol = Number(select.value);

    select.disabled = true;
    mensajeUsuarios.textContent = "";

    try {
        const respuesta = await fetch(`/api/usuarios/${usuario.id_usuario}/rol`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ id_rol: idRol })
        });
        const datos = await respuesta.json();

        if (!respuesta.ok) {
            mensajeUsuarios.textContent = datos.error;
            select.value = usuario.id_rol;
            return;
        }

        usuario.id_rol = datos.id_rol;
        mensajeUsuarios.textContent = `${usuario.username} ahora tiene el rol ${select.options[select.selectedIndex].text}`;
    } catch (error) {
        console.error("No se pudo cambiar el rol:", error);
        mensajeUsuarios.textContent = "No se ha podido conectar. Inténtalo más tarde";
        select.value = usuario.id_rol;
    } finally {
        select.disabled = false;
    }
}

async function desactivarUsuario(boton) {
    const usuario = usuarios.find((usuario) => usuario.id_usuario === Number(boton.dataset.id));

    if (!confirm("¿Seguro que quieres desactivar a " + usuario.username + "?")) {
        return;
    }

    boton.disabled = true;
    mensajeUsuarios.textContent = "";

    try {
        const respuesta = await fetch(`/api/usuarios/${usuario.id_usuario}/desactivar`, { method: "POST" });
        const datos = await respuesta.json();

        if (!respuesta.ok) {
            mensajeUsuarios.textContent = datos.error;
            boton.disabled = false;
            return;
        }

        usuario.activo = datos.activo;
        mensajeUsuarios.textContent = `Usuario ${usuario.username} desactivado`;
        pintarUsuarios();
    } catch (error) {
        console.error("No se pudo desactivar el usuario:", error);
        mensajeUsuarios.textContent = "No se ha podido conectar. Inténtalo más tarde";
        boton.disabled = false;
    }
}

async function crearUsuario(evento) {
    evento.preventDefault();

    botonCrearUsuario.disabled = true;
    mensajeCrear.textContent = "";

    try {
        const respuesta = await fetch("/api/usuarios", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
                username: formularioUsuario.username.value.trim(),
                password: formularioUsuario.password.value,
                nombre_completo: formularioUsuario.nombre.value.trim(),
                id_rol: Number(selectRolNuevo.value)
            })
        });
        const datos = await respuesta.json();

        if (!respuesta.ok) {
            mensajeCrear.textContent = datos.error;
            return;
        }

        mensajeCrear.textContent = `Usuario ${datos.username} creado`;
        formularioUsuario.reset();
        cargarUsuarios();
    } catch (error) {
        console.error("No se pudo crear el usuario:", error);
        mensajeCrear.textContent = "No se ha podido conectar. Inténtalo más tarde";
    } finally {
        botonCrearUsuario.disabled = false;
    }
}

function descargarJson(datos, nombreArchivo) {
    const archivo = new Blob([JSON.stringify(datos, null, 4)], { type: "application/json" });
    const enlace = document.createElement("a");

    enlace.href = URL.createObjectURL(archivo);
    enlace.download = nombreArchivo;
    enlace.click();
    URL.revokeObjectURL(enlace.href);
}

async function exportarUsuarios() {
    botonExportar.disabled = true;
    mensajeUsuarios.textContent = "";

    try {
        const respuesta = await fetch("/api/usuarios/exportar", { method: "POST" });
        const datos = await respuesta.json();

        if (!respuesta.ok) {
            mensajeUsuarios.textContent = datos.error;
            return;
        }

        descargarJson(datos, "usuarios_sneaker.json");
        mensajeUsuarios.textContent = `Exportados ${datos.total} usuarios a usuarios_sneaker.json`;
    } catch (error) {
        console.error("No se pudieron exportar los usuarios:", error);
        mensajeUsuarios.textContent = "No se ha podido conectar. Inténtalo más tarde";
    } finally {
        botonExportar.disabled = false;
    }
}

async function iniciarUsuarios() {
    await cargarRoles();
    await cargarUsuarios();
}

if (!esAdmin(usuarioSesion)) {
    window.location.href = "login.html";
} else {
    document.querySelector(".panel__saludo").textContent = "Hola, " + usuarioSesion.nombre;

    iniciarUsuarios();

    cuerpoUsuarios.addEventListener("change", (evento) => {
        if (evento.target.classList.contains("panel__rol")) {
            cambiarRol(evento.target);
        }
    });

    cuerpoUsuarios.addEventListener("click", (evento) => {
        if (evento.target.classList.contains("panel__accion")) {
            desactivarUsuario(evento.target);
        }
    });

    document.querySelector(".panel__recargar").addEventListener("click", cargarUsuarios);

    if (tienePermiso("USUARIOS_EXPORTAR")) {
        botonExportar.addEventListener("click", exportarUsuarios);
    } else {
        botonExportar.remove();
    }
    formularioUsuario.addEventListener("submit", crearUsuario);
}
