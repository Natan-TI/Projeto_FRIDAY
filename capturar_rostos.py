"""
Script AUXILIAR - Captura de rostos para o reconhecimento facial (item 7).

Abre a webcam, detecta o rosto e salva amostras na pasta 'fotos/'.
As imagens são nomeadas como '<Nome>_<numero>.jpg', padrão esperado pelo
script de treinamento.

Como usar:
    1) Rode:  python capturar_rostos.py
    2) Digite o seu nome.
    3) Encare a webcam e pressione 'f' várias vezes para capturar amostras.
       (capture também amostras de outras pessoas usando o nome
        'Desconhecido' para melhorar o reconhecimento, conforme a dica do PDF)

Baseado no 'capturas.py' do professor, com suporte a caminhos acentuados
no Windows (via modulos/cv_utils.py).
"""

import os
import cv2
import numpy as np

from modulos.cv_utils import carregar_classificador_face, imwrite_unicode

# Detector de faces padrão do OpenCV (carregado de forma segura p/ acentos).
classificador = carregar_classificador_face()

camera = cv2.VideoCapture(0)
amostra = 1
numero_max_amostras = 25
nome = input("Digite seu nome (ou 'Desconhecido'): ").strip()

# Garante que a pasta de fotos exista.
os.makedirs("fotos", exist_ok=True)

# Todas as amostras são padronizadas neste tamanho (mesmo do treino/predição).
altura, largura = 220, 220

print("Pressione 'f' para capturar cada amostra. Serão coletadas até 25.")

while True:
    status, imagem = camera.read()
    if not status:
        break

    imagem_cinza = cv2.cvtColor(imagem, cv2.COLOR_BGR2GRAY)
    faces_detectadas = classificador.detectMultiScale(
        imagem_cinza, scaleFactor=1.05, minSize=(150, 150)
    )

    for (x, y, a, l) in faces_detectadas:
        cv2.rectangle(imagem, (x, y), (x + l, y + a), (0, 0, 255), 2)

        # Só salva a amostra quando o usuário pressiona 'f'.
        if cv2.waitKey(1) & 0xFF == ord("f"):
            media_luz = np.average(imagem_cinza)
            print("Média de luminosidade:", media_luz)

            # Evita capturar fotos muito escuras (baixa iluminação).
            if media_luz > 110:
                imagem_face = cv2.resize(
                    imagem_cinza[y : y + a, x : x + l], (largura, altura)
                )
                local_foto = f"fotos/{nome}_{amostra}.jpg"
                imwrite_unicode(local_foto, imagem_face)  # grava mesmo com acento no path
                print(f"Amostra {amostra} salva em {local_foto}")
                amostra += 1

    cv2.imshow("Captura de rostos (f = salvar)", imagem)

    if amostra > numero_max_amostras:
        break
    if cv2.waitKey(1) & 0xFF == ord("q"):
        break

print("Amostras capturadas com sucesso!")
camera.release()
cv2.destroyAllWindows()
