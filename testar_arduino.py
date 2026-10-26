"""
Script AUXILIAR - Teste do hardware do boneco (Arduino).

Testa os olhos e o BALANÇO da cabeça SEM precisar falar com a assistente.
A cabeça balança de um lado para o outro, sem dar voltas, para não torcer
os fios dentro do boneco.

Como usar:
    1) A placa precisa estar com o sketch 'arduino/madara_arduino'.
    2) Feche o Monitor Serial do Arduino IDE (só um programa pode usar a
       porta por vez).
    3) Rode um dos dois:

        python testar_arduino.py        -> começa com um balanço pequeno e
                                           vai aumentando até vocês gostarem
        python testar_arduino.py 80     -> balança direto com 80 ms

O número é quanto tempo o motor fica ligado do centro até cada lado: maior
= balanço mais largo. Quando acharem o valor certo, grave no .env:

    ARDUINO_BALANCO_MS=80

e o "madara hashirama" passa a usar esse balanço.
"""

import sys
import time

from modulos.arduino import FABRICANTES_USB, Arduino, list_ports

BALANCO_INICIAL = 30   # ms - começa pequeno: a cabeça não está bem fixada
PASSO = 15             # ms a mais (ou a menos) a cada tentativa
BALANCO_MAXIMO = 300   # ms - acima disso já seria um giro, não um balanço
TEMPO_BALANCANDO = 3   # segundos de balanço em cada tentativa


def listar_portas() -> None:
    """Mostra as portas seriais, para ajudar se a placa não for encontrada."""
    if list_ports is None:
        return
    print("Portas seriais encontradas:")
    for p in list_ports.comports():
        fabricante = FABRICANTES_USB.get(p.vid, "-")
        print(f"  {p.device:<32} {fabricante:<14} {p.description}")
    print()


def balancar(arduino: Arduino, balanco_ms: int, segundos: float) -> None:
    """Balança a cabeça com os olhos acesos, como na fala do MADARA."""
    with arduino.olhos_acesos(), arduino.cabeca_balancando(balanco_ms):
        time.sleep(segundos)
    time.sleep(1)  # tempo para a cabeça voltar ao centro


def ajustar_balanco(arduino: Arduino) -> int | None:
    """Aumenta o balanço aos poucos até vocês gostarem. None = desistiram."""
    print("Vamos ajustar o tamanho do balanço da cabeça.")
    print("Depois de cada tentativa, responda:")
    print("  s     = está bom assim")
    print("  Enter = balançar MAIS")
    print("  m     = balançar MENOS")
    print("  q     = sair\n")

    balanco = BALANCO_INICIAL
    while True:
        print(f"  Balanço de {balanco} ms...", end=" ", flush=True)
        balancar(arduino, balanco, TEMPO_BALANCANDO)
        resposta = input("e aí? [s / Enter / m / q] ").strip().lower()

        if resposta.startswith("s"):
            return balanco
        if resposta.startswith("q"):
            return None
        if resposta.startswith("m"):
            balanco = max(BALANCO_INICIAL, balanco - PASSO)
        elif balanco + PASSO > BALANCO_MAXIMO:
            print(f"  (já está no máximo de {BALANCO_MAXIMO} ms para um balanço)")
        else:
            balanco += PASSO


if __name__ == "__main__":
    listar_portas()
    arduino = Arduino()
    if not arduino.conectado:
        raise SystemExit(
            "Sem Arduino conectado. Confira o cabo, ou defina ARDUINO_PORTA no "
            ".env com uma das portas listadas acima."
        )

    # O 'finally' para a cabeça e apaga os olhos mesmo com Ctrl+C.
    try:
        # Cada cor separada confere a fiação: o vermelho tem que estar no
        # pino 9 e o azul no pino 10.
        for cor, descricao in (("vermelho", "só o VERMELHO (Sharingan, pino 9)"),
                               ("azul", "só o AZUL (Rinnegan, pino 10)"),
                               ("ambos", "os DOIS juntos")):
            print(f"Acendendo {descricao}...")
            arduino.acender_olhos(cor)
            time.sleep(1.2)
            arduino.apagar_olhos()
            time.sleep(0.5)
        print()

        if len(sys.argv) > 1:
            balanco = int(sys.argv[1])
            print(f"Balançando a cabeça por 5 segundos com {balanco} ms...")
            balancar(arduino, balanco, 5)
        else:
            balanco = ajustar_balanco(arduino)

        if balanco is not None:
            print(f"\nBalanço escolhido: {balanco} ms. Para usar no projeto, "
                  "grave no .env:")
            print(f"    ARDUINO_BALANCO_MS={balanco}")
    finally:
        arduino.fechar()
