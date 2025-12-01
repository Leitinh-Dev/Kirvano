# 🚀 API Kirvano

API Flask para processar cartões Kirvano usando automação de navegador com Playwright.

## 🚀 Deploy no Render

1. Acesse: https://render.com
2. Login com GitHub → "New +" → "Web Service"
3. Conecte este repositório
4. Configure:
   - **Build:** `pip install -r requirements.txt && playwright install chromium`
   - **Start:** `python api/server.py`
   - **Variável:** `CLOUDFLARE_WORKER_URL=https://kirvano.jcntcleber.workers.dev`

## 📝 Uso

```
GET /api/kirvano?lista=numero|mes|ano|cvv&url=https://pay.kirvano.com/...
```

## 🛠️ Local

```bash
pip install -r requirements.txt
playwright install chromium
python api/server.py
```
