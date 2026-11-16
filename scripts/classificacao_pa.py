"""Classificação descritiva da medida de PA pela DBHA 2025, sem diagnóstico."""
from __future__ import annotations

import csv
import hashlib
import json
import math
from datetime import date
from functools import lru_cache
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REFERENCE = ROOT / 'referencias/pa_dbha_2025.csv'
CATEGORIES = ['Normal', 'Pré-hipertensão', 'HA estágio 1', 'HA estágio 2', 'HA estágio 3']
AGE_BANDS = [(1, 'Menor de 1 ano'), (3, '1–2 anos'), (6, '3–5 anos'),
             (13, '6–12 anos'), (18, '13–17 anos'), (20, '18–19 anos')]


def number(value: object) -> float | None:
    try:
        result = float(value)
        return result if math.isfinite(result) else None
    except (ValueError, TypeError):
        return None


def age_context(row: dict) -> dict:
    """Anos completos por aniversário; IDADE decimal só como alternativa."""
    try:
        visit = date.fromisoformat(str(row.get('Atendimento', '')))
        birth = date.fromisoformat(str(row.get('DN', '')))
        years = visit.year - birth.year - ((visit.month, visit.day) < (birth.month, birth.day))
        if visit >= birth and 0 <= years < 20:
            return dict(idade_anos_completos=years, origem_idade='datas',
                        faixa_etaria=next(label for upper, label in AGE_BANDS if years < upper))
    except ValueError:
        pass
    age = number(row.get('IDADE'))
    if age is not None and 0 <= age < 20:
        return dict(idade_anos_completos=math.floor(age), origem_idade='IDADE disponível',
                    faixa_etaria=next(label for upper, label in AGE_BANDS if age < upper))
    return dict(idade_anos_completos=None, origem_idade='indisponível', faixa_etaria=None)


@lru_cache(maxsize=1)
def reference() -> dict:
    metadata = json.loads(REFERENCE.with_suffix('.json').read_text(encoding='utf-8'))
    if hashlib.sha256(REFERENCE.read_bytes()).hexdigest() != metadata['sha256_csv']:
        raise ValueError('Referência de PA não corresponde ao hash versionado')
    with REFERENCE.open(encoding='utf-8') as stream:
        rows = list(csv.DictReader(stream))
    groups = {}
    for row in rows:
        key = (row['sexo'], int(row['idade_anos']))
        groups.setdefault(key, []).append({k: float(v) for k, v in row.items() if k != 'sexo'})
    expected = {(sex, year) for sex in ['Masculino', 'Feminino'] for year in range(1, 13)}
    if set(groups) != expected or len(rows) != 168:
        raise ValueError('Referência de PA incompleta')
    for points in groups.values():
        points.sort(key=lambda p: p['altura_cm'])
        if len(points) != 7 or len({p['altura_cm'] for p in points}) != 7:
            raise ValueError('Grade de altura inválida')
        if any(p['pas_p90'] > p['pas_p95'] or p['pad_p90'] > p['pad_p95'] for p in points):
            raise ValueError('Percentis de pressão inválidos')
    return groups


def pediatric_thresholds(age: int, sex: str, height: float) -> dict | None:
    points = reference()[(sex, age)]
    if not points[0]['altura_cm'] <= height <= points[-1]['altura_cm']:
        return None
    for left, right in zip(points, points[1:]):
        if left['altura_cm'] <= height <= right['altura_cm']:
            ratio = (height-left['altura_cm'])/(right['altura_cm']-left['altura_cm'])
            return {key: left[key]+ratio*(right[key]-left[key])
                    for key in ['pas_p90', 'pas_p95', 'pad_p90', 'pad_p95']}
    raise AssertionError('Altura sem intervalo na referência')


def classify_pressure(age: int | None, sex: str, height: object,
                      systolic: object, diastolic: object) -> dict:
    result = dict(classificacao=None, motivo='', referencia='',
                  pas_elevada=None, pad_elevada=None, pas_estagio1=None,
                  pad_estagio1=None, pas_estagio2=None, pad_estagio2=None,
                  pas_estagio3=None, pad_estagio3=None)
    if age is None or not 0 <= age < 20:
        result['motivo'] = 'idade ausente ou inválida'
        return result
    if age < 1:
        result['motivo'] = 'menor de 1 ano: fora da referência adotada'
        return result
    pas, pad = number(systolic), number(diastolic)
    if pas is None or pad is None:
        result['motivo'] = 'PAS ou PAD ausente/inválida'
        return result
    if not (40 < pas <= 250 and 20 < pad <= 150 and pas > pad):
        result['motivo'] = 'PAS/PAD fora dos limites técnicos ou contraditórias'
        return result
    if age < 13:
        if sex not in {'Masculino', 'Feminino'}:
            result['motivo'] = 'sexo ausente ou sem referência'
            return result
        cm = number(height)
        if cm is None:
            result['motivo'] = 'altura ausente/inválida'
            return result
        thresholds = pediatric_thresholds(age, sex, cm)
        if thresholds is None:
            result['motivo'] = 'altura fora da grade: sem extrapolação'
            return result
        result['referencia'] = 'DBHA 2025 tabelas 9.1–9.3; interpolação em cm'
        pairs = [(min(thresholds['pas_p90'], 120), min(thresholds['pad_p90'], 80)),
                 (min(thresholds['pas_p95'], 130), min(thresholds['pad_p95'], 80)),
                 (min(thresholds['pas_p95']+12, 140), min(thresholds['pad_p95']+12, 90))]
    elif age < 18:
        result['referencia'] = 'DBHA 2025 tabela 9.1; 13–17 anos'
        pairs = [(120, 80), (130, 80), (140, 90)]
    else:
        result['referencia'] = 'DBHA 2025 quadro 3.2; ≥18 anos'
        pairs = [(120, 80), (140, 90), (160, 100), (180, 110)]
    for suffix, (s, d) in zip(['elevada', 'estagio1', 'estagio2', 'estagio3'], pairs):
        result[f'pas_{suffix}'], result[f'pad_{suffix}'] = s, d
    severity = max([0]+[i for i, (s, d) in enumerate(pairs, 1) if pas >= s or pad >= d])
    result.update(classificacao=CATEGORIES[severity], motivo='medida classificada; não confirma diagnóstico')
    return result
