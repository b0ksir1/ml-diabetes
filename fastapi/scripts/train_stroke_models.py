from __future__ import annotations

import argparse
import json
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
from sklearn.linear_model import LogisticRegression
# 모델 교체 지점:
# 알고리즘을 변경하려면 아래 _train_one()의 model 생성부를 바꾸고,
# 필요한 sklearn import를 여기에서 함께 추가하세요.
# 예: RandomForestClassifier, XGBClassifier, SVC(probability=True)
from sklearn.metrics import accuracy_score, f1_score, precision_score, recall_score, roc_auc_score

FEATURES_WITH_GLUCOSE = [
    "age",
    "hypertension",
    "heart_disease",
    "avg_glucose_level",
    "bmi",
    "smoking_status",
]
FEATURES_NO_GLUCOSE = [
    "age",
    "hypertension",
    "heart_disease",
    "bmi",
    "smoking_status",
]
TARGET = "stroke"


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="전처리된 stroke CSV로 모델을 학습합니다")
    parser.add_argument(
        "--train",
        default=r"c:\Users\User_KO\Documents\WorkSpace\Python\project_brain\data\stroke_train_smote.csv",
    )
    parser.add_argument(
        "--valid",
        default=r"c:\Users\User_KO\Documents\WorkSpace\Python\project_brain\data\stroke_valid.csv",
    )
    parser.add_argument(
        "--test",
        default=r"c:\Users\User_KO\Documents\WorkSpace\Python\project_brain\data\stroke_test.csv",
    )
    parser.add_argument(
        "--out-dir",
        default=str(Path(__file__).resolve().parents[1] / "app"),
    )
    return parser.parse_args()


def _load_csv(path: str) -> pd.DataFrame:
    p = Path(path)
    if not p.exists():
        raise FileNotFoundError(f"CSV를 찾을 수 없습니다: {p}")
    return pd.read_csv(p)


def _pick_threshold(y_true: np.ndarray, probs: np.ndarray) -> float:
    # 단순하고 재현 가능한 방식으로 threshold를 탐색
    candidates = np.linspace(0.10, 0.90, 161)
    best_t = 0.5
    best_score = -1.0
    for t in candidates:
        pred = (probs >= t).astype(int)
        score = f1_score(y_true, pred, zero_division=0)
        if score > best_score:
            best_score = score
            best_t = float(t)
    return best_t


def _metrics(y_true: np.ndarray, probs: np.ndarray, threshold: float) -> dict[str, float]:
    pred = (probs >= threshold).astype(int)
    return {
        "accuracy": float(accuracy_score(y_true, pred)),
        "precision": float(precision_score(y_true, pred, zero_division=0)),
        "recall": float(recall_score(y_true, pred, zero_division=0)),
        "f1": float(f1_score(y_true, pred, zero_division=0)),
        "roc_auc": float(roc_auc_score(y_true, probs)),
    }


def _train_one(
    train_df: pd.DataFrame,
    valid_df: pd.DataFrame,
    test_df: pd.DataFrame,
    features: list[str],
) -> tuple[LogisticRegression, float, dict[str, dict[str, float]]]:
    x_train = train_df[features].to_numpy(dtype=float)
    y_train = train_df[TARGET].to_numpy(dtype=int)

    x_valid = valid_df[features].to_numpy(dtype=float)
    y_valid = valid_df[TARGET].to_numpy(dtype=int)

    x_test = test_df[features].to_numpy(dtype=float)
    y_test = test_df[TARGET].to_numpy(dtype=int)

    # 모델 교체 지점 1:
    # 아래 estimator를 원하는 모델로 교체하세요.
    # 런타임은 predict_proba를 사용하므로 확률 출력이 가능한 모델이어야 합니다.
    model = LogisticRegression(max_iter=3000, class_weight="balanced", random_state=42)
    model.fit(x_train, y_train)

    valid_probs = model.predict_proba(x_valid)[:, 1]
    test_probs = model.predict_proba(x_test)[:, 1]

    threshold = _pick_threshold(y_valid, valid_probs)
    report = {
        "valid": _metrics(y_valid, valid_probs, threshold),
        "test": _metrics(y_test, test_probs, threshold),
    }
    return model, threshold, report


def _feature_ranges(*dfs: pd.DataFrame, features: list[str]) -> dict[str, list[float]]:
    merged = pd.concat([d[features] for d in dfs], axis=0, ignore_index=True)
    ranges: dict[str, list[float]] = {}
    for f in features:
        min_v = float(np.nanmin(merged[f].to_numpy(dtype=float)))
        max_v = float(np.nanmax(merged[f].to_numpy(dtype=float)))
        margin = 0.05 * (max_v - min_v if max_v > min_v else 1.0)
        ranges[f] = [min_v - margin, max_v + margin]
    return ranges


def main() -> None:
    args = _parse_args()
    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    train_df = _load_csv(args.train)
    valid_df = _load_csv(args.valid)
    test_df = _load_csv(args.test)

    required = set(FEATURES_WITH_GLUCOSE + [TARGET])
    missing = required - set(train_df.columns)
    if missing:
        raise ValueError(f"train CSV에 필수 컬럼이 없습니다: {sorted(missing)}")

    model_with, threshold_with, report_with = _train_one(
        train_df, valid_df, test_df, FEATURES_WITH_GLUCOSE
    )
    model_without, threshold_without, report_without = _train_one(
        train_df, valid_df, test_df, FEATURES_NO_GLUCOSE
    )

    # 모델 교체 지점 2:
    # 저장 파일명을 바꾸면 fastapi/app/model_loader.py에서도 동일하게 바꿔야 합니다.
    model_with_path = out_dir / "stroke_model_with_glucose.joblib"
    model_without_path = out_dir / "stroke_model_without_glucose.joblib"

    joblib.dump(model_with, model_with_path)
    joblib.dump(model_without, model_without_path)

    feature_ranges = _feature_ranges(
        train_df,
        valid_df,
        test_df,
        features=FEATURES_WITH_GLUCOSE,
    )

    meta = {
        "version": 1,
        "target": TARGET,
        "models": {
            "with_glucose": {
                "path": model_with_path.name,
                "features": FEATURES_WITH_GLUCOSE,
                # 모델 교체 지점 3:
                # 위에서 사용한 알고리즘 이름과 맞춰서 기록하세요.
                "algorithm": "LogisticRegression",
                "valid_metrics": report_with["valid"],
                "test_metrics": report_with["test"],
            },
            "without_glucose": {
                "path": model_without_path.name,
                "features": FEATURES_NO_GLUCOSE,
                # 모델 교체 지점 3:
                # 위에서 사용한 알고리즘 이름과 맞춰서 기록하세요.
                "algorithm": "LogisticRegression",
                "valid_metrics": report_without["valid"],
                "test_metrics": report_without["test"],
            },
        },
        "thresholds": {
            "with_glucose": threshold_with,
            "without_glucose": threshold_without,
        },
        "band_thresholds": {
            "low": 0.33,
            "high": 0.66,
        },
        "feature_ranges": feature_ranges,
    }

    meta_path = out_dir / "stroke_model_meta.json"
    meta_path.write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")

    print("저장 완료:")
    print(f"- {model_with_path}")
    print(f"- {model_without_path}")
    print(f"- {meta_path}")
    print("\n임계값:")
    print(f"- with_glucose: {threshold_with:.4f}")
    print(f"- without_glucose: {threshold_without:.4f}")
    print("\n테스트 지표 (with_glucose):", report_with["test"])
    print("테스트 지표 (without_glucose):", report_without["test"])


if __name__ == "__main__":
    main()
