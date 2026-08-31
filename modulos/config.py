"""
Módulo de CONFIGURAÇÃO da assistente M.A.D.A.R.A.

Função utilitária para ler segredos/configurações (chaves de API, ids de voz)
de duas fontes, nesta ordem:
    1) Variáveis de ambiente do sistema.
    2) Um arquivo '.env' na pasta do projeto (formato CHAVE=valor).

O '.env' é prático porque variáveis criadas por 'setx' só passam a valer em
terminais abertos DEPOIS, o que costuma confundir na hora de rodar.
O arquivo '.env' está no .gitignore e NÃO deve ser enviado ao GitHub.
"""

import os


def obter_variavel(nome: str, padrao: str | None = None) -> str | None:
    """Retorna o valor de 'nome' vindo do ambiente ou do arquivo .env."""
    # 1) Variável de ambiente.
    valor = os.getenv(nome)
    if valor:
        return valor.strip()

    # 2) Fallback: procura a chave dentro de um arquivo .env local.
    if os.path.exists(".env"):
        with open(".env", "r", encoding="utf-8") as arquivo:
            for linha in arquivo:
                linha = linha.strip()
                if not linha or linha.startswith("#") or "=" not in linha:
                    continue
                chave, _, bruto = linha.partition("=")
                if chave.strip() == nome:
                    # remove aspas simples/duplas ao redor do valor, se houver
                    limpo = bruto.strip().strip('"').strip("'")
                    if limpo:
                        return limpo
    return padrao
