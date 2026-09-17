"""Train phishing models on UCI Phishing Websites dataset.
- Downloads ARFF, else falls back to synthetic data (offline mode).
- Trains Logistic Regression, Random Forest, XGBoost/GradientBoosting.
- Saves models/phishing_model.pkl (best), models/metrics.json, models/feature_names.json
"""
import json, os, urllib.request, tempfile
import numpy as np
import pandas as pd

from sklearn.model_selection import train_test_split
from sklearn.linear_model import LogisticRegression
from sklearn.ensemble import RandomForestClassifier, GradientBoostingClassifier
from sklearn.metrics import accuracy_score, precision_score, recall_score, f1_score, confusion_matrix
import joblib

from features import FEATURE_NAMES

UCI_URL = "https://archive.ics.uci.edu/ml/machine-learning-databases/00327/Training%20Dataset.arff"
MODEL_DIR = os.path.join(os.path.dirname(__file__), "models")
DATA_DIR = os.path.join(os.path.dirname(__file__), "data")


def load_uci():
    os.makedirs(DATA_DIR, exist_ok=True)
    local = os.path.join(DATA_DIR, "Training Dataset.arff")
    if not os.path.exists(local):
        print(f"Downloading UCI dataset ...")
        urllib.request.urlretrieve(UCI_URL, local)
        print("Downloaded ->", local)
    try:
        from scipy.io import arff
        data, meta = arff.loadarff(local)
        df = pd.DataFrame(data)
        # Result column is bytes b'1'/b'-1'
        for c in df.columns:
            if df[c].dtype == object:
                try:
                    df[c] = df[c].str.decode('utf-8')
                except Exception:
                    pass
        df = df.apply(pd.to_numeric, errors='coerce')
        return df
    except Exception as e:
        print("scipy ARFF parse failed, manual parse:", e)
        rows, cols = [], []
        with open(local, 'r', errors='ignore') as f:
            in_data = False
            for line in f:
                line = line.strip()
                if not line or line.startswith('%'):
                    continue
                if line.upper().startswith('@ATTRIBUTE'):
                    parts = line.split()
                    cols.append(parts[1].strip("'\""))
                elif line.upper().startswith('@DATA'):
                    in_data = True
                elif in_data:
                    rows.append([float(x.strip()) for x in line.split(',')])
        return pd.DataFrame(rows, columns=cols)


def synthetic_fallback(n=4000, seed=42):
    print("Using SYNTHETIC fallback dataset (offline mode).")
    rng = np.random.default_rng(seed)
    X = rng.choice([-1, 0, 1], size=(n, len(FEATURE_NAMES)), p=[0.35, 0.15, 0.5])
    # phishing likelihood rises with # of -1s
    score = (X == -1).sum(axis=1) + rng.normal(0, 1.5, n)
    y = np.where(score > 7, -1, 1)  # -1 = phishing, 1 = legit (UCI convention)
    df = pd.DataFrame(X, columns=FEATURE_NAMES)
    df['Result'] = y
    return df


def evaluate(name, model, X_test, y_test):
    pred = model.predict(X_test)
    proba = model.predict_proba(X_test) if hasattr(model, 'predict_proba') else None
    # map -1/1 -> 0/1 for sklearn metrics (phishing=1 positive)
    yt = (y_test == -1).astype(int)
    yp = (pred == -1).astype(int)
    return {
        'accuracy': round(float(accuracy_score(yt, yp)), 4),
        'precision': round(float(precision_score(yt, yp, zero_division=0)), 4),
        'recall': round(float(recall_score(yt, yp, zero_division=0)), 4),
        'f1': round(float(f1_score(yt, yp, zero_division=0)), 4),
        'confusion_matrix': confusion_matrix(yt, yp).tolist(),  # [[TN, FP],[FN, TP]]
    }


def main():
    os.makedirs(MODEL_DIR, exist_ok=True)
    try:
        df = load_uci()
        print("Dataset shape:", df.shape)
    except Exception as e:
        print("Download/load failed:", e)
        df = synthetic_fallback()

    target = 'Result' if 'Result' in df.columns else df.columns[-1]
    # normalize column names (ARFF may have different casing)
    colmap = {c: c.strip().strip("'\"") for c in df.columns}
    df = df.rename(columns=colmap)
    if target not in df.columns:
        target = df.columns[-1]
    X = df[[c for c in FEATURE_NAMES if c in df.columns]].copy()
    # ensure all 30 present
    for c in FEATURE_NAMES:
        if c not in X.columns:
            X[c] = 0
    X = X[FEATURE_NAMES].apply(pd.to_numeric, errors='coerce').fillna(0).astype(int)
    y = pd.to_numeric(df[target], errors='coerce').fillna(1).astype(int)
    y = y.apply(lambda v: -1 if v == -1 else 1)

    print("Class balance:", y.value_counts().to_dict())
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=42, stratify=y)

    candidates = {
        'Logistic Regression': LogisticRegression(max_iter=1000),
        'Random Forest': RandomForestClassifier(n_estimators=200, random_state=42, n_jobs=-1),
    }
    try:
        from xgboost import XGBClassifier
        candidates['XGBoost'] = XGBClassifier(n_estimators=200, max_depth=6,
                                              learning_rate=0.08, subsample=0.9,
                                              colsample_bytree=0.9, eval_metric='logloss',
                                              random_state=42, n_jobs=-1)
        print("XGBoost available.")
    except Exception as e:
        print("XGBoost not available, using GradientBoosting:", e)
        candidates['Gradient Boosting'] = GradientBoostingClassifier(random_state=42)

    metrics, trained = {}, {}
    importances = {}
    for name, model in candidates.items():
        print(f"Training {name} ...")
        # XGBoost needs 0/1 labels
        if 'XGBoost' in name:
            yt_train = (y_train == -1).astype(int)
            yt_test = (y_test == -1).astype(int)
            model.fit(X_train, yt_train)
            pred01 = model.predict(X_test)
            pred = np.where(pred01 == 1, -1, 1)
            yt = yt_test; yp = pred01
            m = {
                'accuracy': round(float(accuracy_score(yt, yp)), 4),
                'precision': round(float(precision_score(yt, yp, zero_division=0)), 4),
                'recall': round(float(recall_score(yt, yp, zero_division=0)), 4),
                'f1': round(float(f1_score(yt, yp, zero_division=0)), 4),
                'confusion_matrix': confusion_matrix(yt, yp).tolist(),
            }
        else:
            model.fit(X_train, y_train)
            m = evaluate(name, model, X_test, y_test)
        metrics[name] = m
        trained[name] = model
        print(f"  {name}: {m}")
        if hasattr(model, 'feature_importances_'):
            importances[name] = [round(float(v), 4) for v in model.feature_importances_]
        elif hasattr(model, 'coef_'):
            c = np.abs(model.coef_[0])
            importances[name] = [round(float(v / c.sum()), 4) for v in c]

    best_name = max(metrics, key=lambda k: metrics[k]['f1'])
    print("Best model:", best_name)
    joblib.dump(trained[best_name], os.path.join(MODEL_DIR, 'phishing_model.pkl'))
    # save all models too
    for name, model in trained.items():
        safe = name.lower().replace(' ', '_')
        joblib.dump(model, os.path.join(MODEL_DIR, f'{safe}.pkl'))

    with open(os.path.join(MODEL_DIR, 'metrics.json'), 'w') as f:
        json.dump({'models': metrics, 'best_model': best_name,
                   'n_train': len(X_train), 'n_test': len(X_test)}, f, indent=2)
    with open(os.path.join(MODEL_DIR, 'feature_names.json'), 'w') as f:
        json.dump(FEATURE_NAMES, f, indent=2)
    # feature importance of best (or RF if available)
    imp_src = best_name if best_name in importances else list(importances.keys())[0]
    imp = sorted(zip(FEATURE_NAMES, importances[imp_src]), key=lambda x: x[1], reverse=True)
    with open(os.path.join(MODEL_DIR, 'feature_importance.json'), 'w') as f:
        json.dump([{'feature': k, 'importance': v} for k, v in imp], f, indent=2)
    print("Saved artifacts to", MODEL_DIR)


if __name__ == '__main__':
    main()
