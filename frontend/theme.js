const savedTheme = localStorage.getItem("simulator-theme");
const systemTheme = matchMedia("(prefers-color-scheme: dark)");
const root = document.documentElement;
root.dataset.theme = savedTheme || (systemTheme.matches ? "dark" : "light");

document.addEventListener("DOMContentLoaded", () => {
  const toggle = document.querySelector("#theme-toggle");
  const update = () => toggle.setAttribute("aria-pressed", root.dataset.theme === "dark");
  update();
  toggle.addEventListener("click", () => {
    root.dataset.theme = root.dataset.theme === "dark" ? "light" : "dark";
    localStorage.setItem("simulator-theme", root.dataset.theme);
    update();
  });
});
