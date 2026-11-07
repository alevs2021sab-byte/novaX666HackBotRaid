(function () {
  const form = document.getElementById("form");
  const photo = document.getElementById("photo");
  const preview = document.getElementById("preview");
  const previewImg = document.getElementById("previewImg");
  const previewName = document.getElementById("previewName");
  const clearFileBtn = document.getElementById("clearFile");
  const msg = document.getElementById("msg");
  const wh = document.getElementById("wh");
  const btn = document.getElementById("btn");
  const status = document.getElementById("status");

  let currentFile = null;
  let currentUrl = null;

  function setStatus(kind, text) {
    if (!kind) { status.style.display = "none"; status.textContent = ""; return; }
    status.style.display = "block";
    status.className = "msg " + kind;
    status.textContent = text;
  }

  photo.addEventListener("change", function (e) {
    const f = (e.target.files && e.target.files[0]) || null;
    if (currentUrl) { URL.revokeObjectURL(currentUrl); currentUrl = null; }
    currentFile = f;
    if (!f) { preview.style.display = "none"; return; }
    currentUrl = URL.createObjectURL(f);
    previewImg.src = currentUrl;
    previewName.textContent = f.name;
    preview.style.display = "flex";
  });

  clearFileBtn.addEventListener("click", function () {
    if (currentUrl) { URL.revokeObjectURL(currentUrl); currentUrl = null; }
    currentFile = null;
    photo.value = "";
    preview.style.display = "none";
  });

  form.addEventListener("submit", async function (e) {
    e.preventDefault();
    setStatus(null);

    if (!msg.value.trim()) return setStatus("err", "Mensaje vacío.");
    if (!wh.value.trim()) return setStatus("err", "Webhook obligatorio.");
    if (!/^https:\/\/discord\.com\/api\/webhooks\//i.test(wh.value.trim())) {
      return setStatus("err", "URL de webhook inválida.");
    }

    const fd = new FormData();
    fd.append("message", msg.value);
    fd.append("webhook", wh.value.trim());
    if (currentFile) fd.append("file", currentFile);

    btn.disabled = true;
    const prev = btn.textContent;
    btn.textContent = "enviando…";

    try {
      const res = await fetch("/api/send", { method: "POST", body: fd });
      const data = await res.json().catch(function () { return {}; });
      if (!res.ok) throw new Error(data.error || ("HTTP " + res.status));
      setStatus("ok", "Mensaje entregado al canal.");
      msg.value = "";
      clearFileBtn.click();
    } catch (err) {
      setStatus("err", (err && err.message) ? err.message : "Fallo desconocido");
    } finally {
      btn.disabled = false;
      btn.textContent = prev;
    }
  });
})();
