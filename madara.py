"""
==========================================================================
  PROJETO M.A.D.A.R.A.  -  Assistente Virtual por Comandos de Voz
  Checkpoint 4 - 2º semestre
==========================================================================

Arquivo principal. Contém a classe 'AssistenteMadara', que orquestra todos
os módulos e implementa a REGRA DE OURO do desafio:

    >> Nenhum comando é executado sem antes o usuário falar o nome
       da assistente ("madara"). <<

Comandos suportados:
    1) "madara"                         -> ativa a assistente (palavra de ativação)
    2) "madara cadastrar evento..."     -> grava um evento em agenda.txt
    3) "madara ler agenda"              -> lê os eventos cadastrados
    4) "que horas são?"                 -> fala a hora atual
    5) "que dia é hoje?"                -> fala a data atual
    6) "calcular ..."                   -> faz as 4 operações básicas
    7) "reconhecer face"/"quem sou eu?" -> reconhecimento facial pela webcam
    8) "limpar agenda"                  -> apaga os eventos (mantém o arquivo)
    9) "pergunte à IA ..." / livre      -> integração com IA generativa
   10) extras: dólar, bitcoin, tempo, youtube, print,
       portal da faculdade e jogo da velha.
   11) Arduino: os olhos (LEDs) acendem a cada fala, e três cenas balançam
       a cabeça do boneco enquanto ele fala:
         "madara hashirama"        -> provoca o clã Senju
         "madara ativar sharingan" -> só o LED vermelho acende
         "madara ativar rinnegan"  -> só o LED azul acende

Execute com:  python madara.py
"""

import random

from modulos import (
    Arduino,
    Voz,
    Agenda,
    ReconhecimentoFacial,
    IAGenerativa,
    Utilidades,
    JogoDaVelha,
)


class AssistenteMadara:
    """Classe principal: junta todos os módulos e roteia os comandos de voz."""

    # Como o reconhecimento de fala pode escrever "Hashirama". Se o terminal
    # mostrar outra grafia quando você falar, é só acrescentá-la aqui.
    GATILHOS_HASHIRAMA = ("hashirama", "rashirama", "ashirama", "achirama",
                          "hashi rama")

    # Falas sorteadas quando alguém provoca o MADARA com o nome do rival.
    FALAS_HASHIRAMA = (
        "Hashirama... Esse nome ainda queima dentro de mim. O clã Senju se "
        "ajoelhou uma vez, e vai se ajoelhar de novo diante do meu Sharingan.",
        "Você ousa pronunciar o nome de Hashirama na minha presença? Os Senju "
        "só continuam de pé porque eu ainda não terminei o que comecei.",
        "Hashirama, meu velho rival. A paz dos Senju é uma ilusão vendida aos "
        "fracos. Eu vou despertar este mundo desse sonho.",
        "Os Senju ergueram a vila sobre o sangue dos Uchiha. Chegou a hora de "
        "cobrar essa dívida, até o último deles.",
    )

    # Sharingan e Rinnegan só disparam junto com o verbo "ativar": assim uma
    # pergunta como "madara, quem tem o sharingan?" continua indo para a IA.
    GATILHOS_ATIVAR = ("ativar", "ative", "ativa")
    GATILHOS_SHARINGAN = ("sharingan", "sharingam", "xaringan", "charingan",
                          "sharing gan")
    GATILHOS_RINNEGAN = ("rinnegan", "rinegan", "rinengan", "renegan",
                         "rinne gan", "rin negan")

    # "Manguekiô" está escrito como se fala: escrito "Mangekyou", a voz em
    # português lê "man-jé-kiou".
    FALAS_SHARINGAN = (
        "Manguekiô Sharingan! Nada escapa destes olhos.",
        "Manguekiô Sharingan! Você já está preso na minha ilusão.",
        "Manguekiô Sharingan! Eu vejo cada movimento seu antes mesmo de você "
        "pensar nele.",
    )
    FALAS_RINNEGAN = (
        "Rinnegan! O olho do Sábio dos Seis Caminhos.",
        "Rinnegan do Sábio dos Seis Caminhos! Contemple o poder que rege a "
        "vida e a morte.",
        "Rinnegan! Com estes olhos, eu vou conduzir este mundo ao Tsukuyomi "
        "Infinito.",
    )

    def __init__(self, nome: str = "madara"):
        # Palavra de ativação (wake word). Só após ouvi-la a MADARA age.
        self.nome = nome.lower()

        # Instancia cada módulo (composição de objetos).
        # O Arduino vem primeiro porque a Voz o recebe para acender os olhos
        # a cada fala. Sem placa conectada, ele apenas avisa e fica inativo.
        self.arduino = Arduino()
        self.voz = Voz(arduino=self.arduino)
        self.agenda = Agenda()
        self.face = ReconhecimentoFacial()
        self.ia = IAGenerativa(provedor="groq")  # troque para "ollama" se quiser local
        self.utils = Utilidades()

        self.ativa = True  # controla o laço principal

    # ------------------------------------------------------------------ #
    #  Laço principal
    # ------------------------------------------------------------------ #
    def executar(self) -> None:
        """Fica ouvindo continuamente e processa cada fala reconhecida."""
        try:
            self.voz.falar(
                "Olá! Eu sou o MADARA. Diga 'madara' seguido de um comando "
                "para começar."
            )
            self._laco_principal()
        finally:
            # Roda até no Ctrl+C: apaga os olhos, centraliza a cabeça e
            # libera a porta serial para a próxima execução.
            self.arduino.fechar()

    def _laco_principal(self) -> None:
        """Ouve e processa falas até o comando de desligar."""
        while self.ativa:
            fala = self.voz.ouvir()

            # Nada reconhecido: volta a ouvir.
            if not fala:
                continue

            # REGRA DE OURO: só age se a palavra de ativação estiver presente.
            if self.nome not in fala:
                # Item 1: apenas imprime o texto reconhecido, sem executar nada.
                print(f"(ignorado - sem palavra de ativação) Você disse: {fala}")
                continue

            # Remove o nome da assistente para sobrar apenas o comando.
            comando = fala.replace(self.nome, "").strip()
            self.processar_comando(comando)

    # ------------------------------------------------------------------ #
    #  Roteador de comandos
    # ------------------------------------------------------------------ #
    def processar_comando(self, comando: str) -> None:
        """Identifica a intenção do comando e chama a ação correspondente."""

        # --- Encerrar a assistente ---
        if any(p in comando for p in ["desligar", "encerrar", "tchau", "adeus"]):
            self.voz.falar("Até logo! Encerrando.")
            self.ativa = False
            return

        # --- Arduino: cenas que balançam a cabeça do boneco ---
        if any(g in comando for g in self.GATILHOS_HASHIRAMA):
            self._cena(self.FALAS_HASHIRAMA)
            return
        if any(g in comando for g in self.GATILHOS_ATIVAR):
            if any(g in comando for g in self.GATILHOS_SHARINGAN):
                self._cena(self.FALAS_SHARINGAN, olhos="vermelho")
                return
            if any(g in comando for g in self.GATILHOS_RINNEGAN):
                self._cena(self.FALAS_RINNEGAN, olhos="azul")
                return

        # --- Item 8: limpar agenda (checado ANTES de 'cadastrar/ler') ---
        if "limpar agenda" in comando or "apagar agenda" in comando:
            self.agenda.limpar()
            self.voz.falar("Pronto! A agenda foi limpa, mas o arquivo continua lá.")
            return

        # --- Item 2: cadastrar evento na agenda ---
        if "cadastrar evento" in comando or "cadastrar na agenda" in comando:
            self._cadastrar_evento()
            return

        # --- Item 3: ler agenda ---
        if "ler agenda" in comando or "ler a agenda" in comando:
            self._ler_agenda()
            return

        # --- Item 4: que horas são ---
        if "horas" in comando or "que hora" in comando:
            self.voz.falar(self.utils.hora_atual())
            return

        # --- Item 5: que dia é hoje ---
        if "que dia" in comando or "dia de hoje" in comando or "data de hoje" in comando:
            self.voz.falar(self.utils.data_atual())
            return

        # --- Item 6: calcular ---
        if "calcular" in comando or "quanto é" in comando:
            self.voz.falar(self.utils.calcular(comando))
            return

        # --- Item 7: reconhecimento facial ---
        if "reconhecer face" in comando or "quem sou eu" in comando or "reconhecer rosto" in comando:
            self._reconhecer_face()
            return

        # --- Item 10: cotações ---
        if "dólar" in comando or "dolar" in comando:
            self.voz.falar(self.utils.cotacao_dolar())
            return
        if "bitcoin" in comando:
            self.voz.falar(self.utils.cotacao_bitcoin())
            return

        # --- Item 10: previsão do tempo ---
        if "tempo" in comando or "previsão" in comando or "clima" in comando:
            cidade = self._extrair_depois(comando, ["para", "em", "de"], "São Paulo")
            self.voz.falar(self.utils.previsao_tempo(cidade))
            return

        # --- Item 10: YouTube ---
        if "youtube" in comando or "vídeo" in comando or "video" in comando:
            termo = self._extrair_depois(comando, ["sobre", "de"], "músicas")
            self.voz.falar(self.utils.abrir_youtube(termo))
            return

        # --- Item 10: pesquisar no Google ---
        if "pesquisar" in comando or "pesquise" in comando or "buscar" in comando:
            termo = self._extrair_depois(comando, ["por", "sobre"], comando)
            self.voz.falar(self.utils.pesquisar_google(termo))
            return

        # --- Item 10: portal da faculdade ---
        if "portal" in comando or "faculdade" in comando:
            self.voz.falar(self.utils.abrir_portal_faculdade())
            return

        # --- Item 10: print da tela ---
        if "print" in comando or "captura de tela" in comando or "imprimir tela" in comando:
            self.voz.falar(self.utils.tirar_print())
            return

        # --- Item 10: volume ---
        if "aumentar volume" in comando or "aumenta o volume" in comando:
            self.voz.falar(self.utils.ajustar_volume(aumentar=True))
            return
        if "diminuir volume" in comando or "abaixar volume" in comando:
            self.voz.falar(self.utils.ajustar_volume(aumentar=False))
            return

        # --- Item 10: jogo da velha ---
        if "jogo da velha" in comando or "jogar velha" in comando:
            JogoDaVelha(self.voz).jogar()
            return

        # --- Item 9: qualquer outra coisa vai para a IA generativa ---
        self._perguntar_ia(comando)

    # ------------------------------------------------------------------ #
    #  Ações auxiliares
    # ------------------------------------------------------------------ #
    def _cadastrar_evento(self) -> None:
        """Pergunta o evento, ouve a resposta e grava no agenda.txt (item 2)."""
        self.voz.falar("Ok, qual evento devo cadastrar?")
        # Ditar um evento leva mais tempo que um comando curto, então damos
        # uma janela maior antes de encerrar a captura.
        evento = self.voz.ouvir(limite_frase=25)
        if evento:
            self.agenda.cadastrar_evento(evento)
            self.voz.falar(f"Evento cadastrado: {evento}.")
        else:
            self.voz.falar("Não entendi o evento. Nada foi cadastrado.")

    def _ler_agenda(self) -> None:
        """Lê em voz alta todos os eventos cadastrados (item 3)."""
        eventos = self.agenda.ler_eventos()
        if not eventos:
            self.voz.falar("Sua agenda está vazia.")
            return
        self.voz.falar(f"Você tem {len(eventos)} evento(s) na agenda:")
        for evento in eventos:
            self.voz.falar(evento)

    def _reconhecer_face(self) -> None:
        """Abre a webcam e anuncia quem foi reconhecido (item 7)."""
        self.voz.falar("Abrindo a webcam para reconhecer você.")
        nome = self.face.reconhecer()
        if nome == "modelo_ausente":
            self.voz.falar(
                "O modelo de reconhecimento ainda não foi treinado. "
                "Rode os scripts de captura e treinamento primeiro."
            )
        elif nome == "Desconhecido":
            self.voz.falar("Não reconheci você. Você parece um desconhecido.")
        else:
            self.voz.falar(f"Reconheci você! Olá, {nome}.")

    def _cena(self, falas: tuple[str, ...], olhos: str = "ambos") -> None:
        """
        Sorteia uma das 'falas' e a diz balançando a cabeça do boneco.

        olhos -> quais LEDs acendem durante a fala: "ambos" (Hashirama),
                 "vermelho" (Sharingan) ou "azul" (Rinnegan).

        O balanço é curto, de um lado para o outro, sem dar voltas - para não
        torcer os fios dentro do boneco (ver Arduino.cabeca_balancando).

        A cabeça é entregue à Voz como 'efeito', e não ligada aqui antes de
        falar: assim ela começa a se mexer no mesmo instante em que o áudio
        começa a tocar e os olhos acendem. Ligada antes, ela se mexia sozinha
        durante o segundo em que a voz ainda está sendo gerada pela internet.
        Sem Arduino conectado, o MADARA apenas fala.
        """
        self.voz.falar(
            random.choice(falas),
            efeito=self.arduino.cabeca_balancando,
            olhos=olhos,
        )

    def _perguntar_ia(self, pergunta: str) -> None:
        """Encaminha perguntas abertas para a IA generativa (item 9)."""
        self.voz.falar("Deixa eu pensar...")
        resposta = self.ia.responder(pergunta)
        self.voz.falar(resposta)

    @staticmethod
    def _extrair_depois(texto: str, gatilhos: list[str], padrao: str) -> str:
        """
        Utilitário: devolve o trecho do 'texto' que vem depois do primeiro
        'gatilho' encontrado (ex.: pega 'São Paulo' de 'tempo para São Paulo').
        Se nenhum gatilho aparecer, devolve o valor 'padrao'.
        """
        palavras = texto.split()
        for gatilho in gatilhos:
            if gatilho in palavras:
                idx = palavras.index(gatilho)
                trecho = " ".join(palavras[idx + 1:]).strip()
                if trecho:
                    return trecho
        return padrao


# ---------------------------------------------------------------------- #
#  Ponto de entrada do programa
# ---------------------------------------------------------------------- #
if __name__ == "__main__":
    assistente = AssistenteMadara(nome="madara")
    try:
        assistente.executar()
    except KeyboardInterrupt:
        print("\nEncerrado pelo usuário (Ctrl+C).")
