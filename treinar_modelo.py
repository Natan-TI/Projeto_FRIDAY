"""
Script AUXILIAR - Treinamento do modelo de reconhecimento facial (item 7).

Lê todas as imagens da pasta 'fotos/', associa cada pessoa a um id numérico
e treina um EigenFaceRecognizer, salvando o resultado em
'classificadoreigen.yml' (o modelo pré-treinado usado pela assistente).

IMPORTANTE: os ids abaixo devem ser os MESMOS do dicionário 'self.nomes'
em modulos/reconhecimento_facial.py.

Como usar:
    1) Capture rostos com 'capturar_rostos.py'.
    2) Rode:  python treinar_modelo.py

Baseado no 'treinamento.py' do professor, com suporte a caminhos acentuados
no Windows (via modulos/cv_utils.py).
"""

import os
import unicodedata

import cv2
import numpy as np

from modulos.cv_utils import imread_unicode, salvar_modelo

# Reconhecedor Eigenfaces.
eigen = cv2.face.EigenFaceRecognizer_create()

# Mapa Nome -> id. O id 0 é reservado para "Desconhecido".
# A CHAVE deve ser exatamente o trecho do nome do arquivo antes do "_".
# Ex.: "gustavo_1.jpg" -> chave "gustavo"; "João Pedro_1.jpg" -> "João Pedro".
MAPA_IDS = {
    # Fotos capturadas com o nome "Desconhecido" viram exemplos NEGATIVOS.
    # Servem para o modelo ter com o que comparar, mas não são o mecanismo
    # principal de rejeição - quem decide isso é o 'limite_confianca' em
    # modulos/reconhecimento_facial.py.
    "Desconhecido": 0,
    "Natan": 1,
    "gustavo": 2,
    "Lucas": 3,
    "João Pedro": 4,
}


def carregar_imagens(pasta: str = "fotos"):
    """
    Percorre a pasta de fotos e devolve:
        - um array de ids (rótulos) e
        - uma lista de imagens em tons de cinza (as faces).
    """
    caminhos = [
        os.path.join(pasta, f)
        for f in os.listdir(pasta)
        if f.lower().endswith((".jpg", ".jpeg", ".png"))
    ]
    faces = []
    ids = []
    nao_mapeados = set()

    for caminho in caminhos:
        imagem = imread_unicode(caminho)  # lê mesmo com acento no path
        if imagem is None:
            continue
        imagem_cinza = cv2.cvtColor(imagem, cv2.COLOR_BGR2GRAY)

        # O nome vem do início do arquivo: 'Natan_1.jpg' -> 'Natan'.
        # O normalize("NFC") é obrigatório no macOS: o sistema de arquivos
        # guarda "João" na forma decomposta (a + til separados), que NÃO é
        # igual ao "João" escrito aqui no código. Sem isso a busca no
        # MAPA_IDS falha silenciosamente e a pessoa vira "Desconhecido".
        nome = unicodedata.normalize("NFC", os.path.split(caminho)[-1].split("_")[0])
        if nome not in MAPA_IDS:
            # Sem esse aviso o treino rodaria "com sucesso", mas jogaria todo
            # mundo que falta no MAPA_IDS dentro do mesmo id 0 (Desconhecido).
            nao_mapeados.add(nome)
        ids.append(MAPA_IDS.get(nome, 0))  # desconhecido = 0
        faces.append(imagem_cinza)

    if nao_mapeados:
        print("\n*** ATENÇÃO ***")
        print("Estes nomes não estão no MAPA_IDS e foram treinados como id 0:")
        for nome in sorted(nao_mapeados):
            print(f"  - {nome}")
        print("Adicione-os ao MAPA_IDS (e ao 'self.nomes' em")
        print("modulos/reconhecimento_facial.py) e treine de novo.\n")

    return np.array(ids), faces


if __name__ == "__main__":
    ids, faces = carregar_imagens()

    if len(faces) == 0:
        print("Nenhuma foto encontrada em 'fotos/'. Rode 'capturar_rostos.py' antes.")
    else:
        import collections

        contagem = collections.Counter(ids.tolist())
        print("Fotos por id:")
        for id_pessoa, total in sorted(contagem.items()):
            nome = next((n for n, i in MAPA_IDS.items() if i == id_pessoa), "Desconhecido")
            print(f"  id {id_pessoa} ({nome}): {total} fotos")
        eigen.train(faces, ids)
        salvar_modelo(eigen, "classificadoreigen.yml")  # salva driblando o acento no path
        print("Modelo treinado e salvo em 'classificadoreigen.yml'!")
