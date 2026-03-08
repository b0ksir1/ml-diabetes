# Legacy Diabetes Assets

이 폴더는 뇌졸중 전환 이전의 당뇨 모델/스크립트 보관용입니다.
현재 런타임(FastAPI)에서는 사용하지 않습니다.

## 폴더 구성
- app_artifacts/: 당뇨 모델/전처리 산출물(joblib/json)
- scripts/: 당뇨 학습/검증 노트북 및 스크립트

## 현재 사용 중(뇌졸중)
- fastapi/app/stroke_model_with_glucose.joblib
- fastapi/app/stroke_model_without_glucose.joblib
- fastapi/app/stroke_model_meta.json
- fastapi/scripts/train_stroke_models.py
