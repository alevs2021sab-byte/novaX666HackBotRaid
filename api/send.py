from http.server import BaseHTTPRequestHandler
import json
import base64
import time
import requests
from io import BytesIO

BOT_NAME = "666 H4CK"

class handler(BaseHTTPRequestHandler):
    def do_POST(self):
        content_length = int(self.headers.get('Content-Length', 0))
        body = self.rfile.read(content_length)

        try:
            data = json.loads(body)
        except:
            return self._json(400, {"error": "JSON inválido"})

        webhook   = data.get("webhook", "").strip()
        message   = data.get("message", "").strip()
        amount    = data.get("amount", 1)
        image_b64 = data.get("image")
        filename  = data.get("filename") or "image.png"

        if not webhook:
            return self._json(400, {"error": "Webhook obligatorio"})

        if "discord.com/api/webhooks/" not in webhook and "discordapp.com/api/webhooks/" not in webhook:
            return self._json(400, {"error": "Webhook inválido"})

        try:
            amount = int(amount)
        except:
            amount = 1
        amount = max(1, min(amount, 50))

        file_bytes = None
        if image_b64:
            try:
                file_bytes = base64.b64decode(image_b64)
            except:
                return self._json(400, {"error": "Imagen base64 inválida"})

        logs = []
        success = 0
        failed = 0

        for i in range(amount):
            try:
                if file_bytes:
                    files = {
                        "file": (filename, BytesIO(file_bytes), "application/octet-stream")
                    }
                    payload = {
                        "username": BOT_NAME,
                        "content": message if message else None
                    }
                    response = requests.post(
                        webhook,
                        data={"payload_json": json.dumps(payload)},
                        files=files,
                        timeout=15
                    )
                else:
                    payload = {
                        "username": BOT_NAME,
                        "content": message if message else " "
                    }
                    response = requests.post(
                        webhook,
                        json=payload,
                        timeout=15
                    )

                if response.status_code in (200, 204):
                    success += 1
                    logs.append({"msg": f"#{i+1} enviado", "type": "ok"})
                elif response.status_code == 429:
                    failed += 1
                    logs.append({"msg": f"#{i+1} rate-limit 429", "type": "err"})
                    time.sleep(2.0)
                else:
                    failed += 1
                    logs.append({"msg": f"#{i+1} error {response.status_code}", "type": "err"})

            except Exception as e:
                failed += 1
                logs.append({"msg": f"#{i+1} excepción → {str(e)[:80]}", "type": "err"})

            if i < amount - 1:
                time.sleep(0.45)

        return self._json(200, {
            "success": success,
            "failed": failed,
            "logs": logs
        })

    def _json(self, status, obj):
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(json.dumps(obj).encode())

    def do_OPTIONS(self):
        self.send_response(200)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()
