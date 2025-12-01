#!/bin/bash
# Script de build para forçar Python 3.11

# Verifica e instala Python 3.11 se necessário
python3.11 --version || {
    echo "Python 3.11 não encontrado, usando versão disponível"
}

# Instala dependências
pip install -r requirements.txt

# Instala Playwright e Chromium
playwright install chromium

