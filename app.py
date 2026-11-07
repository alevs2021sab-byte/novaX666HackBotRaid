import os
import re
import json
import uuid
import urllib.request
import urllib.error
from flask import Flask, request, jsonify, send_from_directory

app = Flask(__name__)

DISCORD_RE = re.compile(r"^https://discord\.com/api/webhooks/", re.IGNORECASE)
BOT_NAME = "666 H4CK ON TOP 🔥"
MAX_FILE_BYTES = 8 * 1024 * 1024
MAX_MESSAGE_CHARS = 2000
UA = "666H4CK-Novadynamics/1.0"

def _build_multipart(payload_json: str, file_part):
    boundary = "----666H4CK" + uuid.uuid4().hex
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
            return jsonify({"error": "Archivo > 8 MB."}), 400
        file_part = (file.filename, data, file.content_type)

    payload_json = json.dumps({
        "username": BOT_NAME,
        "content": message,
        "allowed_mentions": {"parse": []},
    }, ensure_ascii=False)

    fwd_headers, fwd_body = _build_multipart(payload_json, file_part)
    fwd_headers["User-Agent"] = UA

    req = urllib.request.Request(webhook, data=fwd_body, headers=fwd_headers, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=20) as resp:
            pass
    except urllib.error.HTTPError as e:
        if e.code == 429:
            retry = e.headers.get("Retry-After", "?")
            return jsonify({"error": f"Rate limit. Reintenta en {retry} s."}), 429
        detail = e.read().decode("utf-8", errors="replace")[:200]
        return jsonify({"error": f"Discord: {e.code} {detail}"}), e.code
    except Exception:
        return jsonify({"error": "No se pudo contactar Discord."}), 502

    return jsonify({"ok": True})

@app.route("/api/send", methods=["GET"])
def health():
    return jsonify({"ok": True, "endpoint": "activo"})
