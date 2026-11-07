(function () {
  const form = document.getElementById("form");
  const photo = document.getElementById("photo");
  const dropZone = document.getElementById("dropZone");
  const dropContent = document.getElementById("dropContent");
  const preview = document.getElementById("preview");
  const previewImg = document.getElementById("previewImg");
  const previewName = document.getElementById("previewName");
  const clearFileBtn = document.getElementById("clearFile");
  const msg = document.getElementById("msg");
  const charCount = document.getElementById("charCount");
  const wh = document.getElementById("wh");
  const whIcon = document.getElementById("whIcon");
  const btn = document.getElementById("btn");
  const btnText = btn.querySelector(".btn-text");
  const spinner = document.getElementById("spinner");
  const status = document.getElementById("status");

  let currentFile = null;
  let currentUrl = null;

  // --- Utilidades UI ---
  function setStatus(kind, text) {
    if (!kind) { status.style.display = "none"; status.textContent = ""; return; }
    status.style.display = "block";
    status.className = "msg-box " + kind;
    status.textContent = text;
  }

  function updateCharCount() {
    charCount.textContent = msg.value.length;
  }

  function validateWebhook() {
    const val = wh.value.trim();
    if (!val) {
      whIcon.className = "validation-icon";
    } else if (/^https:\/\/discord\.com\/api\/webhooks\//i.test(val)) {
      whIcon.className = "validation-icon valid";
    } else {
      whIcon.className = "validation-icon invalid";
    }
  }

  // --- Lógica de Archivo (Drag & Drop) ---
  function handleFile(file) {
    if (!file) return;
    if (!file.type.startsWith("image/")) {
      setStatus("err", "El archivo debe ser una imagen.");
      return;
    }
    if (file.size > 8 * 1024 * 1024) {
      setStatus("err", "La imagen supera los 8 MB.");
      return;
    }
    
    if (currentUrl) { URL.revokeObjectURL(currentUrl); }
    currentFile = file;
    currentUrl = URL.createObjectURL(file);
    
    previewImg.src = currentUrl;
    previewName.textContent = file.name;
    
    dropContent.style.display = "none";
    preview.style.display = "flex";
    setStatus(null);
  }

  function clearFile() {
    if (currentUrl) { URL.revokeObjectURL(currentUrl); currentUrl = null; }
    currentFile = null;
    photo.value = "";
    preview.style.display = "none";
    dropContent.style.display = "flex";
  }

  // --- Event Listeners ---
  msg.addEventListener("input", updateCharCount);
  wh.addEventListener("input", validateWebhook);

  photo.addEventListener("change", (e) => handleFile(e.target.files[0]));

  ["dragenter", "dragover"].forEach(evt => {
    dropZone.addEventListener(evt, (e) => {
      e.preventDefault();
      dropZone.classList.add("dragover");
    });
  });
  ["dragleave", "drop"].forEach(evt => {
    dropZone.addEventListener(evt, (e) => {
      e.preventDefault();
      dropZone.classList.remove("dragover");
    });
  });
  dropZone.addEventListener("drop", (e) => {
    if (e.dataTransfer.files && e.dataTransfer.files.length > 0) {
      handleFile(e.dataTransfer.files[0]);
    }
  });

  clearFileBtn.addEventListener("click", (e) => {
    e.stopPropagation(); // Evita que se abra el explorador de archivos
    clearFile();
  });

  // --- Envío del Formulario ---
  form.addEventListener("submit", async (e) => {
    e.preventDefault();
    setStatus(null);

    if (!msg.value.trim()) return setStatus("err", "El mensaje no puede estar vacío.");
    if (!wh.value.trim()) return setStatus("err", "El Webhook es obligatorio.");
    if (!/^https:\/\/discord\.com\/api\/webhooks\//i.test(wh.value.trim())) {
      return setStatus("err", "La URL del webhook no es válida.");
    }

    const fd = new FormData();
    fd.append("message", msg.value);
    fd.append("webhook", wh.value.trim());
    if (currentFile) fd.append("file", currentFile);

    // Estado de carga
    btn.disabled = true;
    btnText.textContent = "ENVIANDO...";
    spinner.style.display = "block";

    try {
      const res = await fetch("/api/send", { method: "POST", body: fd });
      const data = await res.json().catch(() => ({}));
      
      if (!res.ok) throw new Error(data.error || `Error ${res.status}`);
      
      setStatus("ok", "Mensaje entregado con éxito.");
      msg.value = "";
      updateCharCount();
      clearFile();
    } catch (err) {
      setStatus("err", err.message || "Fallo de conexión.");
    } finally {
      btn.disabled = false;
      btnText.textContent = "START";
      spinner.style.display = "none";
    }
  });
})();
