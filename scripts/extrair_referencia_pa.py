"""Extrai tabelas 9.2/9.3 do HTML oficial; usado só para atualizar a referência."""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
from pathlib import Path

from lxml import html

ROOT = Path(__file__).resolve().parents[1]
URL = 'https://www.scielo.br/j/abc/a/BXT7Vk4B9VKQnJFsJhgJ4Hn/?lang=pt'


def extract(source: Path, output: Path) -> None:
    document = html.fromstring(source.read_bytes())
    records = []
    for sex in ['Masculino', 'Feminino']:
        # Identificar pela legenda evita depender da numeração interna do HTML.
        candidates = document.xpath('//table')
        found = []
        for table in candidates:
            text = ' '.join(table.xpath('.//text()'))
            if 'Estatura (cm)' in text and 'P95' in text:
                found.append(table)
        if len(found) != 2:
            raise ValueError(f'Esperadas duas tabelas completas, encontradas {len(found)}')
        table = found[0 if sex == 'Masculino' else 1]
        age = None
        values = {}
        for tr in table.xpath('.//tr'):
            cells = [' '.join(' '.join(td.xpath('.//text()')).split())
                     for td in tr.xpath('./td|./th')]
            if not cells:
                continue
            if 'Estatura (cm)' in cells:
                age = int(cells[0])
                values = {'height': cells[-14:]}
            elif age is not None:
                label = next((x for x in cells if x in {'P90', 'P95'}), None)
                if label:
                    values[label] = cells[-14:]
                if label == 'P95' and 1 <= age <= 12:
                    for i, percentile in enumerate([5, 10, 25, 50, 75, 90, 95]):
                        def number(key, offset):
                            return float(values[key][i + offset].replace(',', '.'))
                        records.append(dict(sexo=sex, idade_anos=age,
                            percentil_estatura=percentile, altura_cm=number('height', 0),
                            pas_p90=number('P90', 0), pas_p95=number('P95', 0),
                            pad_p90=number('P90', 7), pad_p95=number('P95', 7)))
    if len(records) != 168:
        raise ValueError(f'Esperadas 168 linhas, obtidas {len(records)}')
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open('w', encoding='utf-8', newline='') as stream:
        writer = csv.DictWriter(stream, fieldnames=list(records[0]))
        writer.writeheader()
        writer.writerows(records)
    metadata = dict(fonte=URL, doi='10.36660/abc.20250624', tabelas=['9.2', '9.3'],
                    consulta='2026-11-07', linhas=len(records),
                    sha256_csv=hashlib.sha256(output.read_bytes()).hexdigest())
    output.with_suffix('.json').write_text(json.dumps(metadata, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('html', type=Path)
    parser.add_argument('--saida', type=Path, default=ROOT/'referencias/pa_dbha_2025.csv')
    args = parser.parse_args()
    extract(args.html, args.saida)
