"""
Módulo de integração com o ARDUINO da assistente M.A.D.A.R.A.

Controla o "corpo" do boneco pela porta serial (USB):
    - os dois LEDs dos OLHOS, que acendem sempre que o MADARA fala;
    - o MOTOR DC da CABEÇA (ligado por uma ponte H), que gira em comandos
      como "madara hashirama".

Protocolo: um caractere por comando, a 9600 baud - o mesmo formato do
'arduino_serial.ino' / 'teste_arduino.py' do professor, só que com mais
comandos:

    'O'  -> acende os olhos
    'o'  -> apaga os olhos
    'G'  -> começa a girar a cabeça (vai e volta até receber 'P')
    'P'  -> para a cabeça e volta ao centro
    'V'  -> acende só o LED vermelho (Sharingan)
    'A'  -> acende só o LED azul (Rinnegan)

Ao ligar, o Arduino envia a linha "PRONTO v2" (ver arduino/madara_arduino).
Uma placa com o sketch antigo manda só "PRONTO" e não conhece 'V' nem 'A'.

REGRA IMPORTANTE: o Arduino é OPCIONAL. Se a placa não estiver conectada,
a assistente continua funcionando normalmente, só que sem os efeitos
físicos. Nenhum método desta classe levanta erro para quem o chama.

Teste rápido do hardware (sem precisar falar com a assistente):
    python testar_arduino.py
"""

import threading
import time
from contextlib import contextmanager

from .config import obter_variavel

try:
    import serial
    from serial.tools import list_ports
except ImportError:  # pyserial não instalado: a classe vira "modo sem Arduino"
    serial = None
    list_ports = None


# Fabricantes de chip USB-serial usados nas placas Arduino e nos clones.
# Identificar pelo VID (id do fabricante USB) evita abrir, por engano, portas
# que não são o Arduino - como fones Bluetooth, que também aparecem como
# porta serial no macOS e no Windows.
FABRICANTES_USB = {
    0x2341: "Arduino",
    0x2A03: "Arduino",
    0x1A86: "CH340 (clone)",
    0x0403: "FTDI",
    0x10C4: "CP210x",
}

# Plano B quando o VID não é reconhecido: nomes típicos de porta USB-serial.
NOMES_TIPICOS = ("usbmodem", "usbserial", "wchusbserial", "ttyACM", "ttyUSB")

# Constantes do sketch que o balanço da cabeça precisa conhecer. Se mudar
# lá no madara_arduino.ino, mude aqui também.
PAUSA_INVERSAO_MS = 120    # freio do sketch antes de cada troca de sentido
AMPLITUDE_SKETCH_MS = 600  # a partir daqui o próprio sketch inverteria sozinho

# Balanço padrão da cabeça: quanto tempo o motor fica ligado do centro até
# cada lado. Ajuste com 'python testar_arduino.py' e grave o valor escolhido
# em ARDUINO_BALANCO_MS no .env.
BALANCO_PADRAO_MS = 60  # testado no boneco: balanço visível sem forçar os fios


class Arduino:
    """Envia comandos ao Arduino que controla os olhos e a cabeça do boneco."""

    # Comandos do protocolo (precisam bater com o sketch .ino).
    OLHOS_ACENDER = b"O"
    OLHOS_APAGAR = b"o"
    OLHO_VERMELHO = b"V"
    OLHO_AZUL = b"A"
    CABECA_GIRAR = b"G"
    CABECA_PARAR = b"P"

    def __init__(self, porta: str | None = None, baudrate: int = 9600, ativo: bool = True):
        """
        Parâmetros:
            porta    -> ex.: 'COM3' (Windows) ou '/dev/cu.usbmodem1101' (macOS).
                        Se não for informada, usa ARDUINO_PORTA do .env e,
                        em último caso, procura a placa automaticamente.
            baudrate -> velocidade da serial; precisa ser a mesma do sketch.
            ativo    -> False desliga a integração sem mexer no resto do código.
        """
        self.porta = porta or obter_variavel("ARDUINO_PORTA")
        self.baudrate = baudrate
        self.serial = None
        self.balanco_ms = int(obter_variavel("ARDUINO_BALANCO_MS", str(BALANCO_PADRAO_MS)))

        # O balanço da cabeça manda comandos de uma thread separada, ao mesmo
        # tempo em que a Voz acende e apaga os olhos. A trava impede que duas
        # escritas na porta serial se misturem.
        self._trava = threading.Lock()

        # Só o sketch novo ("PRONTO v2") acende cada LED sozinho.
        self.leds_separados = False

        if ativo:
            self.conectar()

    # ------------------------------------------------------------------ #
    #  Conexão
    # ------------------------------------------------------------------ #
    @property
    def conectado(self) -> bool:
        """Informa se existe uma conexão serial aberta com a placa."""
        return self.serial is not None and self.serial.is_open

    def conectar(self) -> bool:
        """Abre a porta serial. Retorna True se conectou."""
        if serial is None:
            print("[Arduino] Biblioteca 'pyserial' não instalada (pip install pyserial). "
                  "Seguindo sem o Arduino.")
            return False

        porta = self.porta or self.detectar_porta()
        if not porta:
            print("[Arduino] Nenhuma placa encontrada. Seguindo sem o Arduino.")
            return False

        try:
            self.serial = serial.Serial(porta, self.baudrate, timeout=0.1)
        except (serial.SerialException, OSError) as erro:
            print(f"[Arduino] Não consegui abrir a porta {porta}: {erro}. "
                  "Seguindo sem o Arduino.")
            self.serial = None
            return False

        self.porta = porta
        pronto = self._aguardar_pronto()
        if pronto is None:
            print(f"[Arduino] Porta {porta} aberta, mas a placa não respondeu 'PRONTO'. "
                  "Confira se o sketch madara_arduino.ino foi enviado para ela.")
            return True

        print(f"[Arduino] Conectado em {porta}.")
        self.leds_separados = b"v2" in pronto
        if not self.leds_separados:
            print("[Arduino] A placa está com o sketch antigo: o Sharingan e o "
                  "Rinnegan vão acender os DOIS LEDs. Carregue a versão nova do "
                  "madara_arduino.ino para cada um acender só a sua cor.")
        return True

    def _aguardar_pronto(self, limite_segundos: float = 3.0) -> bytes | None:
        """
        Abrir a porta serial REINICIA o Arduino (o sinal DTR do USB dispara o
        reset). Por ~2 segundos quem roda é o bootloader, e tudo que for
        enviado nesse intervalo se perde.

        O 'teste_arduino.py' do professor resolve com time.sleep(2). Aqui
        esperamos a mensagem "PRONTO" que o sketch manda no setup(): é mais
        rápido quando a placa sobe logo, e confiável quando ela demora.

        Retorna a linha recebida (ex.: b"PRONTO v2"), ou None se não chegar.
        """
        fim = time.monotonic() + limite_segundos
        while time.monotonic() < fim:
            try:
                linha = self.serial.readline()
            except (serial.SerialException, OSError):
                return None
            if b"PRONTO" in linha:
                return linha.strip()
        return None

    @staticmethod
    def detectar_porta() -> str | None:
        """Procura uma porta que pareça ser um Arduino. Retorna None se não achar."""
        if list_ports is None:
            return None
        portas = list(list_ports.comports())

        # 1a tentativa: pelo fabricante do chip USB (mais confiável).
        for p in portas:
            if p.vid in FABRICANTES_USB:
                return p.device

        # 2a tentativa: pelo nome da porta.
        for p in portas:
            if any(nome in p.device for nome in NOMES_TIPICOS):
                return p.device
        return None

    def fechar(self) -> None:
        """Deixa o boneco em repouso (olhos apagados, cabeça no centro) e desconecta."""
        if not self.conectado:
            return
        self.apagar_olhos()
        self.parar_cabeca()
        try:
            self.serial.flush()  # garante que os últimos comandos saíram
            self.serial.close()
        except (serial.SerialException, OSError):
            pass
        self.serial = None

    def _enviar(self, comando: bytes) -> None:
        """Envia um comando. Sem placa (ou se o cabo sair), apenas ignora."""
        with self._trava:
            if not self.conectado:
                return
            try:
                self.serial.write(comando)
            except (serial.SerialException, OSError) as erro:
                # Cabo desconectado no meio do uso: avisa uma vez e segue sem
                # o Arduino, em vez de derrubar a assistente.
                print(f"[Arduino] Conexão perdida ({erro}). Seguindo sem o Arduino.")
                try:
                    self.serial.close()
                except (serial.SerialException, OSError):
                    pass
                self.serial = None

    # ------------------------------------------------------------------ #
    #  Olhos (LEDs)
    # ------------------------------------------------------------------ #
    def acender_olhos(self, cor: str = "ambos") -> None:
        """
        Acende os LEDs dos olhos.

        cor -> "ambos" (padrão), "vermelho" (Sharingan) ou "azul" (Rinnegan).
               Com o sketch antigo na placa, qualquer cor acende os dois.
        """
        comandos = {
            "ambos": self.OLHOS_ACENDER,
            "vermelho": self.OLHO_VERMELHO,
            "azul": self.OLHO_AZUL,
        }
        if cor not in comandos:
            raise ValueError(f"Cor inválida: {cor!r}. Use 'ambos', 'vermelho' ou 'azul'.")
        if not self.leds_separados:
            cor = "ambos"
        self._enviar(comandos[cor])

    def apagar_olhos(self) -> None:
        """Apaga os dois LEDs dos olhos."""
        self._enviar(self.OLHOS_APAGAR)

    @contextmanager
    def olhos_acesos(self, cor: str = "ambos"):
        """
        Mantém os olhos acesos enquanto o bloco 'with' executa:

            with arduino.olhos_acesos("vermelho"):
                tocar_audio()

        O 'finally' garante que eles apagam mesmo se o áudio der erro.
        """
        self.acender_olhos(cor)
        try:
            yield
        finally:
            self.apagar_olhos()

    # ------------------------------------------------------------------ #
    #  Cabeça (motor DC na ponte H)
    # ------------------------------------------------------------------ #
    def girar_cabeca(self) -> None:
        """Começa a girar a cabeça. Ela continua até parar_cabeca()."""
        self._enviar(self.CABECA_GIRAR)

    def parar_cabeca(self) -> None:
        """Para a cabeça; o Arduino a leva de volta ao centro suavemente."""
        self._enviar(self.CABECA_PARAR)

    @contextmanager
    def cabeca_balancando(self, balanco_ms: int | None = None):
        """
        Balança a cabeça de um lado para o outro, com movimentos curtos,
        enquanto o bloco 'with' executa - sem dar voltas, para não torcer os
        fios dentro do boneco.

        balanco_ms -> quanto tempo o motor fica ligado do centro até cada
                      lado (padrão: ARDUINO_BALANCO_MS do .env, ou 60).
                      Maior = balanço mais largo.

        Cada balançada é um gesto completo, como um "não, não" de cabeça:
            centro -> direita -> esquerda -> centro (pausa breve) -> de novo

        Funciona com o sketch que já está na placa, que só conhece 'G' (gira)
        e 'P' (para e volta ao centro):
            - 'G' tira a cabeça do centro para a direita;
            - "PG" seguidos viram um "inverter": o 'P' freia e marca a volta
              ao centro, e o 'G' logo depois faz o sketch seguir em frente,
              passando do centro até a esquerda;
            - um 'P' sozinho traz a cabeça de volta e a PARA no centro.
        Quem decide quando inverter é o Python, bem antes dos 600 ms em que o
        sketch inverteria sozinho - é isso que deixa o balanço curto.

        Por que parar no centro a cada gesto: cada comando chega à placa com
        alguns milissegundos de variação, e como os movimentos alternam de
        sentido, esses erros não se cancelam - vão se somando, e numa fala
        longa o balanço ia "andando" para um dos lados. Parando no centro, que
        o sketch conhece com exatidão, o erro de um gesto não passa para o
        próximo.
        """
        balanco = balanco_ms if balanco_ms is not None else self.balanco_ms
        # Abaixo de ~10 ms o motor nem chega a vencer a inércia; acima de 400
        # ficaria perto demais do limite em que o sketch inverte por conta.
        balanco = max(10, min(400, int(balanco)))
        parar = threading.Event()

        freio, folga = PAUSA_INVERSAO_MS, 40
        # (instante em ms dentro do gesto, comando). Cada trecho começa com o
        # freio de 120 ms que o sketch faz antes de mover o motor.
        gesto = (
            (0, self.CABECA_GIRAR),                              # centro -> direita
            (freio + balanco, self.CABECA_PARAR + self.CABECA_GIRAR),  # direita -> esquerda
            (2 * freio + 3 * balanco, self.CABECA_PARAR),        # esquerda -> centro
        )
        # A cabeça chega ao centro em 3 freios + 4 balanços; a folga garante
        # que o próximo 'G' só chegue depois que ela parou.
        duracao_gesto = 3 * freio + 4 * balanco + folga

        def balancar():
            inicio = time.monotonic()
            numero = 0
            while True:
                comeco = inicio + numero * duracao_gesto / 1000
                for instante_ms, comando in gesto:
                    espera = comeco + instante_ms / 1000 - time.monotonic()
                    if parar.wait(max(0.0, espera)):
                        return
                    self._enviar(comando)
                numero += 1

        thread = threading.Thread(target=balancar, daemon=True)
        thread.start()
        try:
            yield
        finally:
            parar.set()
            thread.join()
            self.parar_cabeca()  # o sketch leva a cabeça de volta ao centro
