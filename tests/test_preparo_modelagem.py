"""Verifica a separação de grupos e o ajuste apenas no treino."""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from analise_dataset import canonical_category  # noqa: E402
from preparar_modelagem import (  # noqa: E402
    NUMERIC_COLUMNS, BEFORE_EXAM, build_preprocessor, duplicate_groups,
    fit_on_train, split_labeled,
)


class PreparoModelagemTest(unittest.TestCase):
    def test_categoria_fixa_independe_da_frequencia(self) -> None:
        self.assertEqual(canonical_category("Convenio", "Gs"), "GS")
        self.assertEqual(canonical_category("Convenio", "GS"), "GS")
        self.assertEqual(canonical_category("SEXO", "f"), "Feminino")

    def test_mesmas_caracteristicas_ficam_no_mesmo_grupo_sem_consultar_alvo(self) -> None:
        frame = pd.DataFrame({
            "ID": ["1", "2"], "IDADE": [3, 3], "SEXO": ["Feminino", "Feminino"],
            "NORMAL X ANORMAL": ["Normal", "Anormal"],
        })
        self.assertEqual(duplicate_groups(frame).iloc[0], duplicate_groups(frame).iloc[1])

    def test_estatisticas_e_vocabulario_sao_do_treino(self) -> None:
        def records(ages: list[float], reasons: list[str]) -> pd.DataFrame:
            data = {column: [10.0] * len(ages) for column in NUMERIC_COLUMNS}
            data["IDADE"] = ages
            data["SEXO"] = ["Feminino"] * len(ages)
            data["MOTIVO1"] = reasons
            return pd.DataFrame(data)

        train = records([2.0, 4.0, np.nan], ["Consulta"] * 3)
        test = records([100.0], ["Categoria inédita"])
        transformer, transformed_train, transformed_test = fit_on_train(
            train, test, NUMERIC_COLUMNS, BEFORE_EXAM
        )
        learned_median = transformer.named_transformers_["numericas"].named_steps[
            "imputar"
        ].statistics_[0]
        self.assertEqual(learned_median, 3.0)
        self.assertEqual(transformed_train.shape[1], transformed_test.shape[1])

    def test_divisao_real_nao_separa_grupos_iguais(self) -> None:
        frame = pd.read_csv(
            ROOT / "resultado_analise" / "UCMF_limpo.csv",
            dtype="string", encoding="utf-8-sig",
        )
        train, test, groups = split_labeled(frame)
        self.assertEqual(len(train) + len(test), 11705)
        self.assertFalse(set(groups.loc[train.index]) & set(groups.loc[test.index]))

    def test_sopro_ausente_nao_se_confunde_com_dado_faltante(self) -> None:
        values = ["Ausente"] * 10 + [np.nan] * 10 + ["Sistólico"] * 2
        transformer = build_preprocessor([], ["SOPRO"])
        transformer.fit(pd.DataFrame({"SOPRO": values}))
        observed = transformer.transform(pd.DataFrame({"SOPRO": ["Ausente", np.nan]}))
        self.assertFalse(np.array_equal(observed[0], observed[1]))


if __name__ == "__main__":
    unittest.main()
