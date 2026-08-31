"""
Módulo de IA GENERATIVA da assistente M.A.D.A.R.A. (item 9).

Permite conversar com um LLM. Suporta dois provedores:
    - 'groq'   -> nuvem, gratuito, rápido (biblioteca 'groq').
    - 'ollama' -> local, roda modelos como llama3.2 na própria máquina.

Baseado nos códigos do professor:
    - teste_groq.py    (cliente Groq)
    - teste_ollama.py  (requisição HTTP ao Ollama local)

A chave da Groq é lida da variável de ambiente GROQ_API_KEY para não
expor segredos no código-fonte enviado ao GitHub.
"""

import requests

from .config import obter_variavel


class IAGenerativa:
    """Fala com um modelo de linguagem para responder perguntas abertas."""

    def __init__(
        self,
        provedor: str = "groq",
        modelo_groq: str = "openai/gpt-oss-20b",
        modelo_ollama: str = "llama3.2:3b",
    ):
        self.provedor = provedor
        self.modelo_groq = modelo_groq
        self.modelo_ollama = modelo_ollama
        self.instrucao_sistema = (
            # "Você é o MADARA, uma assistente pessoal em português do Brasil. "
            # "Responda de forma breve, clara e útil, em no máximo 60 palavras."
            "Você é o MADARA, um ninja assustador do universo de Naruto Shippuden, além de um assistente pessoal em português do Brasil. "
            "Responda de forma breve, clara e útil, em no máximo 60 palavras. Porém se a pergunta contiver algum elemento que cita a obra de Naruto, pode responder como o Madara Uchiha responderia."
        )

    def responder(self, pergunta: str) -> str:
        """Direciona a pergunta para o provedor configurado."""
        if self.provedor == "ollama":
            return self._responder_ollama(pergunta)
        return self._responder_groq(pergunta)

    # ------------------------------------------------------------------ #
    #  Provedor 1: Groq (nuvem)
    # ------------------------------------------------------------------ #
    @staticmethod
    def _obter_chave_groq() -> str | None:
        """
        Procura a chave da Groq na variável de ambiente GROQ_API_KEY ou no
        arquivo '.env' (usando o utilitário compartilhado em config.py).
        """
        return obter_variavel("GROQ_API_KEY")

    def _responder_groq(self, pergunta: str) -> str:
        """Consulta a API da Groq usando a chave em GROQ_API_KEY (ou .env)."""
        chave = self._obter_chave_groq()
        if not chave:
            return (
                "Não encontrei a chave da Groq. Defina a variável de ambiente "
                "GROQ_API_KEY (e reabra o terminal) ou crie um arquivo .env "
                "com a linha GROQ_API_KEY=sua_chave. Ou use o provedor Ollama."
            )
        try:
            from groq import Groq

            cliente = Groq(api_key=chave)
            resposta = cliente.chat.completions.create(
                model=self.modelo_groq,
                messages=[
                    {"role": "system", "content": self.instrucao_sistema},
                    {"role": "user", "content": pergunta},
                ],
            )
            return resposta.choices[0].message.content.strip()
        except Exception as erro:
            return f"Não consegui falar com a IA da Groq: {erro}"

    # ------------------------------------------------------------------ #
    #  Provedor 2: Ollama (local)
    # ------------------------------------------------------------------ #
    def _responder_ollama(self, pergunta: str) -> str:
        """Consulta um modelo rodando localmente via Ollama (porta 11434)."""
        try:
            resposta = requests.post(
                "http://localhost:11434/api/generate",
                json={
                    "model": self.modelo_ollama,
                    "prompt": f"{self.instrucao_sistema}\n\nPergunta: {pergunta}",
                    "stream": False,
                },
                timeout=60,
            )
            return resposta.json().get("response", "").strip()
        except Exception as erro:
            return f"Não consegui falar com o Ollama local: {erro}"
