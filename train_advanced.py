"""Advanced training: hyperparameter-tuned models + voting/stacking ensembles.

Goal: beat the 97.42% Random Forest baseline.
- Same UCI data + same 80/20 split (stratify, seed 42) for fair comparison.
- RandomizedSearchCV tuning for RF / ExtraTrees / HistGradientBoosting / XGBoost.
- Soft Voting + Stacking ensembles on top.
- Winner (by F1) becomes models/phishing_model.pkl (old one backed up).
- metrics.json is merged so the website's Model Arena keeps old entries + shows new ones.
"""
import json
import os
import shutil

import joblib
import numpy as np
import pandas as pd

from sklearn.ensemble import (
    ExtraTreesClassifier,
    HistGradientBoostingClassifier,
    RandomForestClassifier,
    StackingClassifier,
    VotingClassifier,
)
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (
    accuracy_score,
    confusion_matrix,
    f1_score,
    precision_score,
    recall_score,
)
from sklearn.model_selection import RandomizedSearchCV, StratifiedKFold, train_test_split

from features import FEATURE_NAMES
from train import load_uci, synthetic_fallback  # reuse data loading

MODEL_DIR = os.path.join(os.path.dirname(__file__), "models")
N_JOBS = -1
SEED = 42


def scores(yt, yp):
    return {
        "accuracy": round(float(accuracy_score(yt, yp)), 4),
        "precision": round(float(precision_score(yt, yp, zero_division=0)), 4),
        "recall": round(float(recall_score(yt, yp, zero_division=0)), 4),
        "f1": round(float(f1_score(yt, yp, zero_division=0)), 4),
        "confusion_matrix": confusion_matrix(yt, yp).tolist(),
    }


def tune(name, estimator, grid, X_train, y_train, n_iter=12):
    print(f"\n[TUNE] {name} ...", flush=True)
    cv = StratifiedKFold(n_splits=3, shuffle=True, random_state=SEED)
    search = RandomizedSearchCV(
        estimator, grid, n_iter=n_iter, scoring="f1", cv=cv,
        n_jobs=N_JOBS, random_state=SEED, verbose=0,
    )
    search.fit(X_train, y_train)
    print(f"  best CV f1={search.best_score_:.4f} params={search.best_params_}", flush=True)
    return search.best_estimator_, round(float(search.best_score_), 4)


def main():
    os.makedirs(MODEL_DIR, exist_ok=True)
    try:
        df = load_uci()
        print("Dataset shape:", df.shape, flush=True)
    except Exception as e:
        print("Download/load failed:", e, flush=True)
        df = synthetic_fallback()

    colmap = {c: c.strip().strip("'\"") for c in df.columns}
    df = df.rename(columns=colmap)
    target = "Result" if "Result" in df.columns else df.columns[-1]
    X = df[[c for c in FEATURE_NAMES if c in df.columns]].copy()
    for c in FEATURE_NAMES:
        if c not in X.columns:
            X[c] = 0
    X = X[FEATURE_NAMES].apply(pd.to_numeric, errors="coerce").fillna(0).astype(int)
    y_raw = pd.to_numeric(df[target], errors="coerce").fillna(1).astype(int)
    y_raw = y_raw.apply(lambda v: -1 if v == -1 else 1)
    # unify labels: 1 = phishing, 0 = legit (app.py already handles both conventions)
    y = (y_raw == -1).astype(int)
    print("Class balance (1=phish):", pd.Series(y).value_counts().to_dict(), flush=True)

    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=SEED, stratify=y
    )

    from xgboost import XGBClassifier  # required; repo already uses it

    tuned, cv_scores = {}, {}

    rf, s = tune("Random Forest", RandomForestClassifier(random_state=SEED, n_jobs=N_JOBS), {
        "n_estimators": [300, 500, 800],
        "max_depth": [None, 20, 30, 40],
        "min_samples_split": [2, 4, 6],
        "min_samples_leaf": [1, 2],
        "max_features": ["sqrt", 0.7, None],
        "class_weight": [None, "balanced_subsample"],
    }, X_train, y_train)
    tuned["Random Forest (tuned)"] = rf; cv_scores["Random Forest (tuned)"] = s

    et, s = tune("ExtraTrees", ExtraTreesClassifier(random_state=SEED, n_jobs=N_JOBS), {
        "n_estimators": [400, 700, 1000],
        "max_depth": [None, 25, 40],
        "min_samples_split": [2, 4],
        "min_samples_leaf": [1, 2],
        "max_features": ["sqrt", 0.7, None],
        "class_weight": [None, "balanced_subsample"],
    }, X_train, y_train)
    tuned["ExtraTrees (tuned)"] = et; cv_scores["ExtraTrees (tuned)"] = s

    hgb, s = tune("HistGradientBoosting", HistGradientBoostingClassifier(random_state=SEED), {
        "max_iter": [300, 500, 800],
        "max_depth": [None, 12, 20],
        "learning_rate": [0.03, 0.06, 0.1],
        "max_leaf_nodes": [31, 63, 127],
        "l2_regularization": [0.0, 1.0, 5.0],
    }, X_train, y_train)
    tuned["HistGradBoost (tuned)"] = hgb; cv_scores["HistGradBoost (tuned)"] = s

    xgb, s = tune("XGBoost", XGBClassifier(eval_metric="logloss", random_state=SEED, n_jobs=N_JOBS), {
        "n_estimators": [300, 600, 900],
        "max_depth": [4, 6, 8, 10],
        "learning_rate": [0.03, 0.05, 0.08, 0.12],
        "subsample": [0.8, 0.9, 1.0],
        "colsample_bytree": [0.7, 0.85, 1.0],
        "min_child_weight": [1, 3, 5],
        "reg_lambda": [0.5, 1.0, 2.0],
    }, X_train, y_train)
    tuned["XGBoost (tuned)"] = xgb; cv_scores["XGBoost (tuned)"] = s

    # ---- ensembles of the tuned base models ----
    print("\n[ENSEMBLE] fitting Voting + Stacking ...", flush=True)
    estimators = [(k, m) for k, m in tuned.items()]
    voting = VotingClassifier(estimators=estimators, voting="soft", n_jobs=N_JOBS)
    voting.fit(X_train, y_train)
    tuned["Voting Ensemble"] = voting

    stacking = StackingClassifier(
        estimators=estimators,
        final_estimator=LogisticRegression(max_iter=2000, C=1.0),
        cv=StratifiedKFold(n_splits=5, shuffle=True, random_state=SEED),
        n_jobs=N_JOBS,
    )
    stacking.fit(X_train, y_train)
    tuned["Stacking Ensemble"] = stacking

    # ---- holdout evaluation ----
    print("\n[EVAL] holdout test set:", flush=True)
    new_metrics = {}
    for name, model in tuned.items():
        yp = model.predict(X_test)
        m = scores(y_test, yp)
        if name in cv_scores:
            m["cv_f1_mean"] = cv_scores[name]
        new_metrics[name] = m
        print(f"  {name}: acc={m['accuracy']} prec={m['precision']} rec={m['recall']} f1={m['f1']}", flush=True)

    # ---- merge with previous metrics.json ----
    metrics_path = os.path.join(MODEL_DIR, "metrics.json")
    with open(metrics_path) as f:
        old = json.load(f)
    merged_models = dict(old.get("models", {}))
    merged_models.update(new_metrics)
    best_name = max(merged_models, key=lambda k: merged_models[k]["f1"])
    merged = {"models": merged_models, "best_model": best_name,
              "n_train": len(X_train), "n_test": len(X_test)}
    print(f"\nOld best: {old.get('best_model')} | New best overall: {best_name}", flush=True)

    # ---- persist ----
    main_pkl = os.path.join(MODEL_DIR, "phishing_model.pkl")
    if os.path.exists(main_pkl):
        shutil.copy2(main_pkl, os.path.join(MODEL_DIR, "phishing_model_backup.pkl"))
        print("Backed up previous model -> phishing_model_backup.pkl", flush=True)
    if best_name in tuned:
        joblib.dump(tuned[best_name], main_pkl)
        print(f"Saved new champion '{best_name}' -> phishing_model.pkl", flush=True)
    else:
        print(f"Champion '{best_name}' is a previous model; phishing_model.pkl left as-is.", flush=True)
    for name, model in tuned.items():
        safe = name.lower().replace(" ", "_").replace("(", "").replace(")", "")
        joblib.dump(model, os.path.join(MODEL_DIR, f"{safe}.pkl"))

    with open(metrics_path, "w") as f:
        json.dump(merged, f, indent=2)

    # feature importance from the best tree-based tuned model available
    for cand in (best_name, "XGBoost (tuned)", "Random Forest (tuned)", "ExtraTrees (tuned)", "HistGradBoost (tuned)"):
        if cand in tuned and hasattr(tuned[cand], "feature_importances_"):
            imp = sorted(zip(FEATURE_NAMES, map(float, tuned[cand].feature_importances_)),
                         key=lambda x: x[1], reverse=True)
            with open(os.path.join(MODEL_DIR, "feature_importance.json"), "w") as f:
                json.dump([{"feature": k, "importance": round(v, 4)} for k, v in imp], f, indent=2)
            print(f"Feature importance updated from {cand}.", flush=True)
            break
    print("Done.", flush=True)


if __name__ == "__main__":
    main()
