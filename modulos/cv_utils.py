"""
Utilitários de OpenCV para lidar com CAMINHOS ACENTUADOS no Windows.

Contexto do problema:
    O OpenCV no Windows usa uma API de arquivos que NÃO entende caracteres
    acentuados (ex.: "Área de Trabalho", muito comum em pastas do OneDrive
    em português). Isso faz funções como CascadeClassifier(), imread(),
    imwrite() e FileStorage (.yml) falharem silenciosamente ou com erro
    "(-215:Assertion failed) !empty()".

Solução:
    - Para o classificador Haar e para o modelo .yml: copiamos o arquivo
      para uma pasta temporária de caminho SEM acento e carregamos de lá.
    - Para ler/gravar imagens: usamos numpy.fromfile / ndarray.tofile em
      conjunto com cv2.imdecode / cv2.imencode, que aceitam caminhos Unicode.
"""

import os
import shutil
import tempfile

import cv2
import numpy as np

# Pasta temporária do sistema (normalmente sem acento, ex.: ...\AppData\Local\Temp).
_PASTA_TEMP = tempfile.gettempdir()


def carregar_classificador_face() -> cv2.CascadeClassifier:
    """
    Devolve um CascadeClassifier de faces carregado a partir de uma cópia
    do XML em um caminho sem acento (evita o erro de path do OpenCV).
    """
    nome = "haarcascade_frontalface_default.xml"
    origem = os.path.join(cv2.data.haarcascades, nome)
    destino = os.path.join(_PASTA_TEMP, nome)

    # Copia o XML para o temp apenas na primeira vez.
    if not os.path.exists(destino):
        shutil.copyfile(origem, destino)

    classificador = cv2.CascadeClassifier(destino)
    if classificador.empty():
        raise RuntimeError(
            "Não foi possível carregar o haarcascade. Verifique a instalação "
            "do opencv-contrib-python."
        )
    return classificador


def imread_unicode(caminho: str, flags: int = cv2.IMREAD_COLOR):
    """Lê uma imagem mesmo que o caminho tenha caracteres acentuados."""
    dados = np.fromfile(caminho, dtype=np.uint8)  # numpy aceita path Unicode
    return cv2.imdecode(dados, flags)


def imwrite_unicode(caminho: str, imagem, extensao: str = ".jpg") -> bool:
    """Grava uma imagem mesmo que o caminho tenha caracteres acentuados."""
    ok, buffer = cv2.imencode(extensao, imagem)
    if ok:
        buffer.tofile(caminho)  # ndarray.tofile aceita path Unicode
    return bool(ok)


def salvar_modelo(reconhecedor, caminho: str) -> None:
    """
    Salva um reconhecedor (ex.: EigenFace) driblando o problema de path:
    grava em um .yml temporário sem acento e depois copia para o destino.
    """
    temp = os.path.join(_PASTA_TEMP, "madara_modelo_tmp.yml")
    reconhecedor.write(temp)
    shutil.copyfile(temp, caminho)


def carregar_modelo(reconhecedor, caminho: str) -> None:
    """
    Carrega um modelo .yml para dentro do reconhecedor driblando o path:
    copia o arquivo para um temporário sem acento e lê de lá.
    """
    temp = os.path.join(_PASTA_TEMP, "madara_modelo_read_tmp.yml")
    shutil.copyfile(caminho, temp)
    reconhecedor.read(temp)
