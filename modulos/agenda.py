"""
Módulo de AGENDA da assistente M.A.D.A.R.A.

Responsável pelos itens 2, 3 e 8 do desafio:
    - Cadastrar eventos (grava em 'agenda.txt').
    - Ler todos os eventos cadastrados.
    - Limpar a agenda (apaga o conteúdo SEM excluir o arquivo).
"""

import os
from datetime import datetime


class Agenda:
    """Gerencia o arquivo de texto que armazena os eventos do usuário."""

    def __init__(self, caminho_arquivo: str = "agenda.txt"):
        self.caminho_arquivo = caminho_arquivo
        # Garante que o arquivo exista assim que a agenda é criada.
        self._garantir_arquivo()

    def _garantir_arquivo(self) -> None:
        """Cria o arquivo agenda.txt vazio caso ele ainda não exista."""
        if not os.path.exists(self.caminho_arquivo):
            with open(self.caminho_arquivo, "w", encoding="utf-8"):
                pass  # apenas cria o arquivo vazio

    def cadastrar_evento(self, evento: str) -> None:
        """
        Adiciona um novo evento ao arquivo agenda.txt.
        Cada linha recebe a data/hora do cadastro seguida da descrição.
        """
        carimbo = datetime.now().strftime("%d/%m/%Y %H:%M")
        with open(self.caminho_arquivo, "a", encoding="utf-8") as arquivo:
            arquivo.write(f"[{carimbo}] {evento}\n")

    def ler_eventos(self) -> list[str]:
        """Retorna uma lista com todos os eventos cadastrados (sem vazios)."""
        self._garantir_arquivo()
        with open(self.caminho_arquivo, "r", encoding="utf-8") as arquivo:
            linhas = [linha.strip() for linha in arquivo if linha.strip()]
        return linhas

    def esta_vazia(self) -> bool:
        """Informa se a agenda não possui nenhum evento cadastrado."""
        return len(self.ler_eventos()) == 0

    def limpar(self) -> None:
        """
        Apaga TODOS os eventos, mas mantém o arquivo agenda.txt existindo
        (abrir em modo 'w' zera o conteúdo sem remover o arquivo).
        """
        with open(self.caminho_arquivo, "w", encoding="utf-8"):
            pass
