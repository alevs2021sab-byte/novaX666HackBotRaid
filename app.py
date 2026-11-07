# app.py (archivo en la raíz del proyecto, NO dentro de carpeta api/)
# ⚠️ PROPÓSITO ÚNICAMENTE EDUCATIVO
# ADVERTENCIA: EJECUTA ESTE CÓDIGO SÓLO EN SERVIDORES DE DISCORD DONDE SEAS
# ADMINISTRADOR AUTORIZADO. NO LO USES PARA HACER SPAM NI CON WEBHOOKS AJENOS.
# EN ENTORNOS SERVERLESS COMO VERCEL EXISTE LÍMITE DE TIEMPO DE EJECUCIÓN;
# PUEDE INTERRUMPIRSE ANTES DE FINALIZAR TODOS LOS ENVÍOS Y NO DEVOLVER RESPUESTA.

import os
import re
import json
import uuid
import time
import urllib.request
import urllib.error
from flask import Flask, request, jsonify, send_from_directory

app = Flask(__name__)

DISCORD_RE = re.compile(r"^https://discord\.com/api/webhooks/", re.IGNORECASE)
BOT_NAME = "Bot‑Prueba‑Educativa 🔍"
MAX_FILE_BYTES = 8 * 1024 * 1024
MAX_MESSAGE_CHARS = 2000
UA = "Ejemplo‑Educativo‑Flask‑Webhook/1.0"

# Configuración por variable de entorno con límite de seguridad
MIN_COUNT = 1
try:
    MAX_COUNT = int(os.environ.get("WEBHOOK_MAX_COUNT", "60"))
except ValueError:
    MAX_COUNT = 60
MAX_COUNT = min(MAX_COUNT, 60)

try:
    DELAY_BETWEEN_REQUESTS = float(os.environ.get("WEBHOOK_DELAY", "1.2"))
except ValueError:
    DELAY_BETWEEN_REQUESTS = 1.2
DELAY_BETWEEN_REQUESTS = max(DELAY_BETWEEN_REQUESTS, 0.8)

MAX_RETRIES_429 = 2
SAFE_TIMEOUT_SEC = 9.0  # Margen antes del corte (~10 s Vercel gratuito)

def _build_multipart(payload_json: str, file_part):
    boundary = "----EducWebHook" + uuid.uuid4().hex
    parts = []
    parts.append(("--" + boundary).encode())
    parts.append(b'Content-Disposition: form-data; name="payload_json"')
    parts.append(b"Content-Type: application/json")
    parts.append(b"")
    parts.append(payload_json.encode("utf-8"))
    if file_part:
        filename, data, ctype = file_part
        parts.append(("--" + boundary).encode())
        parts.append(
            f'Content-Disposition: form-data; name="files[0]"; filename="{filename}"'.encode()
        )
        parts.append(f"Content-Type: {ctype or 'application/octet-stream'}".encode())
        parts.append(b"")
        parts.append(data)
    parts.append(("--" + boundary + "--").encode())
    parts.append(b"")
    body = b"\r\n".join(parts)
    headers = {"Content-Type": f"multipart/form-data; boundary={boundary}"}
    return headers, body

def _send_single_webhook(webhook_url, payload_json, file_part):
    fwd_headers, fwd_body = _build_multipart(payload_json, file_part)
    fwd_headers["User-Agent"] = UA
    req = urllib.request.Request(
        webhook_url, data=fwd_body, headers=fwd_headers, method="POST"
    )
    attempt = 0
    while attempt <= MAX_RETRIES_429:
        try:
            with urllib.request.urlopen(req, timeout=20) as resp:
                return {"ok": True, "status": resp.getcode()}
        except urllib.error.HTTPError as e:
            if e.code == 429:
                attempt += 1
                retry_after = int(e.headers.get("Retry-After", "2"))
                if attempt > MAX_RETRIES_429:
                    return {"ok": False, "error": "Límite‑de‑tasa persistente (429)", "retry_after": retry_after}
                time.sleep(retry_after)
                continue
            detail = e.read().decode("utf-8", errors="replace")[:200]
            return {"ok": False, "error": f"Discord: {e.code} {detail}"}
        except Exception as exc:
            return {"ok": False, "error": f"Fallo de conexión: {str(exc)[:120]}"}
    return {"ok": False, "error": "Agotados reintentos por límite‑de‑tasa"}

@app.route("/")
def index():
    return send_from_directory("public", "index.html")

@app.route("/style.css")
def style():
    return send_from_directory("public", "style.css")

@app.route("/script.js")
def script():
    return send_from_directory("public", "script.js")

@app.route("/api/send", methods=["POST"])
def send():
    start_time = time.time()

    count_raw = request.form.get("count", str(MIN_COUNT))
    try:
        count = int(count_raw)
    except ValueError:
        return jsonify({"error": "El parámetro count debe ser un número entero."}), 400
    if not (MIN_COUNT <= count <= MAX_COUNT):
        return jsonify({"error": f"count debe estar entre {MIN_COUNT} y {MAX_COUNT}."}), 400

    client_webhook = request.form.get("webhook", "").strip()
    webhook = (os.environ.get("WEBHOOK_URL") or client_webhook).strip()
    message = request.form.get("message", "").strip()
    file = request.files.get("file")

    if not DISCORD_RE.match(webhook):
        return jsonify({"error": "Webhook inválido."}), 400
    if not message:
        return jsonify({"error": "Mensaje requerido."}), 400
    if len(message) > MAX_MESSAGE_CHARS:
        return jsonify({"error": f"Mensaje > {MAX_MESSAGE_CHARS} caracteres."}), 400

    file_part = None
    if file and file.filename:
        data = file.read()
        if len(data) > MAX_FILE_BYTES:
            return jsonify({"error": "Archivo > 8 MB."}), 400
        file_part = (file.filename, data, file.content_type)

    payload_json = json.dumps({
        "username": BOT_NAME,
        "content": message,
        "allowed_mentions": {"parse": []},
    }, ensure_ascii=False)

    results = []
    corte_por_tiempo = False

    for idx in range(count):
        elapsed = time.time() - start_time
        if elapsed >= SAFE_TIMEOUT_SEC:
            corte_por_tiempo = True
            break

        res = _send_single_webhook(webhook, payload_json, file_part)
        results.append(res)

        if idx != count - 1:
            time.sleep(DELAY_BETWEEN_REQUESTS)

    success_count = sum(1 for r in results if r.get("ok"))
    return jsonify({
        "ok": True,
        "solicitados": count,
        "enviados_exitosos": success_count,
        "cantidad_procesada": len(results),
        "advertencia_tiempo": "¡Posible corte por límite‑Vercel! No se terminó la secuencia" if corte_por_tiempo else "Secuencia completada dentro del margen de tiempo",
        "limite_actual": MAX_COUNT,
        "detalles": results
    })

@app.route("/api/send", methods=["GET"])
def health():
    return jsonify({"ok": True, "endpoint": "activo", "limite_count": MAX_COUNT})

if __name__ == "__main__":
    app.run(debug=False)
