function preferredLang() {
  const saved = localStorage.getItem("maars-lang");
  if (saved === "zh" || saved === "en") return saved;
  return (navigator.language || "en").toLowerCase().startsWith("zh") ? "zh" : "en";
}

function applyLang(lang) {
  document.documentElement.lang = lang;
  document.querySelectorAll("[data-lang-btn]").forEach((button) => {
    button.classList.toggle("active", button.getAttribute("data-lang-btn") === lang);
  });
  localStorage.setItem("maars-lang", lang);
}

function initLang() {
  applyLang(preferredLang());
  document.querySelectorAll("[data-lang-btn]").forEach((button) => {
    button.addEventListener("click", () => applyLang(button.getAttribute("data-lang-btn")));
  });
}

function initScrollspy() {
  const links = Array.from(document.querySelectorAll(".toc a[href^='#']"));
  if (!links.length) return;
  const byId = new Map();
  links.forEach((link) => {
    const target = document.getElementById(link.getAttribute("href").slice(1));
    if (!target) return;
    if (!byId.has(target.id)) byId.set(target.id, []);
    byId.get(target.id).push(link);
  });
  const observer = new IntersectionObserver((entries) => {
    entries.forEach((entry) => {
      if (!entry.isIntersecting) return;
      links.forEach((link) => link.classList.remove("active"));
      (byId.get(entry.target.id) || []).forEach((link) => link.classList.add("active"));
    });
  }, { rootMargin: "-20% 0px -70% 0px", threshold: 0 });
  byId.forEach((_, id) => observer.observe(document.getElementById(id)));
}

document.addEventListener("DOMContentLoaded", () => {
  initLang();
  initScrollspy();
});
