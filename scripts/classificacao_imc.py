"""Classificação descritiva do IMC por idade e sexo com tabelas da OMS.

As referências compactas em referencias/ preservam os pontos de corte
publicados pela OMS: idade diária até 60 meses e mensal de 61 a 228 meses.
Esta classificação não substitui avaliação clínica.
"""

from __future__ import annotations

import math
from functools import lru_cache
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]


@lru_cache(maxsize=1)
def carregar_referencias() -> tuple[pd.DataFrame, pd.DataFrame]:
    inicial = pd.read_csv(ROOT / "referencias" / "imc_oms_0_5.csv", encoding="utf-8-sig")
    posterior = pd.read_csv(ROOT / "referencias" / "imc_oms_5_19.csv", encoding="utf-8-sig")
    return inicial.set_index(["SEXO", "idade_dias"]), posterior.set_index(["SEXO", "idade_meses"])


def classificar_imc_pediatrico(idade_dias: int, sexo: str, imc: float) -> dict:
    """Retorna a categoria e a referência exata usada, ou a razão da ausência."""
    if sexo not in {"Masculino", "Feminino"} or not math.isfinite(imc) or imc <= 0:
        return {"classificacao": None, "motivo": "sexo ou IMC ausente/inválido"}
    if idade_dias < 0:
        return {"classificacao": None, "motivo": "idade ausente/inválida"}

    meses = int(math.floor(idade_dias * 12 / 365.25))
    diario, mensal = carregar_referencias()
    if meses <= 60 and idade_dias <= 1856:
        chave = (sexo, idade_dias)
        tabela, referencia = diario, "OMS 2006, 0–5 anos"
    elif 61 <= meses <= 228:
        chave = (sexo, meses)
        tabela, referencia = mensal, "OMS 2007, 5–19 anos"
    else:
        return {"classificacao": None, "motivo": "idade fora da referência OMS"}
    if chave not in tabela.index:
        return {"classificacao": None, "motivo": "idade sem ponto de referência"}

    corte = tabela.loc[chave]
    if imc < corte["z_menos_3"]:
        categoria = "Magreza acentuada"
    elif imc < corte["z_menos_2"]:
        categoria = "Magreza"
    elif imc <= corte["z_mais_1"]:
        categoria = "Eutrofia"
    elif meses <= 60 and imc <= corte["z_mais_2"]:
        categoria = "Risco de sobrepeso"
    elif imc <= corte["z_mais_2"]:
        categoria = "Sobrepeso"
    elif meses <= 60 and imc <= corte["z_mais_3"]:
        categoria = "Sobrepeso"
    else:
        categoria = "Obesidade"
    return {
        "classificacao": categoria,
        "motivo": "classificação aplicada",
        "referencia": referencia,
        "idade_referencia": chave[1],
    }
