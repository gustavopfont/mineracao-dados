"""Métricas/limiar: scikit-learn; testes: Dietterich 1998, Alpaydin 1999, Holm 1979.

As fontes e hipóteses da v3 constam no relatório de experimentos publicado.
"""
import numpy as np
from scipy.stats import binomtest, f, t
from sklearn.metrics import (average_precision_score, roc_auc_score,
                             confusion_matrix, brier_score_loss)


def validate_scores(y, p):
    y, p = np.asarray(y, dtype=int), np.asarray(p, dtype=float)
    if set(y) != {0, 1} or y.shape != p.shape or not np.isfinite(p).all() or ((p < 0) | (p > 1)).any():
        raise ValueError('Exige ambas as classes e probabilidades finitas em [0,1]')
    return y, p


def choose_threshold(y, p, minimum_specificity=.8):
    y, p = validate_scores(y, p)
    order = np.argsort(-p, kind='stable')
    sorted_p = p[order]
    ends = np.r_[np.flatnonzero(np.diff(sorted_p)), len(p)-1]
    tp = np.r_[0, np.cumsum(y[order])[ends]]
    fp = np.r_[0, (ends+1)-tp[1:]]
    thresholds = np.r_[np.nextafter(sorted_p[0], np.inf), sorted_p[ends]]
    recall = tp/y.sum()
    specificity = 1-fp/(len(y)-y.sum())
    precision = np.divide(tp, tp+fp, out=np.zeros(len(tp), dtype=float), where=(tp+fp)>0)
    eligible = np.flatnonzero(specificity >= minimum_specificity)
    ranking = np.lexsort((thresholds[eligible], specificity[eligible], precision[eligible], recall[eligible]))
    winner = eligible[ranking[-1]]
    return dict(threshold=float(thresholds[winner]), recall=float(recall[winner]),
                specificity=float(specificity[winner]), precision=float(precision[winner]))


def metrics(y, p, threshold=.5, prediction=None):
    y, p = validate_scores(y, p)
    prediction = (p >= threshold).astype(int) if prediction is None else np.asarray(prediction, dtype=int)
    tn, fp, fn, tp = confusion_matrix(y, prediction, labels=[0, 1]).ravel()
    recall, specificity = tp/(tp+fn), tn/(tn+fp)
    precision = tp/(tp+fp) if tp+fp else 0.
    f1 = 2*tp/(2*tp+fp+fn) if 2*tp+fp+fn else 0.
    f2 = 5*tp/(5*tp+4*fn+fp) if 5*tp+4*fn+fp else 0.
    return dict(n=len(y), tp=int(tp), tn=int(tn), fp=int(fp), fn=int(fn),
                accuracy=float((tp+tn)/len(y)), recall=float(recall), specificity=float(specificity),
                precision=float(precision), f1=float(f1), f2=float(f2),
                balanced_accuracy=float((recall+specificity)/2),
                roc_auc=float(roc_auc_score(y,p)), ap=float(average_precision_score(y,p)),
                brier=float(brier_score_loss(y,p)), prevalence=float(y.mean()),
                error=float((fp+fn)/len(y)))


def five_by_two(differences):
    d = np.asarray(differences, dtype=float)
    if d.shape != (5,2) or not np.isfinite(d).all():
        raise ValueError('O teste exige diferenças pareadas 5×2 completas')
    variance_sum = float(((d-d.mean(axis=1, keepdims=True))**2).sum())
    result = dict(mean_difference=float(d.mean()), variance_sum=variance_sum)
    if variance_sum == 0:
        return dict(**result, f_stat=None, f_p=None, t_stat=None, t_p=None, status='variância nula; inferência indefinida')
    statistic_f = float((d*d).sum()/(2*variance_sum))
    statistic_t = float(d[0,0]/np.sqrt(variance_sum/5))
    return dict(**result, f_stat=statistic_f, f_p=float(f.sf(statistic_f,10,5)),
                t_stat=statistic_t, t_p=float(2*t.sf(abs(statistic_t),5)), status='aproximado')


def holm(pvalues):
    """Valores indefinidos não são rejeitados; m inclui a família pré-especificada."""
    adjusted = [None]*len(pvalues)
    order = sorted([i for i,p in enumerate(pvalues) if p is not None], key=lambda i:pvalues[i])
    previous = 0.
    for rank, i in enumerate(order):
        previous = max(previous, (len(pvalues)-rank)*pvalues[i])
        adjusted[i] = min(1.,previous)
    return adjusted


def mcnemar_exact(y, a, b, target):
    mask = np.asarray(y) == target
    ca = np.asarray(a)[mask] == target
    cb = np.asarray(b)[mask] == target
    a_only, b_only = int((ca & ~cb).sum()), int((~ca & cb).sum())
    discordant = a_only+b_only
    return dict(target=target, n=int(mask.sum()), winner_only_correct=a_only, logistic_only_correct=b_only,
                p=float(binomtest(a_only,discordant,.5).pvalue) if discordant else 1.)
