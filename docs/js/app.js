// Frontend de notiemoji: generador de wallpapers dinámico.

import { API_URL } from "./config.js";

const form = document.getElementById("form");
const generar = document.getElementById("generar");
const previewImg = document.getElementById("preview-img");
const previewVacio = document.getElementById("preview-vacio");
const previewContainer = document.getElementById("preview-container");
const descargar = document.getElementById("descargar");
const paletteSelect = document.getElementById("palette");
const fontSizeInput = document.getElementById("font_size");
const fontSizeVal = document.getElementById("font_size_val");
const colorInput = document.getElementById("color");
const colorPicker = document.getElementById("color-picker");
const textColorInput = document.getElementById("text_color");
const textColorPicker = document.getElementById("text-color-picker");
const presetBtns = document.querySelectorAll(".btn-mini");

let blobUrl = null;

// Toasts
function mostrarToast(titulo, mensaje, tono = "ok") {
  const toasts = document.getElementById("toasts");
  const toast = document.createElement("div");
  toast.className = `toast${tono === "error" ? " toast-error" : ""}`;
  toast.setAttribute("role", tono === "error" ? "alert" : "status");

  const cerrar = document.createElement("button");
  cerrar.className = "toast-cerrar";
  cerrar.textContent = "×";
  cerrar.setAttribute("aria-label", "Cerrar");
  cerrar.onclick = () => toast.remove();

  toast.append(cerrar, titulo + ": " + mensaje);
  toasts.prepend(toast);

  if (tono === "ok") {
    setTimeout(() => toast.remove(), 6000);
  }
}

// Cargar paletas
const PALETTES = {};

async function cargarPaletas() {
  try {
    const res = await fetch(`${API_URL}/paletas`);
    if (!res.ok) return;
    for (const { nombre, color, texto } of await res.json()) {
      PALETTES[nombre] = [color, texto];
      const opcion = document.createElement("option");
      opcion.value = nombre;
      opcion.textContent = nombre;
      paletteSelect.append(opcion);
    }
  } catch (_) {}
}

// Actualizar colores al cambiar paleta (solo cuando el usuario selecciona manualmente)
let actualizandoDesdePaleta = false;
paletteSelect.addEventListener("change", () => {
  if (actualizandoDesdePaleta) return;
  const pareja = PALETTES[paletteSelect.value];
  if (pareja) {
    actualizandoDesdePaleta = true;
    colorInput.value = pareja[0];
    colorPicker.value = pareja[0];
    textColorInput.value = pareja[1];
    textColorPicker.value = pareja[1];
    actualizandoDesdePaleta = false;
  }
});

// Sincronizar color pickers con inputs de texto
function sincronizarColor(picker, input) {
  picker.addEventListener("input", () => {
    input.value = picker.value;
    actualizandoDesdePaleta = true;
    paletteSelect.value = "";
    actualizandoDesdePaleta = false;
  });
  input.addEventListener("input", () => {
    if (/^#[0-9a-f]{6}$/i.test(input.value)) picker.value = input.value;
    actualizandoDesdePaleta = true;
    paletteSelect.value = "";
    actualizandoDesdePaleta = false;
  });
}

sincronizarColor(colorPicker, colorInput);
sincronizarColor(textColorPicker, textColorInput);

// Actualizar label de tamaño de fuente
fontSizeInput.addEventListener("input", () => {
  fontSizeVal.textContent = fontSizeInput.value + "px";
});

// Presets de tamaño
presetBtns.forEach(btn => {
  btn.addEventListener("click", () => {
    presetBtns.forEach(b => b.classList.remove("activo"));
    btn.classList.add("activo");
    document.getElementById("width").value = btn.dataset.w;
    document.getElementById("height").value = btn.dataset.h;
  });
});

// Generar wallpaper
form.addEventListener("submit", async (e) => {
  e.preventDefault();
  generar.disabled = true;

  const datos = new FormData(form);
  const payload = {
    width: Number(datos.get("width")),
    height: Number(datos.get("height")),
    font_size: Number(datos.get("font_size")),
    text: String(datos.get("text") ?? ""),
    bold: datos.get("bold") === "on",
    italic: datos.get("italic") === "on",
  };
  
  const color = String(datos.get("color") ?? "").trim();
  const textColor = String(datos.get("text_color") ?? "").trim();
  const palette = String(datos.get("palette") ?? "").trim();
  
  if (color) payload.color = color;
  if (textColor) payload.text_color = textColor;
  if (palette) payload.palette = palette;

  mostrarToast("Enviando", `Generando wallpaper...`);

  try {
    const res = await fetch(`${API_URL}/wallpaper`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });

    if (!res.ok) {
      const data = await res.json().catch(() => null);
      const msg = data?.detail ?? `Error ${res.status}`;
      mostrarToast("Error", msg, "error");
      return;
    }

    const blob = await res.blob();
    if (blobUrl) URL.revokeObjectURL(blobUrl);
    blobUrl = URL.createObjectURL(blob);
    previewImg.src = blobUrl;
    previewImg.hidden = false;
    descargar.href = blobUrl;
    previewVacio.hidden = true;
    previewContainer.hidden = false;
    mostrarToast("Listo", "Wallpaper generado");
  } catch (err) {
    mostrarToast("Error", `No se pudo contactar la API: ${err.message}`, "error");
  } finally {
    generar.disabled = false;
  }
});

cargarPaletas();