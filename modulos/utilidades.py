"""
Módulo de UTILIDADES da assistente M.A.D.A.R.A.

Reúne funcionalidades independentes:
    - Itens 4, 5 e 6: hora atual, dia atual e calculadora por voz.
    - Item 10 (extras): cotação do dólar e do bitcoin, previsão do tempo,
      pesquisa no Google, abrir vídeo no YouTube, tirar print da tela,
      aumentar/diminuir o volume e abrir o portal da faculdade.
"""

import datetime
import webbrowser
import urllib.parse

import requests


class Utilidades:
    """Agrupa comandos utilitários diversos da assistente."""

    # Meses e dias da semana por extenso, para respostas mais naturais.
    MESES = [
        "janeiro", "fevereiro", "março", "abril", "maio", "junho",
        "julho", "agosto", "setembro", "outubro", "novembro", "dezembro",
    ]
    DIAS_SEMANA = [
        "segunda-feira", "terça-feira", "quarta-feira", "quinta-feira",
        "sexta-feira", "sábado", "domingo",
    ]

    # ------------------------------------------------------------------ #
    #  Itens 4 e 5: hora e data
    # ------------------------------------------------------------------ #
    def hora_atual(self) -> str:
        """Retorna a hora atual em texto (ex.: 'São 14 horas e 30 minutos')."""
        agora = datetime.datetime.now()
        return f"Agora são {agora.hour} horas e {agora.minute} minutos."

    def data_atual(self) -> str:
        """Retorna o dia atual por extenso."""
        hoje = datetime.datetime.now()
        dia_semana = self.DIAS_SEMANA[hoje.weekday()]
        mes = self.MESES[hoje.month - 1]
        return f"Hoje é {dia_semana}, dia {hoje.day} de {mes} de {hoje.year}."

    # ------------------------------------------------------------------ #
    #  Item 6: calculadora por voz
    # ------------------------------------------------------------------ #
    def calcular(self, frase: str) -> str:
        """
        Interpreta um comando falado de cálculo e devolve o resultado.

        Aceita tanto símbolos ('2 + 3') quanto palavras
        ('calcular 2 mais 3', 'dividido por', 'vezes', etc.).
        Suporta as 4 operações básicas exigidas pelo desafio.
        """
        # Remove a palavra "calcular" e normaliza os operadores por extenso.
        texto = frase.lower().replace("calcular", "")
        substituicoes = {
            "mais": "+",
            "somar": "+",
            "menos": "-",
            "subtrair": "-",
            "vezes": "*",
            "multiplicado por": "*",
            "multiplicar por": "*",
            "x": "*",
            "dividido por": "/",
            "dividir por": "/",
            "por": "/",
        }
        for palavra, simbolo in substituicoes.items():
            texto = texto.replace(palavra, f" {simbolo} ")

        # Mantém apenas números e operadores para uma avaliação segura.
        permitidos = "0123456789+-*/(). "
        expressao = "".join(c for c in texto if c in permitidos).strip()

        if not expressao:
            return "Não entendi a conta. Tente algo como 'calcular 5 mais 3'."

        try:
            resultado = eval(expressao)  # expressão já filtrada e segura
            return f"O resultado de {expressao} é {resultado}."
        except Exception:
            return "Não consegui realizar esse cálculo."

    # ------------------------------------------------------------------ #
    #  Item 10: cotações (dólar e bitcoin)
    # ------------------------------------------------------------------ #
    def cotacao_dolar(self) -> str:
        """Consulta a cotação do dólar (API pública AwesomeAPI)."""
        try:
            dados = requests.get(
                "https://economia.awesomeapi.com.br/last/USD-BRL", timeout=10
            ).json()
            valor = float(dados["USDBRL"]["bid"])
            return f"O dólar está cotado a {valor:.2f} reais."
        except Exception:
            return "Não consegui consultar a cotação do dólar agora."

    def cotacao_bitcoin(self) -> str:
        """Consulta a cotação do bitcoin em reais (API pública AwesomeAPI)."""
        try:
            dados = requests.get(
                "https://economia.awesomeapi.com.br/last/BTC-BRL", timeout=10
            ).json()
            valor = float(dados["BTCBRL"]["bid"])
            return f"Um bitcoin vale aproximadamente {valor:,.2f} reais."
        except Exception:
            return "Não consegui consultar a cotação do bitcoin agora."

    # ------------------------------------------------------------------ #
    #  Item 10: previsão do tempo
    # ------------------------------------------------------------------ #
    def previsao_tempo(self, cidade: str = "São Paulo") -> str:
        """
        Consulta o tempo atual de uma cidade usando a API gratuita
        wttr.in (não requer chave).
        """
        try:
            cidade_url = urllib.parse.quote(cidade)
            url = f"https://wttr.in/{cidade_url}?format=j1"
            dados = requests.get(url, timeout=10).json()
            atual = dados["current_condition"][0]
            temp = atual["temp_C"]
            desc = atual["lang_pt"][0]["value"] if "lang_pt" in atual else atual["weatherDesc"][0]["value"]
            return f"Em {cidade} agora está {temp} graus, {desc}."
        except Exception:
            return f"Não consegui obter a previsão do tempo para {cidade}."

    # ------------------------------------------------------------------ #
    #  Item 10: navegação / integrações com o navegador
    # ------------------------------------------------------------------ #
    def pesquisar_google(self, termo: str) -> str:
        """Abre o navegador com uma pesquisa no Google."""
        termo_url = urllib.parse.quote(termo)
        webbrowser.open(f"https://www.google.com/search?q={termo_url}")
        return f"Pesquisando por {termo} no Google."

    def abrir_youtube(self, termo: str) -> str:
        """Abre o YouTube já pesquisando (ou tocando) um vídeo sobre o termo."""
        termo_url = urllib.parse.quote(termo)
        webbrowser.open(f"https://www.youtube.com/results?search_query={termo_url}")
        return f"Abrindo o YouTube com vídeos sobre {termo}."

    def abrir_portal_faculdade(self) -> str:
        """Abre o portal do aluno da faculdade."""
        webbrowser.open("https://www.fiap.com.br/graduacao/on/")
        return "Abrindo o portal da faculdade."

    # ------------------------------------------------------------------ #
    #  Item 10: sistema (print da tela e volume)
    # ------------------------------------------------------------------ #
    def tirar_print(self, arquivo: str = "print_tela.png") -> str:
        """Tira um print da tela e salva em arquivo (usa 'pyautogui')."""
        try:
            import pyautogui

            imagem = pyautogui.screenshot()
            imagem.save(arquivo)
            return f"Print da tela salvo como {arquivo}."
        except ImportError:
            # O pyscreeze (usado pelo pyautogui) depende do Pillow, mas NÃO o
            # declara como dependência. A mensagem original do PyAutoGUI culpa
            # a versão do Python, o que despista.
            return (
                "Não consegui tirar o print: falta a biblioteca Pillow. "
                "Instale com: pip install Pillow"
            )
        except Exception as erro:
            texto = str(erro)
            if "could not create image" in texto or "screencapture" in texto:
                # No macOS o print é feito pelo comando 'screencapture', que
                # falha sem a permissão de Gravação de Tela.
                return (
                    "Não consegui tirar o print: falta a permissão de Gravação "
                    "de Tela. Abra Ajustes do Sistema, Privacidade e Segurança, "
                    "Gravação de Tela, e autorize o aplicativo que está rodando "
                    "o Python (Terminal ou VS Code). Depois reinicie esse app."
                )
            return f"Não consegui tirar o print: {erro}."

    def ajustar_volume(self, aumentar: bool = True, passos: int = 5) -> str:
        """
        Aumenta ou diminui o volume do sistema (Windows) simulando as
        teclas de mídia com 'pyautogui'.
        """
        try:
            import pyautogui

            tecla = "volumeup" if aumentar else "volumedown"
            for _ in range(passos):
                pyautogui.press(tecla)
            return "Volume aumentado." if aumentar else "Volume diminuído."
        except Exception as erro:
            return f"Não consegui ajustar o volume: {erro}."
