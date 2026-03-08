from __future__ import annotations

import json
from pathlib import Path

import joblib

APP_DIR = Path(__file__).resolve().parent

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

FEATURE_LABELS = {
    "age": "나이",
    "hypertension": "고혈압",
    "heart_disease": "심장질환",
    "avg_glucose_level": "평균 혈당",
    "bmi": "BMI",
    "smoking_status": "흡연 상태",
}

DEFAULT_FEATURE_RANGES = {
    "age": (-3.0, 3.0),
    "hypertension": (-1.0, 5.0),
    "heart_disease": (-1.0, 5.0),
    "avg_glucose_level": (-3.0, 3.0),
    "bmi": (-3.0, 3.0),
    "smoking_status": (-2.0, 3.0),
}


def _load_required(path: Path, label: str):
    if not path.exists():
        raise FileNotFoundError(f"{label} 파일을 찾을 수 없습니다: {path}")
    return joblib.load(path)


def _load_json(path: Path):
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


# 모델 교체 지점 4:
# 런타임에서 불러오는 모델 파일명을 여기서 정의합니다.
# 학습 스크립트에서 파일명을 바꿨다면 아래 두 경로를 함께 수정하세요.
MODEL_WITH_GLUCOSE = _load_required(
    APP_DIR / "stroke_model_with_glucose.joblib",
    "뇌졸중(혈당 포함) 모델",
)
MODEL_NO_GLUCOSE = _load_required(
    APP_DIR / "stroke_model_without_glucose.joblib",
    "뇌졸중(혈당 미포함) 모델",
)
META = _load_json(APP_DIR / "stroke_model_meta.json")

FEATURE_RANGES = META.get("feature_ranges", DEFAULT_FEATURE_RANGES)


def get_model_threshold(with_glucose: bool) -> float:
    # 모델 교체 지점 5:
    # 분류 임계값은 stroke_model_meta.json에서 읽습니다.
    # 새 모델 교체 후 임계값 기준이 달라지면 meta 파일을 함께 갱신하세요.
    defaults = {"with_glucose": 0.5, "without_glucose": 0.5}
    thresholds = META.get("thresholds", defaults)
    key = "with_glucose" if with_glucose else "without_glucose"
    try:
        return float(thresholds.get(key, defaults[key]))
    except Exception:
        return defaults[key]


def get_band_thresholds() -> tuple[float, float]:
    defaults = {"low": 0.33, "high": 0.66}
    band = META.get("band_thresholds", defaults)
    try:
        low = float(band.get("low", defaults["low"]))
        high = float(band.get("high", defaults["high"]))
    except Exception:
        return defaults["low"], defaults["high"]

    if low >= high:
        return defaults["low"], defaults["high"]
    return low, high


def _typename(obj) -> str:
    return type(obj).__name__ if obj is not None else "None"


print(
    "[모델 로드 완료] "
    f"with_glucose={_typename(MODEL_WITH_GLUCOSE)}, "
    f"without_glucose={_typename(MODEL_NO_GLUCOSE)}"
)
