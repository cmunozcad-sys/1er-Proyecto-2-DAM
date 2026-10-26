const header = document.querySelector(".header__container");

window.addEventListener("scroll", () => {
    header.classList.toggle("header__container--scroll", window.scrollY > 50);
});

const menu = document.querySelector(".lateral__check");
const contenido = document.querySelector(".contenido");

menu.addEventListener("change", () => {
    contenido.classList.toggle("contenido--desplazado", menu.checked);
});