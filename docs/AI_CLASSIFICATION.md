# AI Ticket Classification

## What the analyzer does

`POST /api/ai/analyze-ticket` analyzes a title and description with a local scikit-learn `Pipeline(TfidfVectorizer, LogisticRegression)`. Its six possible labels are Hardware, Software, Network, Account & Access, Security, and Other. The reported confidence is the fitted logistic-regression probability for the predicted class; it is not calibrated.

Team routing is deterministic:

| Category | Recommended team |
| --- | --- |
| Hardware | Desktop Support |
| Software | Application Support |
| Network | Network Support |
| Account & Access | Identity & Access Support |
| Security | Security Operations |
| Other | IT Support |

Priority is a separate, deterministic rules recommendation, not a trained prediction. Rules inspect the title, description, and optional business impact, in this order:

1. `critical`: cues such as `ransomware`, `confirmed breach`, `active compromise`, or a company-wide/production outage.
2. `high`: cues such as `multiple users`, `cannot work`, `data loss`, `security incident`, or `urgent`.
3. `low`: cues such as `minor`, `cosmetic`, `how to`, `question`, or `workaround available`.
4. `medium`: the default when no configured cue matches.

The matching is case-insensitive substring matching, not semantic impact analysis. The result is a recommendation only: this endpoint neither creates tickets nor changes human-selected ticket category or priority. A predicted-class confidence below `0.55` sets `needs_manual_review=true`.

## Dataset and evaluation protocol

- The dataset at `data/sample_tickets/fictional_classification_tickets.csv` contains **108 fictional records**, with 18 records per category. No real user or company data is used.
- `scripts/generate_ticket_dataset.py` regenerates it with `random.Random(20261113)`.
- Training uses title plus description; the optional business-impact text is used only by priority rules.
- Evaluation uses the first fold from `StratifiedGroupKFold(n_splits=4, shuffle=True, random_state=20261113)`: **81 train rows and 27 held-out test rows**.
- Three wording variants share each `scenario_group`, and the grouping keeps every variant of a scenario on one side of the split.
- The training script checks normalized exact duplicates and cross-split `difflib.SequenceMatcher` similarity. It rejects a cross-split pair with similarity **>= 0.88**. In this run the maximum was **0.7344**, with no exact duplicates or near-duplicate pairs over the threshold.
- TF-IDF uses word unigrams/bigrams and sublinear term frequency. Logistic Regression uses `max_iter=1000` and `random_state=20261113`. The persisted artifact is fitted on the 81 training rows, not refitted on held-out examples.

Run `python scripts\generate_ticket_dataset.py` to regenerate the CSV, then `python scripts\train_ticket_classifier.py` to train, evaluate, save the local artifact, and refresh `docs/AI_CLASSIFICATION_EVALUATION.json`.

## Held-out results — synthetic-data performance only

These are the measured results of the protocol above. They are **not real-world accuracy claims**:

- Accuracy: **1.0000**
- Macro F1: **1.0000**

Confusion matrix (rows are true labels; columns are predictions):

| True \ Predicted | Hardware | Software | Network | Account & Access | Security | Other |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| Hardware | 6 | 0 | 0 | 0 | 0 | 0 |
| Software | 0 | 3 | 0 | 0 | 0 | 0 |
| Network | 0 | 0 | 6 | 0 | 0 | 0 |
| Account & Access | 0 | 0 | 0 | 3 | 0 | 0 |
| Security | 0 | 0 | 0 | 0 | 3 | 0 |
| Other | 0 | 0 | 0 | 0 | 0 | 6 |

Per-class test support: Hardware **6**, Software **3**, Network **6**, Account & Access **3**, Security **3**, Other **6**.

## Limitations

This is a small, generated, templated dataset. Its category-specific wording is strongly correlated with labels, which makes the held-out task controlled and explains the high synthetic score. A scenario-group split and similarity check reduce wording leakage but cannot make generated examples representative of real support tickets. Real-world language, class imbalance, ambiguous reports, probability calibration, and model performance have not been evaluated. Treat predictions and confidence as advisory, use the manual-review flag, and do not use these results to claim production or real-world accuracy.

The model file is generated under `backend/app/ai/artifacts/` and excluded from Git. Train it locally before using the endpoint. The app does not retrain during requests; a running process continues using its cached model until restarted. Only load model artifacts generated from this repository's trusted training script.
