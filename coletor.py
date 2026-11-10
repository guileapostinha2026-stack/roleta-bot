import os
from http.server import HTTPServer, BaseHTTPRequestHandler
import threading
import asyncio
from playwright.async_api import async_playwright
import json
import urllib.request
import urllib.parse

# Servidor web falso para manter o Render feliz e ativo
class SimpleHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"Bot da Roleta a funcionar 24/7!")

def run_fake_server():
    port = int(os.environ.get("PORT", 10000))
    server = HTTPServer(("0.0.0.0", port), SimpleHandler)
    server.serve_forever()

# Arranca o servidor web falso numa thread separada
threading.Thread(target=run_fake_server, daemon=True).start()

# Token e Chat ID do Telegram
TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN", "9016660120:AAFdnNRo7NDjIAsbUKA6TX1blNlbgFexD68")
CHAT_ID = "@roletadoguile"

PLACAR_GREENS = 0
PLACAR_REDS = 0

def enviar_telegram(mensagem):
    try:
        url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
        dados = urllib.parse.urlencode({'chat_id': CHAT_ID, 'text': mensagem}).encode('utf-8')
        req = urllib.request.Request(url, data=dados, method='POST')
        with urllib.request.urlopen(req) as resposta:
            return resposta.read()
    except Exception as e:
        print(f"Erro ao enviar para o Telegram: {e}")

def calcular_estrategias_avancadas(num):
    if num == 0:
        return "Zero (Cobertura Total)", "Zero (Cobertura Total)"
    
    if 1 <= num <= 12:
        duzias = "1ª e 2ª Dúzias"
    elif 13 <= num <= 24:
        duzias = "2ª e 3ª Dúzias"
    else:
        duzias = "1ª e 3ª Dúzias"
        
    resto = num % 3
    if resto == 1:
        colunas = "1ª e 2ª Colunas"
    elif resto == 2:
        colunas = "2ª e 3ª Colunas"
    else:
        colunas = "1ª e 3ª Colunas"
        
    return duzias, colunas

async def iniciar_coletor():
    async with async_playwright() as p:
        user_data_dir = os.path.join(os.getcwd(), "user_data_bethor")
        
        print("A iniciar o navegador...")
        browser = await p.chromium.launch_persistent_context(
            user_data_dir=user_data_dir,
            headless=True,
            args=[
                "--disable-blink-features=AutomationControlled",
                "--no-sandbox",
                "--disable-infobars",
                "--disable-dev-shm-usage",
                "--disable-gpu"
            ],
            ignore_default_args=["--enable-automation"]
        )
        
        page = await browser.new_page()

        ultimo_enviado = None
        sinal_ativo = None

        async def monitorizar_websocket(ws):
            async def ao_receber(msg):
                nonlocal ultimo_enviado, sinal_ativo
                global PLACAR_GREENS, PLACAR_REDS
                try:
                    if isinstance(msg, str):
                        data = json.loads(msg)
                    else:
                        data = json.loads(msg.decode('utf-8', errors='ignore'))
                
                    def procurar_chaves(obj):
                        nonlocal ultimo_enviado, sinal_ativo
                        global PLACAR_GREENS, PLACAR_REDS
                        if isinstance(obj, dict):
                            for k, v in obj.items():
                                if k in ["winningNumber", "resultNumber", "number", "outcome"] and v is not None:
                                    numero_str = str(v)
                                    if numero_str != ultimo_enviado and numero_str.isdigit() and 0 <= int(numero_str) <= 36:
                                        ultimo_enviado = numero_str
                                        num_int = int(numero_str)
                                        print(f"🎯 [NÚMERO VENCEDOR] >>> {numero_str} <<<")
                                        
                                        duzias_calc, colunas_calc = calcular_estrategias_avancadas(num_int)

                                        # Validação de Green / Red anterior
                                        if sinal_ativo is not None:
                                            alvos_d = sinal_ativo["duzias"]
                                            alvos_c = sinal_ativo["colunas"]
                                            
                                            acertou_duzia = False
                                            if "1ª e 2ª" in alvos_d and 1 <= num_int <= 24: acertou_duzia = True
                                            elif "2ª e 3ª" in alvos_d and 13 <= num_int <= 36: acertou_duzia = True
                                            elif "1ª e 3ª" in alvos_d and (1 <= num_int <= 12 or 25 <= num_int <= 36): acertou_duzia = True
                                            
                                            acertou_coluna = False
                                            if "1ª e 2ª" in alvos_c and num_int > 0 and num_int % 3 in [1, 2]: acertou_coluna = True
                                            elif "2ª e 3ª" in alvos_c and num_int > 0 and num_int % 3 in [2, 0]: acertou_coluna = True
                                            elif "1ª e 3ª" in alvos_c and num_int > 0 and num_int % 3 in [1, 0]: acertou_coluna = True

                                            deu_green = (num_int == 0) or acertou_duzia or acertou_coluna
                                            
                                            if deu_green:
                                                PLACAR_GREENS += 1
                                                texto_resultado = f"✅ GREEN! Resultado: {numero_str} 🟢\n📊 Placar Atual ➔ ✅: {PLACAR_GREENS} | ❌: {PLACAR_REDS}"
                                            else:
                                                PLACAR_REDS += 1
                                                texto_resultado = f"❌ RED. Resultado: {numero_str} 🔴\n📊 Placar Atual ➔ ✅: {PLACAR_GREENS} | ❌: {PLACAR_REDS}"
                                            
                                            enviar_telegram(texto_resultado)
                                            print(f"📤 Resultado enviado: {texto_resultado}")
                                            sinal_ativo = None

                                        # Novo sinal formatado sem Gale e limpo
                                        sinal_ativo = {
                                            "duzias": duzias_calc,
                                            "colunas": colunas_calc
                                        }

                                        texto_sinal = (
                                            "🏛️ ENTRADA CONFIRMADA 🏛️\n"
                                            "🎰 Roleta Immersive\n"
                                            f"🎯 Número Base: {numero_str}\n"
                                            f"📊 Sugestão: Entrar em {duzias_calc} e {colunas_calc}\n"
                                            "🟢 Cobrir o ZERO\n"
                                            "⚡ Sem Gale"
                                        )
                                        
                                        enviar_telegram(texto_sinal)
                                        print("📤 Novo sinal enviado com sucesso!")
                                    procurar_chaves(v)
                        elif isinstance(obj, list):
                            for item in obj:
                                procurar_chaves(item)

                    procurar_chaves(data)
                except Exception:
                    pass

            ws.on("framereceived", ao_receber)

        page.on("websocket", monitorizar_websocket)

        url_mesa = "https://bethor.bet/games/play/17879/GPKEVO_3976fc70a2fe57793809ef3c7c577a1b"
        print(f"A aceder à mesa: {url_mesa}")
        await page.goto(url_mesa, timeout=60000)

        while True:
            try:
                for frame in page.frames:
                    await frame.evaluate("""() => {
                        const botoes = Array.from(document.querySelectorAll('button, div, span, a'));
                        for (let btn of botoes) {
                            if (btn.innerText.trim().toUpperCase() === 'CLOSE') {
                                btn.click();
                            }
                        }
                    }""")
            except:
                pass
            await asyncio.sleep(5)

if __name__ == "__main__":
    asyncio.run(iniciar_coletor())
