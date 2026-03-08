from __future__ import annotations

import json
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
from sklearn.metrics import accuracy_score, f1_score, precision_score, recall_score
from sklearn.model_selection import train_test_split


CSV_PATH = Path("/Users/cheng80/Desktop/diabetes_python/Data/당뇨.csv")
APP_DIR = Path(__file__).resolve().parents[1] / "app"


PASS_CRITERIA = {
    "A": 0.70,
    "B": 0.65,
    "C": 0.70,
    "C_NS": 0.65,
}


def to_grade(v: float, q: list[float]) -> int:
    if v <= q[0]:
        return 1
    if v <= q[1]:
        return 2
    if v <= q[2]:
        return 3
    return 4


def eval_scenario(df: pd.DataFrame, y: pd.Series, key: str, meta_s: dict) -> dict[str, float]:
    cols = meta_s["features_kor"]
    name = meta_s["artifact_name"]
    mode = meta_s["mode"]
    th = float(meta_s["threshold"])

    x = df[cols].copy()

    x_temp, x_test, y_temp, y_test = train_test_split(
        x, y, test_size=0.2, stratify=y, random_state=42
    )
    x_train, _x_valid, y_train, _y_valid = train_test_split(
        x_temp, y_temp, test_size=0.25, stratify=y_temp, random_state=42
    )

    model = joblib.load(APP_DIR / f"{name}_model.joblib")

    if mode == "detailed":
        scaler = joblib.load(APP_DIR / f"{name}_scaler.joblib")
        imputer = joblib.load(APP_DIR / f"{name}_imputer.joblib")
        clip_bounds: dict[str, list[float]] = joblib.load(APP_DIR / f"{name}_clip_bounds.joblib")
        for c in cols:
            low, up = clip_bounds[c]
            x_train[c] = x_train[c].clip(low, up)
            x_test[c] = x_test[c].clip(low, up)
        x_train_pre = imputer.transform(scaler.transform(x_train))
        x_test_pre = imputer.transform(scaler.transform(x_test))
    else:
        quantiles: dict[str, list[float]] = joblib.load(APP_DIR / f"{name}_quantiles.joblib")
        x_train_pre = pd.DataFrame(index=x_train.index)
        x_test_pre = pd.DataFrame(index=x_test.index)
        for c in cols:
            q = quantiles[c]
            x_train_pre[c] = x_train[c].apply(lambda v: to_grade(float(v), q))
            x_test_pre[c] = x_test[c].apply(lambda v: to_grade(float(v), q))

    train_probs = model.predict_proba(x_train_pre)[:, 1]
    test_probs = model.predict_proba(x_test_pre)[:, 1]
    train_pred = (train_probs >= th).astype(int)
    test_pred = (test_probs >= th).astype(int)

    return {
        "train_accuracy": float(accuracy_score(y_train, train_pred)),
        "test_accuracy": float(accuracy_score(y_test, test_pred)),
        "test_precision": float(precision_score(y_test, test_pred, zero_division=0)),
        "test_recall": float(recall_score(y_test, test_pred, zero_division=0)),
        "test_f1": float(f1_score(y_test, test_pred, zero_division=0)),
    }


def main() -> None:
    if not CSV_PATH.exists():
        raise FileNotFoundError(f"CSV 파일이 없습니다: {CSV_PATH}")

    df = pd.read_csv(CSV_PATH)
    if "당뇨" not in df.columns:
        raise ValueError("CSV에 타깃 컬럼 '당뇨'가 없습니다.")
    y = df["당뇨"]

    meta = json.loads((APP_DIR / "model_scenarios_meta.json").read_text(encoding="utf-8"))
    results: dict[str, dict] = {}
    passed_all = True

    print("=== 4개 시나리오 검증 시작 ===")
    for key in ["A", "B", "C", "C_NS"]:
        m = eval_scenario(df, y, key, meta["scenarios"][key])
        crit = PASS_CRITERIA[key]
        passed = m["test_accuracy"] >= crit
        passed_all = passed_all and passed
        results[key] = {
            **m,
            "pass_accuracy_threshold": crit,
            "passed": passed,
        }
        print(
            f"[{key}] test_acc={m['test_accuracy']:.4f}, "
            f"precision={m['test_precision']:.4f}, recall={m['test_recall']:.4f}, "
            f"f1={m['test_f1']:.4f} -> {'PASS' if passed else 'FAIL'}"
        )

    summary = {"passed_all": passed_all, "results": results}
    out_path = APP_DIR / "model_validation_report.json"
    out_path.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")

    print("\n=== 종합 결과 ===")
    print("PASS" if passed_all else "FAIL")
    print(f"리포트 저장: {out_path}")


if __name__ == "__main__":
    main()
