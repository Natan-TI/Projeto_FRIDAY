"""
Módulo de RECONHECIMENTO FACIAL da assistente M.A.D.A.R.A. (item 7).

Abre a webcam, detecta o rosto com Haar Cascade e reconhece a pessoa
usando um modelo EigenFaceRecognizer pré-treinado ('classificadoreigen.yml').

Baseado nos códigos do professor:
    - deteccao2.py    (detecção pela webcam)
    - reconhecimento.py (EigenFaceRecognizer + predict)
    - treinamento.py  (treino do modelo .yml)

Fluxo recomendado para preparar o reconhecimento:
    1) Rode 'capturar_rostos.py' para tirar amostras de cada pessoa.
    2) Rode 'treinar_modelo.py' para gerar o 'classificadoreigen.yml'.
    3) A assistente já consegue reconhecer via comando de voz.
"""

import os
import cv2

from .cv_utils import carregar_classificador_face, carregar_modelo


class ReconhecimentoFacial:
    """Encapsula a detecção e o reconhecimento facial via webcam."""

    def __init__(
        self,
        modelo_yml: str = "classificadoreigen.yml",
        largura: int = 220,
        altura: int = 220,
    ):
        self.modelo_yml = modelo_yml
        self.largura = largura
        self.altura = altura

        # Detector de faces (carregado de forma segura para caminhos acentuados).
        self.detector = carregar_classificador_face()

        # Mapa de rótulos (id -> nome). Ajuste conforme quem você cadastrou.
        # O id 0 é reservado para "Desconhecido" (dica do PDF).
        self.nomes = {
            0: "Desconhecido",
            1: "Natan",
            2: "Gustavo",
            3: "Lucas",
            4: "Joao",
            5: "Kayky",
            6: "Andre"
        }

    def reconhecer(self, limite_confianca: float = 4400.0) -> str:
        """
        Abre a webcam e tenta reconhecer a pessoa à frente.

        No EigenFaceRecognizer, quanto MENOR o valor de 'confianca', melhor
        é a correspondência. Acima de 'limite_confianca' tratamos como
        'Desconhecido'.

        Sobre o valor 4400: foi calibrado com as 300 fotos da pasta 'fotos/'
        (6 pessoas x 50), com o modelo de 50 componentes de treinar_modelo.py.
        Para simular um estranho, o modelo foi treinado com uma pessoa
        inteira de fora e testado nas fotos dela. Resultado:

            limiar | reconhece cadastrados | rejeita estranhos
             4100  |          78%          |       100%
             4400  |          85%          |        98%   <- escolhido
             5000  |          88%          |        86%

        Acima de 4400 cada ponto a mais para os cadastrados custa muitos
        pontos na rejeição de estranhos.

        IMPORTANTE: o número depende das fotos, da câmera, da iluminação e do
        num_components do treino. Se mudar qualquer um deles, recalibre. A
        janela mostra a confiança ao lado do nome - observe os valores nos
        acertos e nos erros e escolha um limiar entre as duas faixas.

        Retorna o nome reconhecido (ou 'Desconhecido'). Pressione 'q' para sair.
        """
        # Sem modelo treinado não há como reconhecer.
        if not os.path.exists(self.modelo_yml):
            print(
                f"[Face] Modelo '{self.modelo_yml}' não encontrado. "
                "Rode 'capturar_rostos.py' e depois 'treinar_modelo.py'."
            )
            return "modelo_ausente"

        reconhecedor = cv2.face.EigenFaceRecognizer_create()
        carregar_modelo(reconhecedor, self.modelo_yml)  # lê driblando o acento no path

        camera = cv2.VideoCapture(0)
        nome_final = "Desconhecido"
        fonte = cv2.FONT_HERSHEY_SIMPLEX

        # A janela é criada com nome fixo para conseguirmos detectar depois
        # se o usuário a fechou pelo botão vermelho do macOS.
        janela = "M.A.D.A.R.A. - Reconhecimento Facial (q p/ sair)"
        cv2.namedWindow(janela, cv2.WINDOW_AUTOSIZE)

        while True:
            ok, imagem = camera.read()
            if not ok:
                break

            imagem_cinza = cv2.cvtColor(imagem, cv2.COLOR_BGR2GRAY)
            faces = self.detector.detectMultiScale(
                imagem_cinza, scaleFactor=1.5, minSize=(30, 30)
            )

            for (x, y, l, a) in faces:
                # Recorta e redimensiona o rosto para o tamanho do treino.
                face = cv2.resize(
                    imagem_cinza[y : y + a, x : x + l], (self.altura, self.largura)
                )
                cv2.rectangle(imagem, (x, y), (x + l, y + a), (0, 0, 255), 2)

                # 'predict' devolve o id previsto e a confiança da previsão.
                id_previsto, confianca = reconhecedor.predict(face)
                if confianca > limite_confianca:
                    nome_final = "Desconhecido"
                else:
                    nome_final = self.nomes.get(id_previsto, "Desconhecido")

                cv2.putText(
                    imagem,
                    f"{nome_final} ({int(confianca)})",
                    (x, y - 10),
                    fonte,
                    0.8,
                    (0, 0, 255),
                    2,
                )

            cv2.imshow(janela, imagem)

            # No macOS a janela só responde ao teclado quando está em foco.
            # Aceitamos 'q' e ESC, e também o clique no botão de fechar.
            tecla = cv2.waitKey(1) & 0xFF
            if tecla in (ord("q"), 27):  # 27 = ESC
                break
            if cv2.getWindowProperty(janela, cv2.WND_PROP_VISIBLE) < 1:
                break

        camera.release()
        cv2.destroyAllWindows()

        # No macOS o destroyAllWindows() só tem efeito quando o loop de
        # eventos do Cocoa é processado depois dele. Sem estes waitKey a
        # janela vira um "fantasma" que não fecha e trava a aplicação.
        for _ in range(5):
            cv2.waitKey(1)

        return nome_final
