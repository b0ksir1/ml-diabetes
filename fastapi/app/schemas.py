from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class PredictRequest(BaseModel):
    """Stroke risk request payload."""

    age: float | None = Field(None, alias="나이")
    bmi: float | None = Field(None, alias="BMI")
    avg_glucose_level: float | None = Field(None, alias="평균혈당")
    hypertension: float | None = Field(None, alias="고혈압")
    heart_disease: float | None = Field(None, alias="심장질환")
    smoking_status: float | None = Field(None, alias="흡연상태")
    input_mode: str | None = Field("detail", alias="입력모드")

    model_config = ConfigDict(populate_by_name=True)


class PredictResponse(BaseModel):
    prediction: int
    probability: float
    label: str
    input: dict[str, float]
    used_model: str
    chart_image_base64: str | None = None


class GeocodeRequest(BaseModel):
    address: str = Field(..., description="변환할 주소")


class GeocodeResponse(BaseModel):
    lat: str
    lng: str
