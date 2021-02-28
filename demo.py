#    Copyright 2021 Boostgang.

from __future__ import print_function, division

import sys

import numpy as np

from sklearn import preprocessing, metrics
from sklearn.ensemble import AdaBoostClassifier
from sklearn.datasets import load_breast_cancer, fetch_openml
from sklearn.impute import SimpleImputer
from dwave.system.samplers import DWaveSampler
from sklearn.model_selection import train_test_split
from dwave.system.composites import EmbeddingComposite

from qboost import WeakClassifiers, QBoostClassifier


def metric(y, y_pred):

    return metrics.accuracy_score(y, y_pred)


def print_accuracy(y_train, y_train_pred, y_test, y_test_pred):
    """Print information about accuracy."""

    print('    Accuracy on training set: {:5.2f}'.format(metric(y_train, y_train_pred)))
    print('    Accuracy on test set:     {:5.2f}'.format(metric(y_test, y_test_pred)))


def train_models(X_train, y_train, X_test, y_test, lmd, verbose=False):
    """
    Train a series of 4 boosted classification models.
    
    Args:
        X_train (array):
            2D array of features for training.
        y_train (array):
            1D array of labels for training.
        X_test (array):
            2D array of features for testing.
        y_test (array):
            1D array of labels for testing.
        lam (float):
            lambda parameter to control regularization term.
        verbose (bool):
            If True, print weak classifier weights.
    """
    NUM_READS = 3000
    NUM_WEAK_CLASSIFIERS = 35
    # lmd = 0.5
    TREE_DEPTH = 3

    # define sampler
    dwave_sampler = DWaveSampler()
    emb_sampler = EmbeddingComposite(dwave_sampler)

    N_train = len(X_train)
    N_test = len(X_test)

    print('Size of training set:', N_train)
    print('Size of test set:    ', N_test)
    print('Number of weak classifiers:', NUM_WEAK_CLASSIFIERS)
    print('Tree depth:', TREE_DEPTH)


    # input: dataset X and labels y (in {+1, -1}

    # Preprocessing data
    # imputer = SimpleImputer()
    scaler = preprocessing.StandardScaler()     # standardize features
    normalizer = preprocessing.Normalizer()     # normalize samples

    # X = imputer.fit_transform(X)
    X_train = scaler.fit_transform(X_train)
    X_train = normalizer.fit_transform(X_train)

    # X_test = imputer.fit_transform(X_test)
    X_test = scaler.fit_transform(X_test)
    X_test = normalizer.fit_transform(X_test)


    # ===============================================
    print('\nAdaboost:')

    clf = AdaBoostClassifier(n_estimators=NUM_WEAK_CLASSIFIERS)

    # scores = cross_val_score(clf, X, y, cv=5, scoring='accuracy')
    clf.fit(X_train, y_train)

    hypotheses_ada = clf.estimators_
    # clf.estimator_weights_ = np.random.uniform(0,1,size=NUM_WEAK_CLASSIFIERS)
    y_train_pred = clf.predict(X_train)
    y_test_pred = clf.predict(X_test)

    print_accuracy(y_train, y_train_pred, y_test, y_test_pred)


    # ===============================================
    print('\nDecision tree:')

    clf2 = WeakClassifiers(n_estimators=NUM_WEAK_CLASSIFIERS, max_depth=TREE_DEPTH)
    clf2.fit(X_train, y_train)

    y_train_pred2 = clf2.predict(X_train)
    y_test_pred2 = clf2.predict(X_test)

    if verbose:
        print('weights:\n', clf2.estimator_weights)

    print_accuracy(y_train, y_train_pred2, y_test, y_test_pred2)


    # ===============================================
    print('\nQBoost:')

    DW_PARAMS = {'num_reads': NUM_READS,
                 'auto_scale': True,
                 # "answer_mode": "histogram",
                 'num_spin_reversal_transforms': 10,
                 # 'annealing_time': 10,
                 }

    clf3 = QBoostClassifier(n_estimators=NUM_WEAK_CLASSIFIERS, max_depth=TREE_DEPTH)
    clf3.fit(X_train, y_train, emb_sampler, lmd=lmd, **DW_PARAMS)

    y_train_dw = clf3.predict(X_train)
    y_test_dw = clf3.predict(X_test)

    if verbose:
        print('weights\n', clf3.estimator_weights)

    print_accuracy(y_train, y_train_dw, y_test, y_test_dw)


if __name__ == '__main__':

    # Major changes
    print('Client Model Simulation Crashes Data Set:')

    # Note: as_frame default changed between scikit-learn 0.23 and 0.24
    X,y = fetch_openml('creditcard', version=1, return_X_y=True)

    # train on a random 2/3 and test on the remaining 1/3

    X_train, X_test, y_train, y_test = train_test_split (X,y, test_size = 0.3, random_state = 0)
    # Note: clim['target'] is an array of string numbers, hence the comparison with '4'
    y_train = 2*(y_train == '1') - 1
    y_test = 2*(y_test == '1') - 1

    print(y_train)
    train_models(X_train, y_train, X_test, y_test, 1.0)

