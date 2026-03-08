from __future__ import annotations

import socket
from typing import Any

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from app.geocoding import geocoding
from app.predictor import predict_with_model
from app.schemas import GeocodeRequest, GeocodeResponse, PredictRequest, PredictResponse

app = FastAPI(title="Stroke Risk Prediction API", version="3.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def _get_local_ip() -> str:
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception:
        return "127.0.0.1"


@app.get("/health")
def health() -> dict[str, Any]:
    local_ip = _get_local_ip()
    return {
        "status": "ok",
        "model_with_glucose": "Stroke Model A (age, hypertension, heart_disease, avg_glucose_level, bmi, smoking_status)",
        "model_without_glucose": "Stroke Model B (age, hypertension, heart_disease, bmi, smoking_status)",
        "local_ip": local_ip,
        "suggested_url": f"http://{local_ip}:8000",
    }


@app.post("/predict", response_model=PredictResponse)
def predict(payload: PredictRequest) -> PredictResponse:
    return predict_with_model(payload)


@app.post("/geocode", response_model=GeocodeResponse)
def geocode_address(payload: GeocodeRequest) -> GeocodeResponse:
    result = geocoding(payload.address)
    if result is None:
        raise HTTPException(status_code=404, detail="주소를 찾을 수 없습니다.")
    return GeocodeResponse(lat=result["lat"], lng=result["lng"])
