# Stroke FastAPI API Guide

Flutter 앱과 통신하는 FastAPI 백엔드 명세입니다.

## 실행
```powershell
cd fastapi
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
python -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

문서 확인:
- Swagger: `http://localhost:8000/docs`

## Endpoints

### 1) GET /health
서버 상태와 모델 로드 상태를 확인합니다.

응답 예시:
```json
{
  "status": "ok",
  "model_with_glucose": "Stroke Model A (age, hypertension, heart_disease, avg_glucose_level, bmi, smoking_status)",
  "model_without_glucose": "Stroke Model B (age, hypertension, heart_disease, bmi, smoking_status)",
  "local_ip": "192.168.0.15",
  "suggested_url": "http://192.168.0.15:8000"
}
```

### 2) POST /predict
뇌졸중 위험 확률을 계산합니다.

요청 스키마 (`PredictRequest`):
- `age: float` (스케일된 값)
- `bmi: float` (스케일된 값)
- `avg_glucose_level: float | null` (스케일된 값, 선택)
- `hypertension: float` (인코딩/스케일된 값)
- `heart_disease: float` (인코딩/스케일된 값)
- `smoking_status: float` (인코딩/스케일된 값)
- `input_mode: string | null` (`detail` 또는 `simple`, 현재 로직상 참고 필드)

요청 예시(혈당 포함):
```json
{
  "input_mode": "detail",
  "age": 1.62,
  "bmi": -0.93,
  "avg_glucose_level": -0.19,
  "hypertension": -0.3183,
  "heart_disease": -0.2483,
  "smoking_status": 0.8408
}
```

요청 예시(혈당 미포함):
```json
{
  "input_mode": "simple",
  "age": 0.15,
  "bmi": -0.10,
  "hypertension": -0.3183,
  "heart_disease": -0.2483,
  "smoking_status": -0.0956
}
```

응답 예시:
```json
{
  "prediction": 1,
  "probability": 0.8636,
  "label": "고위험군",
  "input": {
    "age": 1.623,
    "hypertension": -0.3183,
    "heart_disease": -0.2483,
    "avg_glucose_level": -0.188,
    "bmi": -0.928,
    "smoking_status": 0.8408
  },
  "used_model": "Stroke Model A (혈당 포함)",
  "chart_image_base64": "iVBORw0KGgoAAA..."
}
```

분기 규칙:
- `avg_glucose_level` 포함 -> `Stroke Model A (혈당 포함)`
- `avg_glucose_level` 미포함 -> `Stroke Model B (혈당 미포함)`

위험군 라벨 규칙:
- `저위험군`, `중위험군`, `고위험군`
- 기준값은 `fastapi/app/stroke_model_meta.json`의 `band_thresholds`

오류:
- `400`: 필수 입력 누락, 범위 오류

### 3) POST /geocode
주소를 위도/경도로 변환합니다.

요청:
```json
{ "address": "서울시 강남구 테헤란로 212" }
```

응답:
```json
{ "lat": "37.501", "lng": "127.039" }
```

오류:
- `404`: 주소 변환 실패

## 모델 아티팩트
`fastapi/app`:
- `stroke_model_with_glucose.joblib`
- `stroke_model_without_glucose.joblib`
- `stroke_model_meta.json`

## 재학습
```powershell
cd fastapi
python scripts\train_stroke_models.py `
  --train "<train_csv_path>" `
  --valid "<valid_csv_path>" `
  --test "<test_csv_path>"
```

학습 결과:
- 모델 2개와 메타 파일이 `fastapi/app`에 저장됩니다.
