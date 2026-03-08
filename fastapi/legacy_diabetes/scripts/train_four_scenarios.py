from __future__ import annotations

import argparse
import json
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
from sklearn.ensemble import (
    AdaBoostClassifier,
    GradientBoostingClassifier,
    RandomForestClassifier,
    VotingClassifier,
)
from sklearn.impute import KNNImputer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import accuracy_score, f1_score, precision_score, recall_score
from sklearn.model_selection import train_test_split
from sklearn.neighbors import KNeighborsClassifier
from sklearn.neural_network import MLPClassifier
from sklearn.svm import SVC
from sklearn.tree import DecisionTreeClassifier
from sklearn.preprocessing import StandardScaler


KOR_COL = {
    "pregnancies": "임신횟수",
    "glucose": "혈당",
    "bmi": "BMI",
    "age": "나이",
}

SCENARIOS = {
    "A": {"name": "a_detail_sugar", "features_eng": ["pregnancies", "glucose", "bmi", "age"], "mode": "detailed"},
    "B": {"name": "b_detail_no_sugar", "features_eng": ["pregnancies", "bmi", "age"], "mode": "detailed"},
    "C": {"name": "c_simple_sugar", "features_eng": ["pregnancies", "glucose", "bmi", "age"], "mode": "simple"},
    "C_NS": {"name": "cns_simple_no_sugar", "features_eng": ["pregnancies", "bmi", "age"], "mode": "simple"},
}


def _candidate_models():
    return [
        ("LR", LogisticRegression(C=0.01, random_state=42, max_iter=1000)),
        ("KNN", KNeighborsClassifier(n_neighbors=15)),
        ("RF", RandomForestClassifier(n_estimators=100, max_depth=3, random_state=42)),
        ("GB", GradientBoostingClassifier(n_estimators=30, max_depth=2, random_state=42)),
        ("Ada", AdaBoostClassifier(n_estimators=100, learning_rate=0.1, random_state=42)),
        ("SVM", SVC(C=1, probability=True, random_state=42)),
        ("MLP", MLPClassifier(hidden_layer_sizes=(50,), max_iter=1000, random_state=42)),
        ("DT", DecisionTreeClassifier(max_depth=3, random_state=42)),
    ]


def _to_grade(v: float, q1: float, q2: float, q3: float) -> int:
    # 노트북 동작과 동일하게 NaN은 else로 떨어져 4가 되도록 유지
    if v <= q1:
        return 1
    if v <= q2:
        return 2
    if v <= q3:
        return 3
    return 4


def _preprocess_detailed(x_train: pd.DataFrame, x_valid: pd.DataFrame, x_test: pd.DataFrame):
    clip_bounds: dict[str, list[float]] = {}
    for col in x_train.columns:
        q1, q3 = x_train[col].quantile([0.25, 0.75])
        iqr = q3 - q1
        low, up = q1 - 1.5 * iqr, q3 + 1.5 * iqr
        clip_bounds[col] = [float(low), float(up)]
        x_train[col] = x_train[col].clip(low, up)
        x_valid[col] = x_valid[col].clip(low, up)
        x_test[col] = x_test[col].clip(low, up)

    scaler = StandardScaler()
    imputer = KNNImputer(n_neighbors=5)
    x_train_pre = imputer.fit_transform(scaler.fit_transform(x_train))
    x_valid_pre = imputer.transform(scaler.transform(x_valid))
    x_test_pre = imputer.transform(scaler.transform(x_test))
    return x_train_pre, x_valid_pre, x_test_pre, scaler, imputer, clip_bounds


def _preprocess_simple(x_train: pd.DataFrame, x_valid: pd.DataFrame, x_test: pd.DataFrame):
    quantiles: dict[str, list[float]] = {}
    x_train_g = x_train.copy()
    x_valid_g = x_valid.copy()
    x_test_g = x_test.copy()
    for col in x_train.columns:
        q1, q2, q3 = x_train[col].quantile([0.25, 0.5, 0.75])
        quantiles[col] = [float(q1), float(q2), float(q3)]
        x_train_g[col] = x_train[col].apply(lambda v: _to_grade(v, q1, q2, q3))
        x_valid_g[col] = x_valid[col].apply(lambda v: _to_grade(v, q1, q2, q3))
        x_test_g[col] = x_test[col].apply(lambda v: _to_grade(v, q1, q2, q3))
    return x_train_g, x_valid_g, x_test_g, quantiles


def _select_winner(x_train_pre, y_train, x_valid_pre, y_valid):
    perf = []
    fitted = {}
    for name, model in _candidate_models():
        model.fit(x_train_pre, y_train)
        perf.append({"name": name, "score": float(model.score(x_valid_pre, y_valid))})
        fitted[name] = model
    perf.sort(key=lambda x: x["score"], reverse=True)
    top3 = perf[:3]
    ensemble = VotingClassifier(
        estimators=[(m["name"], fitted[m["name"]]) for m in top3],
        voting="soft",
    )
    ensemble.fit(x_train_pre, y_train)
    perf.append({"name": "Voting Ensemble (Top 3 Mix)", "score": float(ensemble.score(x_valid_pre, y_valid))})
    perf.sort(key=lambda x: x["score"], reverse=True)
    winner_name = perf[0]["name"]
    if winner_name == "Voting Ensemble (Top 3 Mix)":
        return ensemble, winner_name, perf
    return fitted[winner_name], winner_name, perf


def _optimize_threshold(model, x_valid_pre, y_valid):
    probs = model.predict_proba(x_valid_pre)[:, 1]
    best_th, best_acc = 0.5, -1.0
    for th in np.arange(0.3, 0.7, 0.01):
        preds = (probs >= th).astype(int)
        acc = accuracy_score(y_valid, preds)
        if acc > best_acc:
            best_acc = acc
            best_th = float(th)
    return best_th


def _metrics(model, x_data, y_data, th):
    probs = model.predict_proba(x_data)[:, 1]
    preds = (probs >= th).astype(int)
    return {
        "accuracy": float(accuracy_score(y_data, preds)),
        "precision": float(precision_score(y_data, preds, zero_division=0)),
        "recall": float(recall_score(y_data, preds, zero_division=0)),
        "f1": float(f1_score(y_data, preds, zero_division=0)),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="최종 리포트 셀(run_best_model_and_report) 기준 4시나리오 학습")
    parser.add_argument("--csv", default="/Users/cheng80/Desktop/diabetes_python/Data/당뇨.csv")
    parser.add_argument("--out-dir", default=str(Path(__file__).resolve().parents[1] / "app"))
    parser.add_argument("--overwrite-runtime", action="store_true")
    args = parser.parse_args()

    csv_path = Path(args.csv)
    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    if not csv_path.exists():
        raise FileNotFoundError(f"CSV 파일이 없습니다: {csv_path}")

    df = pd.read_csv(csv_path)
    if "당뇨" not in df.columns:
        raise ValueError("CSV에 타깃 컬럼 '당뇨'가 없습니다.")
    y = df["당뇨"]

    cols_zero = ["혈당", "혈압", "피부두께", "인슐린", "BMI"]
    for c in cols_zero:
        if c in df.columns:
            df[c] = df[c].replace(0, np.nan)

    metadata: dict[str, dict] = {"scenarios": {}}

    for key, cfg in SCENARIOS.items():
        name = cfg["name"]
        mode = cfg["mode"]
        features_eng = cfg["features_eng"]
        features_kor = [KOR_COL[f] for f in features_eng]
        x = df[features_kor].copy()

        x_temp, x_test, y_temp, y_test = train_test_split(
            x, y, test_size=0.2, stratify=y, random_state=42
        )
        x_train, x_valid, y_train, y_valid = train_test_split(
            x_temp, y_temp, test_size=0.25, stratify=y_temp, random_state=42
        )

        if mode == "detailed":
            x_train_pre, x_valid_pre, x_test_pre, scaler, imputer, clip_bounds = _preprocess_detailed(
                x_train.copy(), x_valid.copy(), x_test.copy()
            )
            quantiles = None
        else:
            x_train_pre, x_valid_pre, x_test_pre, quantiles = _preprocess_simple(
                x_train.copy(), x_valid.copy(), x_test.copy()
            )
            scaler = None
            imputer = None
            clip_bounds = None

        model, winner_name, perf = _select_winner(x_train_pre, y_train, x_valid_pre, y_valid)
        threshold = _optimize_threshold(model, x_valid_pre, y_valid)

        train_m = _metrics(model, x_train_pre, y_train, threshold)
        valid_m = _metrics(model, x_valid_pre, y_valid, threshold)
        test_m = _metrics(model, x_test_pre, y_test, threshold)

        joblib.dump(model, out_dir / f"{name}_model.joblib")
        if scaler is not None:
            joblib.dump(scaler, out_dir / f"{name}_scaler.joblib")
        if imputer is not None:
            joblib.dump(imputer, out_dir / f"{name}_imputer.joblib")
        if clip_bounds is not None:
            joblib.dump(clip_bounds, out_dir / f"{name}_clip_bounds.joblib")
        if quantiles is not None:
            joblib.dump(quantiles, out_dir / f"{name}_quantiles.joblib")

        metadata["scenarios"][key] = {
            "artifact_name": name,
            "mode": mode,
            "features_eng": features_eng,
            "features_kor": features_kor,
            "winner_model": winner_name,
            "threshold": threshold,
            "metrics": {"train": train_m, "valid": valid_m, "test": test_m},
            "candidates_valid_accuracy": perf,
        }

        print(
            f"[{key}] winner={winner_name}, threshold={threshold:.2f}, "
            f"test_acc={test_m['accuracy']:.4f}"
        )

    if args.overwrite_runtime:
        a_model = joblib.load(out_dir / "a_detail_sugar_model.joblib")
        b_model = joblib.load(out_dir / "b_detail_no_sugar_model.joblib")
        joblib.dump(a_model, out_dir / "model_sugar.joblib")
        joblib.dump(b_model, out_dir / "model_no_sugar.joblib")
        metadata["compat"] = {
            "model_sugar.joblib": "A",
            "model_no_sugar.joblib": "B",
        }

    (out_dir / "model_scenarios_meta.json").write_text(
        json.dumps(metadata, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    print("저장 완료: model_scenarios_meta.json")


if __name__ == "__main__":
    main()
