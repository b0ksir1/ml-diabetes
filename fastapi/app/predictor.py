from __future__ import annotations

import base64
import io

import matplotlib
import matplotlib.pyplot as plt
import numpy as np
from fastapi import HTTPException

from app.model_loader import (
    FEATURE_LABELS,
    FEATURE_RANGES,
    FEATURES_NO_GLUCOSE,
    FEATURES_WITH_GLUCOSE,
    MODEL_NO_GLUCOSE,
    MODEL_WITH_GLUCOSE,
    get_band_thresholds,
    get_model_threshold,
)
from app.schemas import PredictRequest, PredictResponse

matplotlib.use("Agg")
# 한글 폰트 우선순위: Windows -> macOS -> fallback
plt.rcParams["font.family"] = ["Malgun Gothic", "AppleGothic", "DejaVu Sans"]
plt.rcParams["axes.unicode_minus"] = False


def _create_chart_base64(
    probability: float,
    input_values: dict[str, float],
    model,
    feature_names: list[str],
) -> str:
    fig, axes = plt.subplots(2, 1, figsize=(6, 7))

    ax1 = axes[0]
    stroke_prob = max(0.0, min(1.0, probability))
    non_stroke_prob = 1.0 - stroke_prob
    labels = ["비발생 가능성", "뇌졸중 위험 가능성"]
    values = [non_stroke_prob, stroke_prob]
    colors = ["#4CAF50", "#E53935"]

    bars = ax1.bar(labels, values, color=colors)
    ax1.set_ylim(0, 1)
    ax1.set_ylabel("확률")
    ax1.set_title("뇌졸중 예측 결과")

    for bar, value in zip(bars, values):
        ax1.text(
            bar.get_x() + bar.get_width() / 2,
            value + 0.02,
            f"{value * 100:.1f}%",
            ha="center",
            va="bottom",
            fontsize=11,
        )

    ax2 = axes[1]
    chart_labels = [FEATURE_LABELS.get(k, k) for k in feature_names]

    if hasattr(model, "feature_importances_"):
        importances = model.feature_importances_
        imp_colors = [
            "#1976D2" if imp < 0.1 else "#FF9800" if imp < 0.2 else "#E53935"
            for imp in importances
        ]
        bars2 = ax2.barh(chart_labels, importances, color=imp_colors)
        ax2.set_xlim(0, max(importances) * 1.3 if len(importances) else 1)
        ax2.set_xlabel("중요도")
        ax2.set_title("피처 중요도")
        ax2.invert_yaxis()
        for bar, imp in zip(bars2, importances):
            ax2.text(
                imp + 0.005,
                bar.get_y() + bar.get_height() / 2,
                f"{imp:.3f}",
                ha="left",
                va="center",
                fontsize=9,
            )
    else:
        input_vals = [input_values.get(k, 0.0) for k in feature_names]
        bar_colors = ["#1976D2" if v > 0 else "#9E9E9E" for v in input_vals]
        bars2 = ax2.barh(chart_labels, input_vals, color=bar_colors)
        ax2.set_xlabel("입력값(스케일)")
        ax2.set_title("입력 피처")
        ax2.invert_yaxis()
        for bar, val in zip(bars2, input_vals):
            ax2.text(
                val + (0.05 if val >= 0 else -0.05),
                bar.get_y() + bar.get_height() / 2,
                f"{val:.2f}",
                ha="left" if val >= 0 else "right",
                va="center",
                fontsize=9,
            )

    fig.tight_layout()

    buf = io.BytesIO()
    fig.savefig(buf, format="png", dpi=150)
    plt.close(fig)
    buf.seek(0)
    return base64.b64encode(buf.read()).decode("utf-8")


def _validate_ranges(user_provided: dict[str, float]) -> None:
    for key, value in user_provided.items():
        if key in FEATURE_RANGES:
            min_v, max_v = FEATURE_RANGES[key]
            if value < min_v or value > max_v:
                label = FEATURE_LABELS.get(key, key)
                raise HTTPException(
                    status_code=400,
                    detail=f"{label}({key}) 값은 {min_v:.2f} ~ {max_v:.2f} 범위여야 합니다.",
                )


def _risk_label(probability: float) -> str:
    low, high = get_band_thresholds()
    if probability < low:
        return "저위험군"
    if probability < high:
        return "중위험군"
    return "고위험군"


def predict_with_model(payload: PredictRequest) -> PredictResponse:
    raw_input: dict[str, float | None] = {
        "age": payload.age,
        "hypertension": payload.hypertension,
        "heart_disease": payload.heart_disease,
        "avg_glucose_level": payload.avg_glucose_level,
        "bmi": payload.bmi,
        "smoking_status": payload.smoking_status,
    }

    user_provided = {k: float(v) for k, v in raw_input.items() if v is not None}

    if not user_provided:
        raise HTTPException(status_code=400, detail="최소 1개 이상의 입력 항목이 필요합니다.")

    has_glucose = "avg_glucose_level" in user_provided
    feature_names = FEATURES_WITH_GLUCOSE if has_glucose else FEATURES_NO_GLUCOSE

    missing = [f for f in feature_names if f not in user_provided]
    if missing:
        labels = ", ".join(FEATURE_LABELS.get(m, m) for m in missing)
        raise HTTPException(status_code=400, detail=f"필수 입력값이 누락되었습니다: {labels}")

    _validate_ranges(user_provided)

    # 모델 교체 지점 6:
    # model_loader에서 불러온 모델 객체를 여기서 실제 추론에 사용합니다.
    # 모델 파일 교체 + 서버 재시작 시 자동으로 새 모델이 반영됩니다.
    model = MODEL_WITH_GLUCOSE if has_glucose else MODEL_NO_GLUCOSE
    used_model_name = "Stroke Model A (혈당 포함)" if has_glucose else "Stroke Model B (혈당 미포함)"

    x_values = [user_provided[f] for f in feature_names]
    x = np.array([x_values], dtype=float)

    proba = model.predict_proba(x)[0]
    probability = float(proba[1])
    threshold = get_model_threshold(with_glucose=has_glucose)
    prediction = int(probability >= threshold)
    label = _risk_label(probability)

    chart_image_base64: str | None = None
    try:
        chart_image_base64 = _create_chart_base64(
            probability,
            user_provided,
            model,
            feature_names,
        )
    except Exception:
        chart_image_base64 = None

    return PredictResponse(
        prediction=prediction,
        probability=round(probability, 4),
        label=label,
        input=user_provided,
        used_model=used_model_name,
        chart_image_base64=chart_image_base64,
    )
