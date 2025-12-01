# 🚀 INSTRUÇÕES DEFINITIVAS - Render Dashboard

## ⚠️ PROBLEMA ATUAL
O Render precisa da versão COMPLETA do Python (major.minor.patch).

## ✅ SOLUÇÃO NO DASHBOARD

### 1. Vá em "Settings" → "Build & Deploy"

### 2. Configure os comandos:

**Build Command:**
```
pip install -r requirements.txt && playwright install chromium
```

**Start Command:**
```
python api/server.py
```

### 3. IMPORTANTE - Versão do Python:

**Procure por:**
- "Python Version"
- "Runtime Version"  
- "Environment"
- "Python Runtime"

**Configure para:** `3.11.9` (VERSÃO COMPLETA!)

**Se não encontrar campo de versão:**
- Vá em "Environment" (menu lateral)
- Adicione variável:
  - Nome: `PYTHON_VERSION`
  - Valor: `3.11.9` (VERSÃO COMPLETA!)

### 4. Salve e aguarde redeploy

## 📝 Arquivos já configurados

- ✅ `runtime.txt` → `python-3.11.9`
- ✅ `render.yaml` → `pythonVersion: "3.11.9"`
- ✅ `.python-version` → `3.11.9`

O Render deve respeitar esses arquivos, mas se não respeitar, configure manualmente no dashboard!
