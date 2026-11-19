"""Reproduz as figuras e a análise de erros do artigo da A2.

Reajusta floresta e logística no conjunto de desenvolvimento com os parâmetros,
representações e limiares congelados em modelos_selecionados.json, confere
tp/tn/fp/fn com metricas_teste.csv (modo aprendido) e grava (por padrão em resultados/a2/erros_e_figuras_artigo/):
  <saida>/erros/    erros por subgrupo (CSV) e resumo de FN/FP;
  <saida>/figuras/  quatro figuras (PDF e PNG).
A semente 4201 é a do ajuste final de freeze() em treinar_modelos.py; os
pipelines binários não são versionados, então são reajustados (cache=None).
"""

import argparse
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib.patches import Patch
from matplotlib.ticker import FuncFormatter
from scipy.stats import chi2_contingency
from threadpoolctl import threadpool_limits

from preparar_modelagem import ROOT
from treinar_modelos import load_frame
from modelos_ucmf import pipeline
from representacoes_ucmf import input_frame

SEED = 4201
MODELOS = ['floresta', 'logistica']
EXP = ROOT / 'resultados/experimentos/v3'


# ---------- Reprodução do teste ----------
def reproduzir():
    frame = load_frame(ROOT / 'resultados/preparo/UCMF_supervisionado.csv')
    part = pd.read_csv(EXP / 'particao_principal.csv', dtype='string')
    assert list(part.ID) == list(frame.ID), 'Partição não corresponde à base'
    frame['conjunto'] = part.conjunto.values
    dev = frame[frame.conjunto == 'desenvolvimento'].reset_index(drop=True)
    test = frame[frame.conjunto == 'teste'].reset_index(drop=True)
    cong = json.loads((EXP / 'modelos_selecionados.json').read_text(encoding='utf-8'))['models']
    pub = pd.read_csv(EXP / 'metricas_teste.csv')
    pub = pub[pub['mode'] == 'aprendido'].set_index('model')
    yt = test.y.to_numpy()
    pred = {}
    for nome in MODELOS:
        c = cong[nome]
        with threadpool_limits(limits=1):
            m = pipeline(nome, c['params'], SEED, None, c['representation'])
            m.fit(input_frame(dev), dev.y.to_numpy())
            p = m.predict_proba(input_frame(test))[:, 1]
        pr = p >= c['threshold_info']['threshold']
        got = dict(tp=(pr & (yt == 1)).sum(), tn=(~pr & (yt == 0)).sum(),
                   fp=(pr & (yt == 0)).sum(), fn=(~pr & (yt == 1)).sum())
        got = {k: int(v) for k, v in got.items()}
        exp = {k: int(pub.loc[nome, k]) for k in got}
        print(nome, 'MATCH' if got == exp else 'MISMATCH', got)
        if got != exp:
            sys.exit(f'Erro: {nome} não reproduz metricas_teste.csv (obtido {got}, publicado {exp}). '
                     'Verifique versões das bibliotecas em modelos_selecionados.json.')
        pred[nome] = pr.astype(int)
    return test, pred


# ---------- Análise de erros ----------
def tabela(d, col, m):
    linhas = []
    for k, g in d.groupby(col):
        y, p = g.y.values, g['pred_' + m].values
        tp = int(((y == 1) & (p == 1)).sum()); fn = int(((y == 1) & (p == 0)).sum())
        tn = int(((y == 0) & (p == 0)).sum()); fp = int(((y == 0) & (p == 1)).sum())
        linhas.append(dict(subgrupo=k, n_normal=int((y == 0).sum()), n_anormal=int((y == 1).sum()),
                           TP=tp, FN=fn, recall=tp / (tp + fn) if tp + fn else np.nan,
                           TN=tn, FP=fp, specificity=tn / (tn + fp) if tn + fp else np.nan))
    return pd.DataFrame(linhas)


def erros(test, pred, pasta):
    pasta.mkdir(parents=True, exist_ok=True)
    d = test.copy().astype(object).where(test.notna(), np.nan)
    for m in MODELOS:
        d['pred_' + m] = pred[m]
    mot = d.MOTIVO_UNIFICADO.astype(str).where(d.MOTIVO_UNIFICADO.notna(), np.nan)
    d['grp'] = mot.str.split(' → ').str[0].str.strip().fillna('Sem informação')
    d['det'] = mot.str.split(' → ').str[-1].str.strip()
    top = d.det.value_counts().head(8).index
    d['det8'] = np.where(d.det.isna(), 'Sem informação', np.where(d.det.isin(top), d.det, 'Demais'))
    d['b2'] = np.where(d.B2.isna(), 'Sem informação', np.where(d.B2 == 'Normal', 'Normal', 'Alterado'))
    d['hda'] = np.where(d.HDA_UNIFICADA.isna(), 'Sem informação',
                        np.where(d.HDA_UNIFICADA == 'Assintomático', 'Assintomático', 'Com sintoma'))
    d['pas'] = np.where(d['PA SISTOLICA'].isna(), 'PAS ausente', 'PAS presente')
    d['faixa'] = d.FAIXA_ETARIA.fillna('Sem informação')
    for col, nome in [('grp', 'motivo_grupo'), ('det8', 'motivo_detalhe'), ('b2', 'B2'),
                      ('faixa', 'faixa_etaria'), ('hda', 'HDA'), ('pas', 'PAS')]:
        for m in MODELOS:
            tabela(d, col, m).to_csv(pasta / f'{nome}_{m}.csv', index=False)
    fn = d[(d.y == 1) & (d.pred_floresta == 0)]
    fp = d[(d.y == 0) & (d.pred_floresta == 1)]
    resumo = [
        'Floresta no teste',
        f'FN n={len(fn)}; motivo grupo 5 ou 2: {100 * fn.grp.str[0].isin(["5", "2"]).mean():.1f}%; '
        f'B2 Normal: {100 * (fn.b2 == "Normal").mean():.1f}%',
        'FN por grupo de motivo:', fn.grp.value_counts().to_string(),
        f'FP n={len(fp)}; detalhe "6 - Sopro": {100 * (fp.det == "6 - Sopro").mean():.1f}%; '
        f'B2 Alterado: {100 * (fp.b2 == "Alterado").mean():.1f}%',
        'Detalhes de motivo mais frequentes (teste):', d.det.value_counts().head(10).to_string()]
    (pasta / 'resumo_fn_fp.txt').write_text('\n'.join(resumo) + '\n', encoding='utf-8')


# ---------- Figuras ----------
TXT, SP, GR, BL, OR = '#0b0b0b', '#52514e', '#d9d9d9', '#2a78d6', '#eb6834'
W = 3.45


def br(x, d=0):
    return f'{x:,.{d}f}'.replace(',', 'X').replace('.', ',').replace('X', '.')


FMT = FuncFormatter(lambda v, p: br(v, 0))


def estilo(ax, axis='x'):
    for s in ('left', 'bottom'):
        ax.spines[s].set_color(SP); ax.spines[s].set_linewidth(0.6)
    ax.grid(axis=axis, color=GR, linewidth=0.5); ax.set_axisbelow(True)
    ax.tick_params(width=0.6, color=SP, length=2.5)


def salvar(fig, pasta, nome):
    fig.savefig(pasta / f'{nome}.pdf', bbox_inches='tight', pad_inches=0.02)
    fig.savefig(pasta / f'{nome}.png', dpi=300, bbox_inches='tight', pad_inches=0.02)
    plt.close(fig)


def hb(ax, y, v, h, cor, hachura=False):
    b = ax.barh(y, v, h, color=cor, edgecolor='white' if hachura else cor, linewidth=0)
    if hachura:
        for r in b:
            r.set_hatch('////'); r.set_edgecolor('white')


def figuras(pasta):
    pasta.mkdir(parents=True, exist_ok=True)
    plt.rcParams.update({'font.family': 'STIXGeneral', 'mathtext.fontset': 'stix', 'font.size': 8,
        'xtick.labelsize': 7, 'ytick.labelsize': 7, 'pdf.fonttype': 42, 'text.color': TXT,
        'axes.labelcolor': TXT, 'xtick.color': TXT, 'ytick.color': TXT, 'axes.edgecolor': SP,
        'axes.linewidth': 0.6, 'axes.spines.top': False, 'axes.spines.right': False,
        'hatch.linewidth': 0.4, 'axes.axisbelow': True})

    # 1: sopro x classe (vazamento)
    d = pd.read_csv(ROOT / 'resultados/analise/UCMF_limpo.csv', dtype='string', encoding='utf-8-sig')
    d = d[d['NORMAL X ANORMAL'].notna() & d.SOPRO.notna()]
    t = d['NORMAL X ANORMAL']
    n = {c: int((t == c).sum()) for c in ['Normal', 'Anormal']}
    cat = d.SOPRO.map(lambda s: s if s in ('Ausente', 'Sistólico') else 'Outros')
    ct = pd.crosstab(cat, t).loc[['Ausente', 'Sistólico', 'Outros']]
    pct = ct / ct.sum() * 100
    full = pd.crosstab(d.SOPRO, t)
    chi = chi2_contingency(full, correction=False)[0]
    print('Fig. sopro: n', n, 'V de Cramér', round(float(np.sqrt(chi / (full.values.sum() * (min(full.shape) - 1)))), 3))
    fig, ax = plt.subplots(figsize=(W, 1.45)); estilo(ax, 'x')
    pos = np.arange(3)[::-1]; h = 0.32
    for off, c, cor, ht in [(h / 2 + 0.01, 'Normal', BL, False), (-h / 2 - 0.01, 'Anormal', OR, True)]:
        hb(ax, pos + off, pct[c].values, h, cor, ht)
        for p_, v in zip(pos + off, pct[c].values):
            ax.text(v + 1, p_, f'{br(v, 1)}%', va='center', ha='left', fontsize=7)
    ax.set_yticks(pos); ax.set_yticklabels(ct.index); ax.set_xlim(0, 105); ax.set_ylim(-0.6, 2.6)
    ax.set_xlabel('Percentual dentro da classe (%)'); ax.xaxis.set_major_formatter(FMT)
    ax.tick_params(axis='y', length=0)
    ax.legend(handles=[Patch(facecolor=BL, label=f'Normal (n={br(n["Normal"])})'),
                       Patch(facecolor=OR, hatch='////', edgecolor='white', linewidth=0,
                             label=f'Anormal (n={br(n["Anormal"])})')],
              loc='lower right', frameon=False, fontsize=7, handlelength=1.4)
    salvar(fig, pasta, 'fig_sopro_vazamento')

    # 2: prevalência de anormal por motivo
    s = pd.read_csv(ROOT / 'resultados/preparo/UCMF_supervisionado.csv', dtype='string', encoding='utf-8-sig')
    s['det'] = s.MOTIVO_UNIFICADO.str.split(' → ').str[-1].str.strip()
    s['y'] = (s['NORMAL X ANORMAL'] == 'Anormal').astype(int)
    prev = s.y.mean()
    g = s.groupby('det').y.agg(['mean', 'count', 'sum']).sort_values('count', ascending=False).head(8).sort_values('mean', ascending=False)
    lab = [re.sub(r'^\d+ - ', '', i) for i in g.index]
    fig, ax = plt.subplots(figsize=(W, 1.9)); estilo(ax, 'x')
    y = np.arange(len(g))[::-1]
    ax.barh(y, g['mean'] * 100, 0.62, color=OR, edgecolor='white', linewidth=0)
    for r in ax.patches:
        r.set_hatch('////'); r.set_edgecolor('white')
    for yy, m, c in zip(y, g['mean'], g['count']):
        ax.text(m * 100 + 1, yy, f'{br(m * 100, 1)}% (n={br(c)})', va='center', fontsize=7, zorder=5,
                bbox=dict(fc='white', ec='none', pad=0.6))
    ax.axvline(prev * 100, color=SP, ls='--', lw=0.7, zorder=1)
    ax.text(prev * 100 + 0.8, -0.95, 'prevalência global', fontsize=6.5, color=SP, va='center', ha='left')
    ax.set_yticks(y); ax.set_yticklabels(lab); ax.set_xlim(0, 118); ax.set_ylim(-1.3, len(g) - 0.4)
    ax.set_xticks(range(0, 101, 20)); ax.xaxis.set_major_formatter(FMT)
    ax.set_xlabel('% Anormal'); ax.tick_params(axis='y', length=0)
    salvar(fig, pasta, 'fig_motivo_alvo')

    # 3: matrizes de confusão no teste (de metricas_teste.csv)
    mt = pd.read_csv(EXP / 'metricas_teste.csv')
    mt = mt[mt['mode'] == 'aprendido'].set_index('model')
    fig, axs = plt.subplots(1, 2, figsize=(W, 1.55)); cmap = plt.get_cmap('Blues')
    for ax, (m, tt) in zip(axs, [('logistica', 'Regressão logística'), ('floresta', 'Random Forest (selecionado)')]):
        r = mt.loc[m]
        M = np.array([[r.tn, r.fp], [r.fn, r.tp]]).astype(int); P = M / M.sum(1, keepdims=True) * 100
        ax.imshow(P, cmap=cmap, vmin=0, vmax=100, aspect='auto')
        for i in range(2):
            for j in range(2):
                ax.text(j, i, f'{br(M[i, j])}\n({br(P[i, j], 1)}%)', ha='center', va='center',
                        fontsize=7, color='white' if P[i, j] > 50 else TXT)
        ax.set_xticks([0, 1]); ax.set_xticklabels(['Normal', 'Anormal'])
        ax.set_yticks([0, 1]); ax.set_yticklabels(['Normal', 'Anormal'], rotation=90, va='center')
        ax.set_title(tt, fontsize=8, pad=3); ax.set_xlabel('Predito'); ax.tick_params(length=0)
        for sp in ax.spines.values():
            sp.set_visible(False)
    axs[0].set_ylabel('Real'); axs[1].set_yticklabels([])
    fig.subplots_adjust(wspace=0.08)
    salvar(fig, pasta, 'fig_matrizes')

    # 4: importância por permutação
    p = pd.read_csv(EXP / 'importancia_permutacao.csv')
    a = p.groupby('feature').ap_drop.agg(['mean', 'std']).sort_values('mean', ascending=False)
    nm = {'MOTIVO_UNIFICADO': 'Motivo do encaminhamento', 'B2': 'B2 (2ª bulha)', 'HDA_UNIFICADA': 'HDA (sintomas)',
          'FC': 'Frequência cardíaca', 'FAIXA_ETARIA': 'Faixa etária', 'SEXO': 'Sexo',
          'PPA_CALCULADA': 'Classificação da PA', 'CLASSIFICACAO IMC': 'Classificação do IMC', 'PULSOS': 'Pulsos'}
    fig, ax = plt.subplots(figsize=(W, 1.75)); estilo(ax, 'x'); y = np.arange(len(a))[::-1]
    ax.barh(y, a['mean'], 0.62, color=BL, xerr=a['std'],
            error_kw=dict(ecolor=SP, elinewidth=0.5, capsize=1.2, capthick=0.5))
    for yy, m, sd in zip(y, a['mean'], a['std']):
        ax.text(m + sd + 0.004, yy, br(m, 3), va='center', fontsize=7)
    ax.set_yticks(y); ax.set_yticklabels([nm.get(i, i) for i in a.index])
    ax.set_xlim(0, a['mean'].max() + a['std'].max() + 0.04)
    ax.xaxis.set_major_formatter(FuncFormatter(lambda v, _: br(v, 2)))
    ax.set_xlabel('Queda média na AP (permutação)'); ax.tick_params(axis='y', length=0)
    salvar(fig, pasta, 'fig_importancia')


def main():
    ap = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    ap.add_argument('--saida', type=Path, default=ROOT / 'resultados/a2' / 'erros_e_figuras_artigo')
    args = ap.parse_args()
    test, pred = reproduzir()
    erros(test, pred, args.saida / 'erros')
    figuras(args.saida / 'figuras')
    print('Saídas em', args.saida)


if __name__ == '__main__':
    main()
