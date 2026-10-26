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
#
# num_components = quantos "autorrostos" (padrões de variação entre os
# rostos) o PCA guarda. O padrão do OpenCV guarda todos - com 300 fotos
# seriam 300, gerando um arquivo de 399 MB que leva 1,3 s para carregar a
# cada "quem sou eu". Medindo com as fotos deste projeto, 50 componentes
# acertam quem é quem tão bem quanto todos (98,3%), com 67 MB e 0,2 s, e
# separam melhor os cadastrados dos estranhos.
# Se mudar este número, recalibre o 'limite_confianca' em
# modulos/reconhecimento_facial.py.
eigen = cv2.face.EigenFaceRecognizer_create(num_components=50)

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
    "Joao": 4,
    "Kayky": 5,
    "Andre": 6
}


def normalizar(nome: str) -> str:
    """
    Padroniza um nome para a busca no MAPA_IDS, tornando-a imune a:
        - MAIÚSCULAS/minúsculas  ("Gustavo" == "gustavo")
        - acentos                ("João" == "Joao")
        - espaços sobrando

    O acento importa por dois motivos: o macOS grava nomes de arquivo numa
    forma decomposta (o "ã" vira "a" + til separados), que NÃO é igual ao
    texto digitado aqui no código; e cada pessoa pode digitar o nome com ou
    sem acento na hora de capturar as fotos.
    """
    sem_acento = unicodedata.normalize("NFD", nome)
    sem_acento = "".join(c for c in sem_acento if not unicodedata.combining(c))
    return sem_acento.strip().casefold()


# Versão do MAPA_IDS pronta para a busca (chaves já normalizadas).
MAPA_BUSCA = {normalizar(nome): id_ for nome, id_ in MAPA_IDS.items()}


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
        nome = os.path.split(caminho)[-1].split("_")[0]
        chave = normalizar(nome)
        if chave not in MAPA_BUSCA:
            # Sem esse aviso o treino rodaria "com sucesso", mas jogaria todo
            # mundo que falta no MAPA_IDS dentro do mesmo id 0 (Desconhecido).
            nao_mapeados.add(nome)
        ids.append(MAPA_BUSCA.get(chave, 0))  # desconhecido = 0
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
            nome = next((n for n, i in MAPA_IDS.items() if i == id_pessoa), "?")
            print(f"  id {id_pessoa} ({nome}): {total} fotos")
        eigen.train(faces, ids)
        salvar_modelo(eigen, "classificadoreigen.yml")  # salva driblando o acento no path
        print("Modelo treinado e salvo em 'classificadoreigen.yml'!")
