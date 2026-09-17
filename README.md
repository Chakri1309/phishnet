# 🛡️ PhishNet AI — Detection of Phishing Websites Using Machine Learning

Interactive Python ML project: train 3 classifiers on the **UCI Phishing Websites** dataset (11,055 sites × 30 features) and judge **any live URL** in a very interactive Flask website.

## ✨ Features
- **Live scanner**: paste any URL → 30 forensic features → risk gauge, verdict, top signals, full feature chart
- **Model arena**: Logistic Regression vs Random Forest vs XGBoost (accuracy / precision / recall / F1 + confusion matrix + feature importance)
- **Bulk checker**: up to 20 URLs at once + CSV download
- **History** (localStorage), **phishing quiz**, animated dark UI with Chart.js

## 🚀 Quickstart
```bash
pip install -r requirements.txt   # web app only (slim, deploy-safe)
pip install -r requirements-train.txt  # + pandas/xgboost, only if retraining
python train.py      # downloads UCI data, trains, saves models/
python app.py        # → http://127.0.0.1:5000
```

## ☁️ Deploy (Vercel)
Import the repo in Vercel — no extra config needed (`vercel.json` routes
everything to the Flask app in `api/index.py`). `requirements.txt` is
inference-only so the serverless bundle stays under Vercel's 500 MB limit.

## 🧠 Results (same 80/20 split, 2,211 test sites — `python train_advanced.py`)
| Model | Acc | Prec | Rec | F1 |
|---|---|---|---|---|
| Logistic Regression | 0.929 | 0.935 | 0.902 | 0.918 |
| Random Forest | 0.9742 | 0.9782 | 0.9633 | 0.9707 |
| XGBoost | 0.9701 | 0.9751 | 0.9571 | 0.966 |
| Random Forest (tuned) | 0.9765 | 0.9793 | 0.9673 | 0.9733 |
| ExtraTrees (tuned) | 0.9765 | 0.9774 | 0.9694 | 0.9734 |
| HistGradBoost (tuned) 👑 **(live — compact 2.8 MB build)** | 0.9769 | 0.9804 | 0.9673 | 0.9738 |
| XGBoost (tuned) | 0.9765 | 0.9784 | 0.9684 | 0.9733 |
| Voting Ensemble | 0.9769 | 0.9794 | 0.9684 | 0.9738 |
| **Stacking Ensemble** | **0.9774** | 0.9804 | 0.9684 | 0.9743 |

Test errors dropped 57 → 50. Baseline script kept as `train.py`; tuned version is `train_advanced.py` (RandomizedSearchCV + soft voting + stacking, old model backed up to `models/phishing_model_backup.pkl`).

## 📁 Structure
```
phishing-detector/
  app.py              # Flask app + /api/predict, /api/batch
  train.py            # dataset download + training + metrics
  features.py         # URL → 30 UCI-style features (-1/0/1)
  requirements.txt
  models/             # phishing_model.pkl, metrics.json, feature_importance.json
  data/               # UCI ARFF (auto-downloaded)
  templates/index.html
  static/css/style.css  static/js/main.js
```

## 🧬 The 30 features
IP-in-URL, length, shortener, @, //-redirect, prefix-suffix, subdomains, SSL, domain age/registration, favicon, port, https-token, request-URL, anchors, tags, form-handler, mailto, abnormal URL, redirects, mouseover, right-click, popup, iframe, DNS, traffic, PageRank, Google-index, backlinks, blacklist. See `features.py:EXPLANATIONS`.

> ⚠️ Educational project — always verify sensitive links manually.
