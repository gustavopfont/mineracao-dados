"""Verificações de regressão para erros observados no conjunto UCMF."""

from __future__ import annotations

import csv
import sys
import unittest
from datetime import date, timedelta
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from analise_dataset import parse_date, read_dataset  # noqa: E402
from classificacao_imc import classificar_imc_pediatrico  # noqa: E402


class UcmfPipelineTest(unittest.TestCase):
    def test_tres_linhas_com_virgula_na_data_nao_deslocam_campos(self) -> None:
        raw = read_dataset(ROOT / "dados/UCMF_raw.csv").set_index("ID")
        self.assertEqual(len(raw), 12873)
        self.assertEqual(raw.at["12394", "DN"], "Ago/28,/1991")
        self.assertEqual(raw.at["12394", "PA SISTOLICA"], "110.0")
        self.assertEqual(raw.at["12394", "SEXO"], "M")
        for identifier in ("16368", "16369"):
            self.assertEqual(raw.at[identifier, "DN"], "18/10,1996")
            self.assertEqual(raw.at[identifier, "SEXO"], "F")

    def test_datas_textuais_e_seriais(self) -> None:
        self.assertEqual(parse_date("11/05/06")[0], date(2006, 5, 11))
        self.assertEqual(parse_date("18/10,1996")[0], date(1996, 10, 18))
        self.assertEqual(parse_date("38062")[0], date(1899, 12, 30) + timedelta(days=38062))
        self.assertIsNone(parse_date("8/anos")[0])

    def test_referencia_oms_aplica_cortes_por_idade_e_sexo(self) -> None:
        self.assertEqual(
            classificar_imc_pediatrico(0, "Masculino", 17)["classificacao"],
            "Sobrepeso",
        )
        self.assertEqual(
            classificar_imc_pediatrico(0, "Masculino", 14)["classificacao"],
            "Eutrofia",
        )
        self.assertIsNone(
            classificar_imc_pediatrico(0, "Indeterminado", 17)["classificacao"]
        )

    def test_saida_csv_e_dominio(self) -> None:
        path = ROOT / "resultados/analise" / "UCMF_limpo.csv"
        with path.open(encoding="utf-8-sig", newline="") as stream:
            reader = csv.reader(stream)
            header = next(reader)
            lengths = {len(row) for row in reader}
        self.assertEqual(len(header), 22)
        self.assertEqual(lengths, {22})
        clean = pd.read_csv(path, dtype="string", encoding="utf-8-sig")
        self.assertEqual(len(clean), 12134)
        self.assertTrue(clean["ID"].is_unique)
        self.assertFalse(clean["PPA"].eq("Não Calculado").any())
        self.assertTrue(clean["SEXO"].dropna().isin(
            ["Masculino", "Feminino", "Indeterminado"]
        ).all())
        ages = pd.to_numeric(clean["IDADE"], errors="coerce").dropna()
        self.assertTrue(ages.between(0, 20, inclusive="left").all())
        bmi = pd.to_numeric(clean["IMC"], errors="coerce").dropna()
        self.assertTrue(((bmi > 8) & (bmi <= 70)).all())
        row = clean.set_index("ID").loc["12394"]
        self.assertEqual(row["NORMAL X ANORMAL"], "Anormal")
        self.assertEqual(row["SEXO"], "Masculino")


if __name__ == "__main__":
    unittest.main()
