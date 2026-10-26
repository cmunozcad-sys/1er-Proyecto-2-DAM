const header = document.querySelector(".header__container");

window.addEventListener("scroll", () => {
    header.classList.toggle("header__container--scroll", window.scrollY > 50);
});