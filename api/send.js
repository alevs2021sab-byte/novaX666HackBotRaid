export default async function handler(req, res) {
  // CORS
  res.setHeader('Access-Control-Allow-Origin', '*');
  res.setHeader('Access-Control-Allow-Methods', 'POST, OPTIONS');
  res.setHeader('Access-Control-Allow-Headers', 'Content-Type');

  if (req.method === 'OPTIONS') {
    return res.status(200).end();
  }

  if (req.method !== 'POST') {
    return res.status(405).json({ error: 'Method not allowed' });
  }

  const { webhook, message, amount, image, filename } = req.body || {};

  if (!webhook) {
    return res.status(400).json({ error: 'Webhook obligatorio' });
  }

  if (!webhook.includes('discord.com/api/webhooks/') && !webhook.includes('discordapp.com/api/webhooks/')) {
    return res.status(400).json({ error: 'Webhook inválido' });
  }

  let count = parseInt(amount) || 1;
  count = Math.max(1, Math.min(count, 50));

  const BOT_NAME = '666 H4CK';
  const logs = [];
  let success = 0;
  let failed = 0;

  for (let i = 0; i < count; i++) {
    try {
      let response;

      if (image) {
        // Con imagen (multipart)
        const form = new FormData();
        const payload = {
          username: BOT_NAME,
          content: message || undefined
        };
        form.append('payload_json', JSON.stringify(payload));

        // Convertir base64 a Blob
        const binary = Buffer.from(image, 'base64');
        const blob = new Blob([binary]);
        form.append('files[0]', blob, filename || 'image.png');

        response = await fetch(webhook, {
          method: 'POST',
          body: form
        });
      } else {
        // Solo texto
        response = await fetch(webhook, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            username: BOT_NAME,
            content: message || ' '
          })
        });
      }

      if (response.status === 200 || response.status === 204) {
        success++;
        logs.push({ msg: `#${i + 1} enviado`, type: 'ok' });
      } else if (response.status === 429) {
        failed++;
        logs.push({ msg: `#${i + 1} rate-limit 429`, type: 'err' });
        await new Promise(r => setTimeout(r, 2000));
      } else {
        failed++;
        logs.push({ msg: `#${i + 1} error ${response.status}`, type: 'err' });
      }
    } catch (err) {
      failed++;
      logs.push({ msg: `#${i + 1} excepción → ${err.message.slice(0, 80)}`, type: 'err' });
    }

    if (i < count - 1) {
      await new Promise(r => setTimeout(r, 450));
    }
  }

  return res.status(200).json({
    success,
    failed,
    logs
  });
                           }
