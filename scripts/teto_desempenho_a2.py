"""Estima o teto de desempenho do classificador usando SÓ o desenvolvimento.

Parte 1: curvas de aprendizado (logística, floresta, boosting congelados) em
         CV 5x2 e extrapolação por lei de potência (AP = a - b*n^-c;
         erro = a + b*n^-c), IC95% por bootstrap dos 10 folds.
Parte 2: erro do 1-NN (três representações) extrapolado para n -> infinito e
         limites de Cover-Hart para o erro de Bayes, duplicatas conflitantes.
O teste nunca é usado (há asserções). Saídas em --saida (padrão
ROOT/resultados/a2/teto_desempenho).
Sementes: CV 11 e 22; subamostras 1000*fold+índice da fração; ajuste final
4201 (como em freeze()); bootstrap 2024.
"""

import argparse
import json
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from joblib import Parallel, delayed
from matplotlib.ticker import FuncFormatter
from scipy.optimize import curve_fit
from sklearn.dummy import DummyClassifier
from sklearn.metrics import average_precision_score
from sklearn.model_selection import StratifiedKFold, train_test_split
from sklearn.neighbors import KNeighborsClassifier
from sklearn.pipeline import Pipeline
from threadpoolctl import threadpool_limits

from preparar_modelagem import ROOT
from treinar_modelos import load_frame
from modelos_ucmf import pipeline
from representacoes_ucmf import input_frame, preprocessor, REPRESENTATIONS

EXP = ROOT / 'resultados/experimentos/v3'
SEED_FIT, SEED_BOOT = 4201, 2024
CV_SEEDS = (11, 22)
FRACOES = [0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 1.0]
MODELOS = ['logistica', 'floresta', 'boosting']
COR = {'logistica': '#2a78d6', 'floresta': '#eb6834', 'boosting': '#1baf7a'}


def carregar():
    frame = load_frame(ROOT / 'resultados/preparo/UCMF_supervisionado.csv')
    part = pd.read_csv(EXP / 'particao_principal.csv', dtype='string')
    assert list(part.ID) == list(frame.ID), 'Partição não corresponde à base'
    frame['conjunto'] = part.conjunto.values
    ids_teste = set(frame.ID[frame.conjunto == 'teste'])
    dev = frame[frame.conjunto == 'desenvolvimento'].reset_index(drop=True)
    assert len(dev) == 9148 and not ids_teste & set(dev.ID), 'Teste vazou para o desenvolvimento'
    cong = json.loads((EXP / 'modelos_selecionados.json').read_text(encoding='utf-8'))['models']
    return dev, ids_teste, cong


def tarefa(X, y, itr, iva, fold, k, f, nome, cfg):
    """Ajusta um modelo numa subamostra estratificada do treino e avalia no fold."""
    if f < 1.0:
        itr, _ = train_test_split(itr, train_size=f, stratify=y[itr], random_state=1000 * fold + k)
    yt, yv = y[itr], y[iva]
    with threadpool_limits(limits=1):
        if nome == 'dummy':
            m = DummyClassifier(strategy='prior')
        elif nome.startswith('knn_'):
            m = Pipeline([('preparo', preprocessor(nome[4:])), ('modelo', KNeighborsClassifier(n_neighbors=1))])
        else:
            m = pipeline(nome, cfg['params'], SEED_FIT, None, cfg['representation'])
        m.fit(X.iloc[itr], yt)
        pv = m.predict_proba(X.iloc[iva])[:, 1]
        r = dict(fold=fold, fracao=f, modelo=nome, n_treino=len(itr),
                 erro_val=float(np.mean((pv >= 0.5) != (yv == 1))))
        if nome.startswith('knn_'):
            d, _ = m.named_steps['modelo'].kneighbors(m.named_steps['preparo'].transform(X.iloc[iva]))
            r['share_dist0'] = float(np.mean(d[:, 0] == 0))
        elif nome != 'dummy':
            r['ap_val'] = float(average_precision_score(yv, pv))
            r['ap_treino'] = float(average_precision_score(yt, m.predict_proba(X.iloc[itr])[:, 1]))
    return r


def potencia(x, y, sinal, xs):
    """Ajusta a + sinal*b*x^-c em escala x/xs; devolve (a, b, c) com b na escala original."""
    f = lambda t, a, b, c: a + sinal * b * t ** (-c)
    melhor, sse = None, np.inf
    for c0 in (0.3, 1.0, 2.0):
        try:
            p, _ = curve_fit(f, x / xs, y, p0=[y[-1], 0.1, c0], bounds=([0, 1e-9, 1e-6], [1, 10, 3]), maxfev=20000)
        except Exception:
            continue
        s = np.sum((f(x / xs, *p) - y) ** 2)
        if s < sse:
            melhor, sse = p, s
    if melhor is None:
        return None
    a, b, c = melhor
    return a, b * xs ** c, c


def prever(p, n, sinal):
    return p[0] + sinal * p[1] * n ** (-p[2])


def ic(v):
    v = np.asarray(v, float)
    return (np.nanpercentile(v, 2.5), np.nanpercentile(v, 97.5)) if len(v) else (np.nan, np.nan)


def ajustar_curva(M, n, sinal, rng, nboot):
    """M: folds x frações (métrica). Ajuste na média + bootstrap dos folds."""
    xs = n[-1]
    p = potencia(n, M.mean(0), sinal, xs)
    rmse = float(np.sqrt(np.mean((prever(p, n, sinal) - M.mean(0)) ** 2)))
    asint, ok = [], 0
    for _ in range(nboot):
        q = potencia(n, M[rng.integers(0, len(M), len(M))].mean(0), sinal, xs)
        if q is not None:
            asint.append(q[0]); ok += 1
    return p, rmse, np.array(asint), ok


def cover_hart(R):
    R = np.asarray(R, float)
    return (1 - np.sqrt(np.clip(1 - 2 * R, 0, None))) / 2, R


def br(x, d=0):
    return f'{x:,.{d}f}'.replace(',', 'X').replace('.', ',').replace('X', '.')


def figura(pasta, n, curvas, ajustes):
    plt.rcParams.update({'font.family': 'STIXGeneral', 'mathtext.fontset': 'stix', 'font.size': 8,
                         'xtick.labelsize': 7, 'ytick.labelsize': 7, 'pdf.fonttype': 42,
                         'axes.spines.top': False, 'axes.spines.right': False, 'axes.linewidth': 0.6})
    fig, ax = plt.subplots(figsize=(3.45, 1.7))
    xx = np.linspace(n[0], 2 * n[-1], 200)
    for m in MODELOS:
        M = curvas[m]
        ax.fill_between(n, M.mean(0) - M.std(0, ddof=1), M.mean(0) + M.std(0, ddof=1), color=COR[m], alpha=0.18, lw=0)
        ax.plot(n, M.mean(0), 'o', color=COR[m], ms=2.2, label={'logistica': 'Logística', 'floresta': 'Floresta', 'boosting': 'Boosting'}[m])
        p = ajustes[m]
        ax.plot(xx, prever(p, xx, -1), '-', color=COR[m], lw=0.8)
        ax.axhline(p[0], color=COR[m], ls='--', lw=0.6)
    ax.set_xlabel('Registros de treino'); ax.set_ylabel('AP (validação)')
    ax.set_xlim(0, 2.05 * n[-1])
    ax.xaxis.set_major_formatter(FuncFormatter(lambda v, _: br(v)))
    ax.yaxis.set_major_formatter(FuncFormatter(lambda v, _: br(v, 2)))
    ax.tick_params(width=0.6, length=2.5)
    ax.grid(color='#e3e3e3', lw=0.4); ax.set_axisbelow(True)
    ax.legend(loc='lower right', frameon=False, fontsize=7, handlelength=1.2, ncol=1)
    fig.savefig(pasta / 'fig_teto.pdf', bbox_inches='tight', pad_inches=0.02)
    fig.savefig(pasta / 'fig_teto.png', dpi=300, bbox_inches='tight', pad_inches=0.02)
    plt.close(fig)


def main():
    t0 = time.time()
    ap = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    ap.add_argument('--saida', type=Path, default=ROOT / 'resultados/a2' / 'teto_desempenho')
    ap.add_argument('--jobs', type=int, default=4)
    ap.add_argument('--bootstrap', type=int, default=2000)
    a = ap.parse_args()
    a.saida.mkdir(parents=True, exist_ok=True)

    dev, ids_teste, cong = carregar()
    X, y = input_frame(dev), dev.y.to_numpy()
    folds = []
    for s in CV_SEEDS:
        folds += list(StratifiedKFold(5, shuffle=True, random_state=s).split(X, y))
    assert all(not ids_teste & set(dev.ID.iloc[iv]) for _, iv in folds)
    print(f'desenvolvimento: {len(dev)} linhas, prevalência {y.mean():.4f}, {len(folds)} folds', flush=True)

    modelos = {m: cong[m] for m in MODELOS}
    modelos.update({f'knn_{r}': None for r in REPRESENTATIONS})
    modelos['dummy'] = None
    tarefas = [(i, k, f, nome) for i in range(len(folds)) for k, f in enumerate(FRACOES) for nome in modelos
               if not (nome == 'dummy' and f < 1.0)]
    res = Parallel(n_jobs=a.jobs, verbose=0)(
        delayed(tarefa)(X, y, folds[i][0], folds[i][1], i, k, f, nome, modelos[nome]) for i, k, f, nome in tarefas)
    cur = pd.DataFrame(res).sort_values(['modelo', 'fold', 'fracao']).reset_index(drop=True)
    cur.to_csv(a.saida / 'curvas_aprendizado.csv', index=False)
    print(f'ajustes concluídos em {time.time() - t0:.0f}s', flush=True)

    def matriz(nome, col):
        d = cur[cur.modelo == nome].pivot(index='fold', columns='fracao', values=col)
        return d.to_numpy()
    n = cur[cur.modelo == 'logistica'].groupby('fracao').n_treino.mean().to_numpy()
    n_full = n[-1]
    rng = np.random.default_rng(SEED_BOOT)

    linhas, ajustes_ap, curvas_ap, boot_knn, resumo = [], {}, {}, {}, {'n_full': float(n_full)}
    for m in MODELOS:
        for met, col, sinal in [('AP', 'ap_val', -1), ('erro', 'erro_val', 1)]:
            M = matriz(m, col)
            p, rmse, asint, ok = ajustar_curva(M, n, sinal, rng, a.bootstrap)
            lo, hi = ic(asint)
            linhas.append(dict(model=m, metric=met, a=p[0], a_lo=lo, a_hi=hi, b=p[1], c=p[2], rmse=rmse,
                               pred_full=prever(p, n_full, sinal), pred_2x=prever(p, 2 * n_full, sinal),
                               pred_10x=prever(p, 10 * n_full, sinal), n_bootstrap_ok=ok))
            if met == 'AP':
                ajustes_ap[m], curvas_ap[m] = p, M
    ch = []
    for r in REPRESENTATIONS:
        nome = f'knn_{r}'
        M = matriz(nome, 'erro_val')
        p, rmse, asint, ok = ajustar_curva(M, n, 1, rng, a.bootstrap)
        lo, hi = ic(asint)
        linhas.append(dict(model=nome, metric='erro', a=p[0], a_lo=lo, a_hi=hi, b=p[1], c=p[2], rmse=rmse,
                           pred_full=prever(p, n_full, 1), pred_2x=prever(p, 2 * n_full, 1),
                           pred_10x=prever(p, 10 * n_full, 1), n_bootstrap_ok=ok))
        # limites de Cover-Hart: R_inf (principal) e R_full (sensibilidade)
        bl, bu = cover_hart(asint)
        rf = M[:, -1]
        rfb = np.array([rf[rng.integers(0, len(rf), len(rf))].mean() for _ in range(a.bootstrap)])
        fl, fu = cover_hart(rfb)
        l0, u0 = cover_hart(p[0]); l1, u1 = cover_hart(rf.mean())
        # duplicatas com rótulos conflitantes (pré-processador ajustado no desenvolvimento, sem rótulos)
        Xp = preprocessor(r).fit_transform(X)
        _, inv = np.unique(Xp, axis=0, return_inverse=True)
        inv = inv.ravel()
        n0 = np.bincount(inv, weights=(y == 0)); n1 = np.bincount(inv, weights=(y == 1))
        tam = n0 + n1
        conf = (n0 > 0) & (n1 > 0)
        d0 = cur[(cur.modelo == nome) & (cur.fracao == 1.0)].share_dist0
        ch.append(dict(
            representation=r, R_full=rf.mean(), R_full_lo=ic(rfb)[0], R_full_hi=ic(rfb)[1],
            R_inf=p[0], R_inf_lo=lo, R_inf_hi=hi,
            bayes_lower_inf=l0, bayes_lower_inf_lo=ic(bl)[0], bayes_lower_inf_hi=ic(bl)[1], bayes_upper_inf=u0,
            bayes_upper_inf_lo=lo, bayes_upper_inf_hi=hi,
            bayes_lower_full=l1, bayes_lower_full_lo=ic(fl)[0], bayes_lower_full_hi=ic(fl)[1], bayes_upper_full=u1,
            bayes_upper_full_lo=ic(rfb)[0], bayes_upper_full_hi=ic(rfb)[1],
            n_vetores_unicos=len(tam), n_linhas_em_duplicatas=int(tam[tam > 1].sum()),
            n_grupos_conflitantes=int(conf.sum()), n_linhas_em_conflito=int(tam[conf].sum()),
            erro_minimo_duplicatas=float(np.minimum(n0, n1).sum() / len(y)),
            share_dist0=float(d0.mean()), n_bootstrap_ok=ok))
    pd.DataFrame(linhas).to_csv(a.saida / 'ajustes_potencia.csv', index=False)
    pd.DataFrame(ch).to_csv(a.saida / 'cover_hart.csv', index=False)

    full = cur[cur.fracao == 1.0].groupby('modelo').erro_val.mean()
    resumo.update(erro_threshold05_full={k: float(v) for k, v in full.items()},
                  prevalencia=float(y.mean()), n_folds=len(folds), n_dev=len(dev),
                  teste_usado=False, tempo_s=time.time() - t0,
                  bootstrap_falhas={f"{l['model']}/{l['metric']}": a.bootstrap - l['n_bootstrap_ok'] for l in linhas})
    (a.saida / 'resumo.json').write_text(json.dumps(resumo, indent=2, ensure_ascii=False), encoding='utf-8')
    figura(a.saida, n, curvas_ap, ajustes_ap)
    print(pd.DataFrame(linhas).round(4).to_string()); print(pd.DataFrame(ch).round(4).T.to_string())
    print(json.dumps(resumo, indent=1)); print(f'tempo {time.time() - t0:.0f}s')


if __name__ == '__main__':
    main()
