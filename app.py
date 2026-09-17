"""Phishing Website Detector — Flask app."""
import json, os
import joblib
import numpy as np
from flask import Flask, render_template, request, jsonify

from features import FEATURE_NAMES, EXPLANATIONS, extract_features, features_to_vector

app = Flask(__name__)
BASE = os.path.dirname(__file__)
MODEL_PATH = os.path.join(BASE, 'models', 'phishing_model.pkl')
METRICS_PATH = os.path.join(BASE, 'models', 'metrics.json')
IMP_PATH = os.path.join(BASE, 'models', 'feature_importance.json')

model = joblib.load(MODEL_PATH)
with open(METRICS_PATH) as f:
    METRICS = json.load(f)
try:
    with open(IMP_PATH) as f:
        IMPORTANCE = json.load(f)
except FileNotFoundError:
    IMPORTANCE = []

MODEL_LABEL = METRICS.get('best_model', 'Random Forest')


def predict_url(url: str):
    feats = extract_features(url)
    vec = np.array(features_to_vector(feats)).reshape(1, -1)
    # model may be XGB (0/1) or sklearn (-1/1)
    try:
        proba = model.predict_proba(vec)[0]
        classes = list(model.classes_)
        # phishing class: -1 for sklearn, 1 for XGB
        if -1 in classes:
            phish_p = float(proba[classes.index(-1)])
        else:
            phish_p = float(proba[classes.index(1)])
        pred = model.predict(vec)[0]
        is_phish = (pred == -1) if -1 in classes else (pred == 1)
    except Exception:
        pred = model.predict(vec)[0]
        is_phish = str(pred) == '-1'
        phish_p = 0.85 if is_phish else 0.15
    legit_p = 1 - phish_p
    risk = round(phish_p * 100, 1)
    if risk >= 70:
        verdict, level = 'PHISHING', 'danger'
    elif risk >= 40:
        verdict, level = 'SUSPICIOUS', 'warning'
    else:
        verdict, level = 'LEGITIMATE', 'safe'

    detail = []
    for name in FEATURE_NAMES:
        v = int(feats.get(name, 0))
        detail.append({
            'feature': name,
            'value': v,
            'label': 'Phishy' if v == -1 else ('Suspicious' if v == 0 else 'Legit'),
            'explanation': EXPLANATIONS.get(name, '')
        })
    signals = [d for d in detail if d['value'] == -1][:8]
    return {
        'url': url, 'verdict': verdict, 'level': level,
        'risk_score': risk, 'phish_prob': round(phish_p, 4), 'legit_prob': round(legit_p, 4),
        'model': MODEL_LABEL, 'features': detail, 'top_signals': signals,
        'counts': {'phishy': sum(1 for d in detail if d['value'] == -1),
                   'suspicious': sum(1 for d in detail if d['value'] == 0),
                   'legit': sum(1 for d in detail if d['value'] == 1)},
    }


@app.route('/')
def index():
    return render_template('index.html', metrics=METRICS, importance=IMPORTANCE[:12])


@app.route('/api/predict', methods=['POST'])
def api_predict():
    data = request.get_json(force=True, silent=True) or {}
    url = (data.get('url') or '').strip()
    if not url:
        return jsonify({'error': 'Please enter a URL.'}), 400
    return jsonify(predict_url(url))


@app.route('/api/batch', methods=['POST'])
def api_batch():
    data = request.get_json(force=True, silent=True) or {}
    urls = data.get('urls') or []
    urls = [u.strip() for u in urls if u and u.strip()][:20]
    if not urls:
        return jsonify({'error': 'No URLs provided.'}), 400
    return jsonify({'results': [predict_url(u) for u in urls]})


@app.route('/api/metrics')
def api_metrics():
    return jsonify(METRICS)


@app.route('/api/importance')
def api_importance():
    return jsonify(IMPORTANCE)


if __name__ == '__main__':
    app.run(debug=True, port=5000)
