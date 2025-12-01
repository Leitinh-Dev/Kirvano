#!/usr/bin/env python3
"""
Script de teste para a API Kirvano
"""

import requests
import urllib.parse

# URL da API
API_URL = "https://kirvano-m9ra.onrender.com/api/kirvano"

# Dados do teste
lista = "4984424545308961|11|2028|394"
url_kirvano = "https://pay.kirvano.com/e0dd0498-3c81-4249-b14e-f3eee05927e7"

# Monta a URL com parâmetros
params = {
    'lista': lista,
    'url': url_kirvano
}

print("=" * 60)
print("TESTE API KIRVANO")
print("=" * 60)
print(f"Cartão: {lista}")
print(f"URL Kirvano: {url_kirvano}")
print(f"API URL: {API_URL}")
print("=" * 60)
print("\nEnviando requisição...\n")

try:
    response = requests.get(API_URL, params=params, timeout=120)
    
    print(f"Status HTTP: {response.status_code}")
    print(f"Resposta: {response.json()}")
    
    if response.status_code == 200:
        data = response.json()
        print("\n" + "=" * 60)
        print("RESULTADO:")
        print("=" * 60)
        print(f"Status: {data.get('status')}")
        print(f"Mensagem: {data.get('message')}")
        if 'card_used' in data:
            print(f"Cartão usado: {data['card_used']}")
        print("=" * 60)
    else:
        print(f"\nErro: {response.status_code}")
        print(response.text)
        
except requests.exceptions.Timeout:
    print("\n❌ TIMEOUT: A requisição demorou mais de 120 segundos")
except requests.exceptions.RequestException as e:
    print(f"\n❌ ERRO na requisição: {e}")
except Exception as e:
    print(f"\n❌ ERRO: {e}")

