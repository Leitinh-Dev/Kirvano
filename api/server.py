#!/usr/bin/env python3
"""
API Flask para processar cartões Kirvano
Replica exatamente o comportamento do main.py
"""

from flask import Flask, request, jsonify
from flask_cors import CORS
import asyncio
import sys
import os

# Adiciona o diretório raiz ao path para importar o main.py
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from main import KirvanoStealthAutomation

app = Flask(__name__)
CORS(app)

async def process_card_async():
    """Processa um cartão usando a automação Kirvano"""
    try:
        # Valida parâmetros
        lista = request.args.get('lista')
        url = request.args.get('url', 'https://pay.kirvano.com/a88f1635-2808-4bd0-b763-e43d2832299b')
        
        if not lista:
            return jsonify({
                'status': 'error',
                'message': 'Parâmetro lista não fornecido'
            }), 400
        
        # Parse do cartão
        parts = lista.split('|')
        if len(parts) != 4:
            return jsonify({
                'status': 'error',
                'message': 'Formato inválido. Use: número|mês|ano|cvv'
            }), 400
        
        cc, mes, ano, cvv = [p.strip() for p in parts]
        
        # Formata cartão
        cc_clean = cc.replace(' ', '')
        cc_formatted = ' '.join([cc_clean[i:i+4] for i in range(0, len(cc_clean), 4)])
        mes_formatted = mes.zfill(2)
        ano_formatted = ano[-2:] if len(ano) == 4 else ano
        expiration = f"{mes_formatted}/{ano_formatted}"
        
        # Cria instância da automação
        # headless=True força o uso do chromium normal mesmo em modo headless
        automation = KirvanoStealthAutomation(
            headless=True,
            slow_mo=1000,
            url=url,
            user_name="Render_API"
        )
        
        # Gera dados brasileiros
        customer_data = await automation.generate_brazilian_data()
        
        # Prepara dados do cartão
        card_data = {
            "titular": customer_data["nome_completo"],
            "numero": cc_formatted,
            "vencimento": expiration,
            "cvv": cvv
        }
        
        # Executa o teste
        result = await automation._run_single_test_async(card_data, customer_data)
        
        # Formata resposta
        if result == 'SUCCESS':
            return jsonify({
                'status': 'success',
                'message': 'SUCCESS',
                'card_used': {
                    'cc': cc_formatted,
                    'expiration': expiration,
                    'cvv': cvv
                }
            }), 200
        elif isinstance(result, str):
            return jsonify({
                'status': 'success',
                'message': result,
                'card_used': {
                    'cc': cc_formatted,
                    'expiration': expiration,
                    'cvv': cvv
                }
            }), 200
        else:
            return jsonify({
                'status': 'error',
                'message': 'FAILED',
                'card_used': {
                    'cc': cc_formatted,
                    'expiration': expiration,
                    'cvv': cvv
                }
            }), 200
            
    except Exception as e:
        error_message = str(e)
        is_timeout = 'Timeout' in error_message or 'timeout' in error_message.lower()
        
        return jsonify({
            'status': 'error',
            'message': 'TIMEOUT_ERROR' if is_timeout else error_message
        }), 500

# Wrapper para executar função async
def run_async(coro):
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()

@app.route('/api/kirvano', methods=['GET', 'OPTIONS'])
def process_card():
    """Endpoint para processar cartão"""
    if request.method == 'OPTIONS':
        return '', 200
    return run_async(process_card_async())

@app.route('/health', methods=['GET'])
def health():
    """Health check"""
    return jsonify({'status': 'ok'}), 200

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)

