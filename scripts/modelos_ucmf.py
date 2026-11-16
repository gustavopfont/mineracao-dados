"""Famílias e candidatos pré-especificados; nenhuma seleção usa o teste."""
from sklearn.dummy import DummyClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.tree import DecisionTreeClassifier
from sklearn.ensemble import RandomForestClassifier, HistGradientBoostingClassifier
from sklearn.neighbors import KNeighborsClassifier
from sklearn.model_selection import ParameterGrid
from sklearn.pipeline import Pipeline
from joblib import Memory
import numpy as np
from representacoes_ucmf import preprocessor

MODEL_ORDER = ['logistica','arvore','knn','floresta','boosting']
ALL_MODELS = ['dummy']+MODEL_ORDER
SPACES = {
    'logistica': {'C':[.001,.01,.1,1,10,100], 'class_weight':[None,'balanced']},
    'arvore': {'max_depth':[3,6,12,None], 'min_samples_leaf':[1,5,20], 'class_weight':[None,'balanced']},
    'floresta': {'max_depth':[8,16,None], 'min_samples_leaf':[1,3,10],
                 'max_features':['sqrt',.5,1.], 'class_weight':[None,'balanced_subsample']},
    'boosting': {'max_iter':[100,200], 'learning_rate':[.03,.1], 'max_leaf_nodes':[7,15,31], 'l2_regularization':[0,1,10]},
    'knn': {'n_neighbors':[5,11,21,41,81], 'weights':['uniform','distance'], 'p':[1,2]},
}


def candidates(seed=42, count=4):
    result = {'dummy':[{}]}
    for i,name in enumerate(MODEL_ORDER):
        grid = list(ParameterGrid(SPACES[name]))
        if not isinstance(count,int) or isinstance(count,bool) or not 1 <= count <= len(grid):
            raise ValueError('Quantidade de candidatos deve ser inteira e caber na grade, sem reposição')
        indices = (range(len(grid)) if count==len(grid) else
                   np.random.default_rng(seed+i).choice(len(grid),count,replace=False))
        result[name] = [grid[int(j)] for j in indices]
    return result


def pipeline(name, parameters, seed, cache=None, representation='continua'):
    constructors = {
        'dummy':lambda:DummyClassifier(strategy='prior'),
        'logistica':lambda:LogisticRegression(solver='lbfgs',max_iter=3000,random_state=seed),
        'arvore':lambda:DecisionTreeClassifier(criterion='gini',random_state=seed),
        'floresta':lambda:RandomForestClassifier(n_estimators=200,n_jobs=1,random_state=seed),
        'boosting':lambda:HistGradientBoostingClassifier(early_stopping=False,random_state=seed),
        'knn':lambda:KNeighborsClassifier(n_jobs=1),
    }
    estimator = constructors[name]().set_params(**parameters)
    return Pipeline([('preparo',preprocessor(representation)),('modelo',estimator)],
                    memory=Memory(str(cache),verbose=0) if cache else None)
