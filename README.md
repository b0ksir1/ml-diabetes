# 뇌졸중 위험도 예측 앱

Flutter + FastAPI 기반의 뇌졸중 위험도 예측 앱입니다.  
사용자가 건강 정보를 입력하면 ML 모델이 위험 확률을 계산하고, 저장한 주소 기준으로 주변 병원을 안내합니다.

## 현재 상태
- 앱 주제: 당뇨 -> 뇌졸중으로 전환 완료
- 예측 결과 라벨: `저위험군 / 중위험군 / 고위험군`
- 모델: 혈당 입력 유무에 따라 2개 모델 자동 분기
  - `Stroke Model A`: 혈당 포함
  - `Stroke Model B`: 혈당 미포함

## 핵심 기능
1. 심플 예측
- 나이, BMI, 고혈압, 심장질환, 흡연상태, (선택) 평균 혈당 입력
- 빠른 3단계 위험군 분류

2. 상세 예측
- 평균 혈당을 직접 수치로 입력 가능 (선택)
- 입력값 검증 후 예측 수행

3. 병원 검색/길찾기
- 저장 주소 -> 좌표 변환
- 좌표 기반 주변 병원 조회
- 카카오맵/네이버지도/애플맵/구글맵 연동

## 모델 상세
현재 앱은 `LogisticRegression` 기반 모델 2개를 사용합니다.

1. 혈당 포함 모델 (`Stroke Model A`)
- 파일: `fastapi/app/stroke_model_with_glucose.joblib`
- 입력 피처: `age`, `hypertension`, `heart_disease`, `avg_glucose_level`, `bmi`, `smoking_status`
- 이진 분류 임계값: `0.78`
- Test 성능: Accuracy `0.8796`, Recall `0.6000`, F1 `0.3279`, ROC-AUC `0.8377`

2. 혈당 미포함 모델 (`Stroke Model B`)
- 파일: `fastapi/app/stroke_model_without_glucose.joblib`
- 입력 피처: `age`, `hypertension`, `heart_disease`, `bmi`, `smoking_status`
- 이진 분류 임계값: `0.845`
- Test 성능: Accuracy `0.9129`, Recall `0.4000`, F1 `0.3101`, ROC-AUC `0.8358`

공통 위험군 라벨(3단계):
- `저위험군`: probability < `0.33`
- `중위험군`: `0.33` <= probability < `0.66`
- `고위험군`: probability >= `0.66`

모델/임계값 메타 정보는 `fastapi/app/stroke_model_meta.json`에 저장됩니다.

## 심플/상세 예측 동작
1. 심플 뇌졸중 예측
- 입력 UI: 나이, 키/몸무게(BMI), 고혈압 여부, 심장질환 여부, 흡연 상태, 평균 혈당(선택/구간)
- 평균 혈당을 선택하면 `Stroke Model A` 사용
- 평균 혈당을 비우면 `Stroke Model B` 사용
- 빠른 입력을 위한 화면이며, 혈당은 구간값의 대표값으로 변환 후 예측

2. 상세 뇌졸중 예측
- 입력 UI: 나이, 키/몸무게(BMI), 고혈압 여부, 심장질환 여부, 흡연 상태, 평균 혈당(선택/직접 수치)
- 평균 혈당을 직접 수치로 넣고 싶을 때 사용
- 모델 선택 규칙은 심플과 동일 (혈당 입력 시 A, 미입력 시 B)

3. 공통 처리
- Flutter에서 사용자 친화 입력값을 모델 입력 스케일로 변환
- FastAPI `/predict`에서 입력 범위 검증
- 확률 계산 후:
  - 이진 예측(`prediction`): 모델별 임계값(0.78 / 0.845) 적용
  - 3단계 라벨(`label`): 저/중/고위험군 기준(0.33 / 0.66) 적용
- 결과 화면에 확률 바 차트 + 입력 피처 차트(Base64 이미지) 제공

## 기술 스택
- Frontend: Flutter (Dart)
- Backend: FastAPI (Python)
- ML: scikit-learn (LogisticRegression)
- Geocoding: geopy (Nominatim)
- Hospital API: 공공데이터포털 응급의료 API
- Local Storage: GetStorage

## 프로젝트 구조
```text
ml-diabetes/
├─ lib/
│  ├─ main.dart
│  ├─ config.dart
│  ├─ constants/diabetes_predict_mapping.dart
│  ├─ view/
│  │  ├─ main_tab_page.dart
│  │  ├─ simple_predict_page.dart
│  │  ├─ detail_predict_page.dart
│  │  ├─ address_search_page.dart
│  │  └─ hospital_search_page.dart
│  └─ ...
├─ fastapi/
│  ├─ app/
│  │  ├─ main.py
│  │  ├─ schemas.py
│  │  ├─ predictor.py
│  │  ├─ model_loader.py
│  │  ├─ stroke_model_with_glucose.joblib
│  │  ├─ stroke_model_without_glucose.joblib
│  │  └─ stroke_model_meta.json
│  ├─ scripts/
│  │  └─ train_stroke_models.py
│  ├─ requirements.txt
│  └─ APIGUIDE.md
└─ pubspec.yaml
```

## 시작 방법
### 0) 사전 준비
- Flutter SDK 설치
- Python 3.10+ 설치
- 이 저장소 루트에서 작업

### 1) FastAPI 백엔드 실행
```powershell
cd fastapi
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

#### (선택) 뇌졸중 모델 재학습
이미 학습된 모델 파일이 `fastapi/app`에 있으면 생략 가능합니다.

사용자 데이터셋 경로가 아래와 같다면:
- `c:\Users\User_KO\Documents\WorkSpace\Python\project_brain\data\stroke_train_smote.csv`
- `c:\Users\User_KO\Documents\WorkSpace\Python\project_brain\data\stroke_valid.csv`
- `c:\Users\User_KO\Documents\WorkSpace\Python\project_brain\data\stroke_test.csv`

```powershell
python scripts\train_stroke_models.py `
  --train "c:\Users\User_KO\Documents\WorkSpace\Python\project_brain\data\stroke_train_smote.csv" `
  --valid "c:\Users\User_KO\Documents\WorkSpace\Python\project_brain\data\stroke_valid.csv" `
  --test "c:\Users\User_KO\Documents\WorkSpace\Python\project_brain\data\stroke_test.csv"
```

#### 서버 실행
```powershell
python -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

확인 URL:
- Swagger: `http://localhost:8000/docs`
- Health: `http://localhost:8000/health`

### 2) Flutter 앱 실행
다른 터미널(저장소 루트):
```powershell
flutter pub get
flutter run
```

### 3) 실기기 테스트 시 API 주소 설정
- 앱 좌측 메뉴(설정)에서 API URL을 PC IP로 설정
- 예: `http://192.168.0.15:8000`
- `/health` 응답의 `suggested_url` 값 사용 가능

## API 요약
- `GET /health`: 서버 상태/모델 정보
- `POST /predict`: 뇌졸중 위험도 예측
- `POST /geocode`: 주소 -> 좌표 변환

자세한 요청/응답 스키마는 [fastapi/APIGUIDE.md](fastapi/APIGUIDE.md) 참고.

## 주의사항
- 현재 앱 패키지명은 `diabetes_app`으로 남아있습니다(코드 동작에는 문제 없음).
- 예측 결과는 의료 진단이 아닌 참고용 위험도입니다.
