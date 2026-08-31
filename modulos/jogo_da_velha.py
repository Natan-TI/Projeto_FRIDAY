"""
Módulo JOGO DA VELHA da assistente M.A.D.A.R.A. (extra do item 10).

Um jogo da velha jogado por VOZ contra a assistente. O usuário fala a
posição desejada (de 1 a 9) e a MADARA joga em seguida usando uma
estratégia simples (vencer, bloquear ou escolher a melhor casa livre).

O tabuleiro segue a numeração do teclado numérico:
    1 | 2 | 3
    4 | 5 | 6
    7 | 8 | 9
"""


class JogoDaVelha:
    """Controla uma partida de jogo da velha entre usuário (X) e MADARA (O)."""

    # Todas as combinações que fecham o jogo (linhas, colunas e diagonais).
    LINHAS_VITORIA = [
        (0, 1, 2), (3, 4, 5), (6, 7, 8),   # linhas
        (0, 3, 6), (1, 4, 7), (2, 5, 8),   # colunas
        (0, 4, 8), (2, 4, 6),              # diagonais
    ]

    def __init__(self, voz):
        """Recebe o objeto Voz para poder falar e ouvir durante a partida."""
        self.voz = voz
        self.tabuleiro = [" "] * 9  # 9 casas vazias
        self.jogador = "X"          # usuário
        self.maquina = "O"          # MADARA

    # ------------------------------------------------------------------ #
    #  Exibição e regras
    # ------------------------------------------------------------------ #
    def _desenhar(self) -> None:
        """Imprime o tabuleiro atual no terminal."""
        t = self.tabuleiro
        print("\n")
        print(f" {t[0]} | {t[1]} | {t[2]} ")
        print("---+---+---")
        print(f" {t[3]} | {t[4]} | {t[5]} ")
        print("---+---+---")
        print(f" {t[6]} | {t[7]} | {t[8]} ")
        print("\n")

    def _vencedor(self, simbolo: str) -> bool:
        """Verifica se o símbolo informado completou alguma linha de vitória."""
        return any(
            all(self.tabuleiro[i] == simbolo for i in linha)
            for linha in self.LINHAS_VITORIA
        )

    def _casas_livres(self) -> list[int]:
        """Retorna os índices das casas ainda vazias."""
        return [i for i, casa in enumerate(self.tabuleiro) if casa == " "]

    # ------------------------------------------------------------------ #
    #  Inteligência simples da MADARA
    # ------------------------------------------------------------------ #
    def _jogada_maquina(self) -> int:
        """
        Escolhe a jogada da máquina seguindo prioridades:
            1) vencer se possível;
            2) bloquear a vitória do jogador;
            3) pegar o centro;
            4) pegar um canto;
            5) qualquer casa livre.
        """
        # 1) Tenta vencer.
        for i in self._casas_livres():
            self.tabuleiro[i] = self.maquina
            if self._vencedor(self.maquina):
                return i
            self.tabuleiro[i] = " "

        # 2) Tenta bloquear o jogador.
        for i in self._casas_livres():
            self.tabuleiro[i] = self.jogador
            if self._vencedor(self.jogador):
                self.tabuleiro[i] = " "
                return i
            self.tabuleiro[i] = " "

        # 3/4/5) Centro, cantos e depois qualquer casa.
        for preferida in [4, 0, 2, 6, 8, 1, 3, 5, 7]:
            if preferida in self._casas_livres():
                return preferida
        return self._casas_livres()[0]

    # ------------------------------------------------------------------ #
    #  Laço principal da partida
    # ------------------------------------------------------------------ #
    def jogar(self) -> None:
        """Executa a partida completa até haver vitória ou empate."""
        self.voz.falar(
            "Vamos jogar o jogo da velha! Você é o X. "
            "Fale o número da casa, de 1 a 9, onde quer jogar."
        )
        self._desenhar()

        while True:
            # ---------------- Vez do jogador ---------------- #
            posicao = self._ler_posicao_do_usuario()
            if posicao is None:
                self.voz.falar("Não entendi a casa. Vamos encerrar o jogo.")
                return
            self.tabuleiro[posicao] = self.jogador
            self._desenhar()

            if self._vencedor(self.jogador):
                self.voz.falar("Você venceu! Parabéns!")
                return
            if not self._casas_livres():
                self.voz.falar("Deu velha! Empatamos.")
                return

            # ---------------- Vez da MADARA ---------------- #
            jogada = self._jogada_maquina()
            self.tabuleiro[jogada] = self.maquina
            self.voz.falar(f"Eu joguei na casa {jogada + 1}.")
            self._desenhar()

            if self._vencedor(self.maquina):
                self.voz.falar("Eu venci! Quem sabe na próxima.")
                return
            if not self._casas_livres():
                self.voz.falar("Deu velha! Empatamos.")
                return

    def _ler_posicao_do_usuario(self):
        """
        Ouve o usuário e devolve o índice (0 a 8) de uma casa VÁLIDA e LIVRE,
        ou None caso ele desista/erre repetidas vezes.
        """
        # Converte números por extenso para dígitos.
        numeros = {
            "um": 1, "dois": 2, "três": 3, "quatro": 4, "cinco": 5,
            "seis": 6, "sete": 7, "oito": 8, "nove": 9,
        }
        for _ in range(3):  # até 3 tentativas
            fala = self.voz.ouvir()
            if "sair" in fala or "parar" in fala:
                return None

            posicao = None
            for token in fala.split():
                if token.isdigit() and 1 <= int(token) <= 9:
                    posicao = int(token)
                    break
                if token in numeros:
                    posicao = numeros[token]
                    break

            if posicao is None:
                self.voz.falar("Fale um número de 1 a 9.")
                continue

            indice = posicao - 1
            if self.tabuleiro[indice] != " ":
                self.voz.falar("Essa casa já está ocupada. Escolha outra.")
                continue
            return indice
        return None
