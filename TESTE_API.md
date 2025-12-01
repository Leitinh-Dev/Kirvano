# 🧪 Como Testar a API

## 📋 Dados do Teste

- **URL Kirvano**: `https://pay.kirvano.com/e0dd0498-3c81-4249-b14e-f3eee05927e7`
- **Cartão**: `4984424545308961|11|2028|394`

## 🌐 Opção 1: Teste via Navegador/Postman

URL completa para teste:

```
https://kirvano-m9ra.onrender.com/api/kirvano?lista=4984424545308961|11|2028|394&url=https://pay.kirvano.com/e0dd0498-3c81-4249-b14e-f3eee05927e7
```

## 🐍 Opção 2: Teste via Script Python

1. Execute diretamente:
```bash
python test_api.py
```

## 📝 Opção 3: Teste via cURL

```bash
curl "https://kirvano-m9ra.onrender.com/api/kirvano?lista=4984424545308961|11|2028|394&url=https://pay.kirvano.com/e0dd0498-3c81-4249-b14e-f3eee05927e7"
```

## ⚠️ Importante

- O teste pode levar até 2 minutos (timeout de 120s)
- Certifique-se de que o deploy no Render está completo
- Verifique primeiro o `/health` para confirmar que o servidor está rodando

## ✅ Health Check

Teste primeiro se o servidor está rodando:
```
https://kirvano-m9ra.onrender.com/health
```

Deve retornar: `{"status": "ok"}`

