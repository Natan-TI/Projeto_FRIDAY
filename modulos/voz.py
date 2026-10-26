"""
Módulo de VOZ da assistente M.A.D.A.R.A.

Responsável por:
    - Reconhecer comandos de voz (Speech-to-Text) usando a API do Google
      através da biblioteca 'speech_recognition'.
    - Sintetizar respostas em áudio (Text-to-Speech). Suporta dois motores:
        * 'edge'    -> voz de PERSONAGEM (grave/sombria, estilo Madara Uchiha)
                       usando o edge-tts (gratuito, sem chave de API).
        * 'pyttsx3' -> voz padrão do sistema, 100% offline (fallback).

Baseado nos códigos do professor:
    - reconhecedor.py  (speech_recognition + recognize_google)
    - sintetizador1.py (pyttsx3)
    - sintetizador2.py (gTTS + pygame -> reaproveitado aqui para tocar o mp3)

Como funciona a voz "assustadora":
    O edge-tts permite ajustar o TOM (pitch) e a VELOCIDADE (rate) da fala.
    Usamos uma voz masculina em português e abaixamos o tom para dar aquele
    ar grave e ameaçador. Ajuste os valores em EDGE_PITCH / EDGE_RATE (abaixo
    ou no arquivo .env) para deixar do seu gosto.
"""

import os
import asyncio
import tempfile
import time
from contextlib import ExitStack, contextmanager

import speech_recognition as sr

from .config import obter_variavel


class Voz:
    """Encapsula tudo que envolve ouvir e falar da assistente."""

    def __init__(
        self,
        idioma: str = "pt-BR",
        taxa_fala: int = 190,
        motor: str = "auto",
        arduino=None,
    ):
        """
        Parâmetros:
            idioma    -> idioma usado no reconhecimento e na síntese.
            taxa_fala -> velocidade da fala (só usada no motor pyttsx3).
            motor     -> 'auto' (tenta a voz de personagem e cai no pyttsx3 se
                         faltar internet/biblioteca), 'edge' ou 'pyttsx3'.
            arduino   -> objeto Arduino (opcional). Se informado, os olhos do
                         boneco acendem durante cada fala.
        """
        self.idioma = idioma
        self.taxa_fala = taxa_fala
        self.arduino = arduino

        # Reconhecedor de fala (Speech-to-Text).
        self.reconhecedor = sr.Recognizer()

        # ----- Ajustes para ele não cortar a frase no meio -----
        # pause_threshold: quanto tempo de SILÊNCIO encerra a frase. O padrão
        # da biblioteca é 0.8s, curto demais para frases como "cadastrar
        # evento reunião com o grupo na terça" - qualquer pausa para respirar
        # já era interpretada como fim da fala.
        self.reconhecedor.pause_threshold = 1.8

        # non_speaking_duration precisa ser <= pause_threshold, senão a
        # biblioteca levanta erro.
        self.reconhecedor.non_speaking_duration = 0.6

        # dynamic_energy_threshold: com True (padrão) o limiar de "o que é
        # voz" é recalculado DURANTE a fala. Numa pausa curta ele sobe, e o
        # resto da sua frase passa a ser tratado como ruído de fundo. É a
        # principal causa do corte precoce - desligamos e calibramos uma vez.
        self.reconhecedor.dynamic_energy_threshold = False

        # Marca se o microfone já foi calibrado (feito só na 1a escuta).
        self._ruido_calibrado = False

        # ----- Configuração da voz de personagem (edge-tts) -----
        # Voz masculina PT-BR. Pitch/rate negativos = mais grave e mais lento.
        self.edge_voz = obter_variavel("EDGE_VOICE", "pt-BR-AntonioNeural")
        self.edge_pitch = obter_variavel("EDGE_PITCH", "-20Hz")  # tom (grave)
        self.edge_rate = obter_variavel("EDGE_RATE", "+10%")      # velocidade
        self.motor = motor if motor != "auto" else "edge"

        # Voz em português usada no fallback pyttsx3.
        self.voz_id = self._descobrir_voz_portugues()

    # ------------------------------------------------------------------ #
    #  Text-to-Speech (falar) - ponto único de entrada
    # ------------------------------------------------------------------ #
    def falar(self, texto: str, efeito=None, olhos: str = "ambos") -> None:
        """
        Fala um texto em voz alta (e também imprime no terminal).

        efeito -> opcional: função que devolve um bloco 'with' para rodar
                  ENQUANTO o áudio toca, junto com os olhos. Exemplo:
                      voz.falar(frase, efeito=arduino.cabeca_balancando)
                  Passamos a FUNÇÃO (sem parênteses), e não o bloco já
                  criado, porque ele pode ser usado duas vezes: se a voz de
                  personagem falhar no meio, o pyttsx3 toca a fala de novo.
        olhos  -> quais LEDs acendem durante a fala: "ambos" (padrão),
                  "vermelho" (Sharingan) ou "azul" (Rinnegan).
        """
        print(f"MADARA: {texto}")
        # Tenta primeiro a voz de personagem (edge-tts); se falhar, usa pyttsx3.
        if self.motor == "edge":
            if self._falar_edge(texto, efeito, olhos):
                return
        self._falar_pyttsx3(texto, efeito, olhos)

    # ------------------------------------------------------------------ #
    #  Motor 1: edge-tts (voz de personagem, grave/sombria)
    # ------------------------------------------------------------------ #
    def _falar_edge(self, texto: str, efeito=None, olhos: str = "ambos") -> bool:
        """Gera o áudio com edge-tts e o reproduz. Retorna True se der certo."""
        try:
            import edge_tts

            # Salva num caminho temporário SEM acento (evita problemas no Windows).
            caminho = os.path.join(tempfile.gettempdir(), "madara_fala.mp3")

            async def _gerar():
                comunicador = edge_tts.Communicate(
                    texto,
                    voice=self.edge_voz,
                    rate=self.edge_rate,
                    pitch=self.edge_pitch,
                )
                await comunicador.save(caminho)

            asyncio.run(_gerar())  # executa a rotina assíncrona do edge-tts
            with self._durante_o_audio(efeito, olhos):
                self._tocar_mp3(caminho)
            return True
        except Exception as erro:
            print(f"[Voz] Falha na voz de personagem ({erro}). Usando a voz padrão.")
            return False

    @contextmanager
    def _durante_o_audio(self, efeito=None, olhos: str = "ambos"):
        """
        Liga os olhos do boneco (e o 'efeito' extra, se houver) durante o
        bloco 'with', e desliga tudo no fim - mesmo se o áudio der erro.

        Usado só em volta da REPRODUÇÃO do áudio, não da fala inteira: o
        edge-tts leva cerca de 1 segundo gerando o mp3 pela internet antes
        de tocar, e qualquer efeito ligado antes disso ficaria fora de
        sincronia com a voz. Sem Arduino, só o 'efeito' (se houver) roda.
        """
        with ExitStack() as pilha:
            if self.arduino is not None:
                pilha.enter_context(self.arduino.olhos_acesos(olhos))
            if efeito is not None:
                pilha.enter_context(efeito())
            yield

    @staticmethod
    def _tocar_mp3(caminho: str) -> None:
        """Reproduz um arquivo mp3 usando o mixer do pygame."""
        from pygame import mixer

        if not mixer.get_init():
            mixer.init()
        mixer.music.load(caminho)
        mixer.music.play()
        while mixer.music.get_busy():
            # Espera em pausas de 10 ms em vez de um laço vazio: o laço vazio
            # ocupava 100% do processador durante a fala inteira e atrasava a
            # thread que balança a cabeça do boneco no mesmo momento.
            time.sleep(0.01)
        mixer.music.unload()

    # ------------------------------------------------------------------ #
    #  Motor 2: pyttsx3 (voz padrão, offline) - fallback
    # ------------------------------------------------------------------ #
    def _descobrir_voz_portugues(self):
        """Retorna o id de uma voz em português instalada no sistema (ou None)."""
        try:
            import pyttsx3
            motor = pyttsx3.init()
            escolhido = None
            for voz in motor.getProperty("voices"):
                nome = (voz.name or "").lower()
                if "portug" in nome or "brazil" in nome or "brasil" in nome:
                    escolhido = voz.id
                    break
            motor.stop()
            return escolhido
        except Exception as erro:
            print(f"[Voz] Não foi possível listar as vozes: {erro}")
            return None

    def _falar_pyttsx3(self, texto: str, efeito=None, olhos: str = "ambos") -> None:
        """
        Fala usando o pyttsx3. Recria o motor a cada chamada para evitar o bug
        do 'fala só na primeira vez' no Windows.
        """
        try:
            import pyttsx3
            motor = pyttsx3.init()
            motor.setProperty("volume", 1.0)
            motor.setProperty("rate", self.taxa_fala)
            if self.voz_id:
                motor.setProperty("voice", self.voz_id)
            motor.say(texto)
            with self._durante_o_audio(efeito, olhos):
                motor.runAndWait()  # é aqui que o áudio realmente toca
            motor.stop()  # encerra o motor para a próxima fala funcionar
        except Exception as erro:
            print(f"[Voz] Falha ao sintetizar áudio: {erro}")

    # ------------------------------------------------------------------ #
    #  Speech-to-Text (ouvir)
    # ------------------------------------------------------------------ #
    def ouvir(
        self,
        ajustar_ruido: bool = True,
        timeout: int | None = None,
        limite_frase: int | None = 15,
    ) -> str:
        """
        Captura o áudio do microfone e o converte em texto.

        Parâmetros:
            ajustar_ruido -> calibra o ruído do ambiente (só na 1a chamada).
            timeout       -> segundos esperando você COMEÇAR a falar.
            limite_frase  -> duração máxima da frase, em segundos. Impede que
                             um ruído contínuo prenda a escuta para sempre.

        Retorna a frase reconhecida em minúsculas, ou uma string vazia
        se nada for entendido.
        """
        with sr.Microphone() as microfone:
            # Calibra UMA única vez. Recalibrar a cada escuta (como antes)
            # somava 1s de espera toda vez e ainda podia elevar o limiar de
            # ruído a ponto de a assistente parar de ouvir vozes mais baixas.
            if ajustar_ruido and not self._ruido_calibrado:
                print("🔧 Calibrando o microfone... (fique em silêncio 1 segundo)")
                self.reconhecedor.adjust_for_ambient_noise(microfone, duration=1)
                self._ruido_calibrado = True

            print("🎤 Ouvindo...")
            try:
                audio = self.reconhecedor.listen(
                    microfone, timeout=timeout, phrase_time_limit=limite_frase
                )
            except sr.WaitTimeoutError:
                return ""

        # Envia o áudio para a API do Google converter em texto.
        try:
            texto = self.reconhecedor.recognize_google(audio, language=self.idioma)
            print(f"Você disse: {texto}")
            return texto.lower().strip()
        except sr.UnknownValueError:
            print("[Voz] Não entendi o que foi dito.")
            return ""
        except sr.RequestError as erro:
            print(f"[Voz] Erro ao acessar o serviço de reconhecimento: {erro}")
            return ""
        except OSError as erro:
            # O áudio é convertido para FLAC antes de ir ao Google. Sem um
            # 'flac' instalado, a biblioteca usa uma cópia embutida que só
            # roda em processador Intel - num Mac com chip Apple e sem
            # Rosetta, isso derrubava a assistente inteira.
            print(f"[Voz] Não consegui preparar o áudio ({erro}). "
                  "No macOS, instale o conversor com: brew install flac")
            return ""
