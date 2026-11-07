import os
import re
import json
import uuid
import urllib.request
import urllib.error
from http.server import BaseHTTPRequestHandler
from email.parser import BytesParser
from email.policy import default as email_default

DISCORD_RE = re.compile(r"^https://discord\.com/api/webhooks/", re.IGNORECASE)
BOT_NAME = "666 H4CK ON TOP 🔥"
MAX_FILE_BYTES = 8 * 1024 * 1024
MAX_MESSAGE_CHARS = 2000
UA = "666H4CK-Novadynamics/1.0"


def _json(status: int, payload: dict):
    body = json.dumps(payload).encode("utf-8")
    return status, {"Content-Type": "application/json"}, body


def _parse_multipart(content_type: str, body: bytes):
    """Parse a multipart/form-data body into (fields: dict[str,str], files: dict[str,tuple[filename, bytes, ctype]])."""
    if "boundary=" not in content_type:
        return {}, {}
    boundary = content_type.split("boundary=", 1)[1].strip().strip('"')
    raw = b"Content-Type: " + content_type.encode() + b"\r\n\r\n" + body
    msg = BytesParser(policy=email_default).parsebytes(raw)
    fields, files = {}, {}
    if not msg.is_multipart():
        return fields, files
    for part in msg.iter_parts():
        name = part.get_param("name", header="content-disposition")
        if not name:
            continue
        filename = part.get_filename()
        payload = part.get_payload(decode=True) or b""
        if filename:
            files[name] = (filename, payload, part.get_content_type())
        else:
            fields[name] = payload.decode("utf-8", errors="replace")
    return fields, files


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


class handler(BaseHTTPRequestHandler):
    def do_OPTIONS(self):
        self.send_response(204)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()

    def do_POST(self):
        try:
            length = int(self.headers.get("Content-Length", "0"))
            if length <= 0 or length > MAX_FILE_BYTES + 64 * 1024:
                return self._emit(*_json(400, {"error": "Cuerpo inválido o demasiado grande."}))

            body = self.rfile.read(length)
            ctype = self.headers.get("Content-Type", "")
            if not ctype.startswith("multipart/form-data"):
                return self._emit(*_json(400, {"error": "Se esperaba multipart/form-data."}))

            fields, files = _parse_multipart(ctype, body)

            client_webhook = (fields.get("webhook") or "").strip()
            webhook = (os.environ.get("WEBHOOK_URL") or client_webhook).strip()
            message = (fields.get("message") or "").strip()
            file_part = files.get("file")

            if not DISCORD_RE.match(webhook):
                return self._emit(*_json(400, {"error": "Webhook inválido."}))
            if not message:
                return self._emit(*_json(400, {"error": "Mensaje requerido."}))
            if len(message) > MAX_MESSAGE_CHARS:
                return self._emit(*_json(400, {"error": f"Mensaje > {MAX_MESSAGE_CHARS} caracteres."}))

            if file_part:
                _, data, _ = file_part
                if len(data) > MAX_FILE_BYTES:
                    return self._emit(*_json(400, {"error": "Archivo > 8 MB."}))

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
                    status = resp.status
            except urllib.error.HTTPError as e:
                if e.code == 429:
                    retry = e.headers.get("Retry-After", "?")
                    return self._emit(*_json(429, {"error": f"Rate limit. Reintenta en {retry} s."}))
                detail = e.read().decode("utf-8", errors="replace")[:200]
                return self._emit(*_json(e.code, {"error": f"Discord: {e.code} {detail}"}))
            except Exception:
                return self._emit(*_json(502, {"error": "No se pudo contactar Discord."}))

            if status >= 400:
                return self._emit(*_json(status, {"error": f"Discord: {status}"}))

            return self._emit(*_json(200, {"ok": True}))

        except Exception as exc:
            return self._emit(*_json(500, {"error": f"Error interno: {type(exc).__name__}"}))

    def _emit(self, status, headers, body):
        self.send_response(status)
        for k, v in headers.items():
            self.send_header(k, v)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)
