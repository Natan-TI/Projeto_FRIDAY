"""
Pacote 'modulos' do Projeto M.A.D.A.R.A.

Reúne as classes responsáveis por cada funcionalidade da assistente:
    - Voz                  -> reconhecimento e síntese de fala
    - Agenda               -> cadastro, leitura e limpeza de eventos
    - ReconhecimentoFacial -> abre a webcam e reconhece o usuário
    - IAGenerativa         -> integração com LLMs (Groq na nuvem / Ollama local)
    - Utilidades           -> hora, data, cálculos, cotações, clima, etc.
    - JogoDaVelha          -> mini-game jogado por voz
"""

from .voz import Voz
from .agenda import Agenda
from .reconhecimento_facial import ReconhecimentoFacial
from .ia_generativa import IAGenerativa
from .utilidades import Utilidades
from .jogo_da_velha import JogoDaVelha

__all__ = [
    "Voz",
    "Agenda",
    "ReconhecimentoFacial",
    "IAGenerativa",
    "Utilidades",
    "JogoDaVelha",
]
