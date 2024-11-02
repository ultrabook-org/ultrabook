const r = document.querySelector(':root');
let theme = "dark";
const themeController = document.getElementById("theme");
themeController.addEventListener("click", changeTheme);

function reset_animation(elementID) {
    const el = document.getElementById(elementID);
    el.style.animation = 'none';
    el.offsetHeight; // Trigger reflow
    el.style.animation = null;
}

function changeTheme() {
    if (theme === "dark") {
        r.style.setProperty('--background', '#f4f3ee');
        r.style.setProperty('--text', '#4a4e69');
        reset_animation("theme");
        themeController.innerHTML = "light_mode";
        theme = "light";
    } else {
        r.style.setProperty('--background', '#4a4e69');
        r.style.setProperty('--text', '#f4f3ee');
        reset_animation("theme");
        themeController.innerHTML = "dark_mode";
        theme = "dark";
    }
}

function switchMode() {
    const toggle = document.getElementById("mode");
    
    if (toggle.checked) {
        window.location.replace(`${window.location.origin}/ingest`)
    } else {
        window.location.replace(window.location.origin)
    }
}