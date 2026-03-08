# `final_scenarios_confusion_matrix.ipynb` 요약

이 문서는 `fastapi/scripts/final_scenarios_confusion_matrix.ipynb`의 목적, 셀 구성, 차트 해석 방법을 빠르게 파악하기 위한 요약입니다.

## 1) 노트 목적

- 노트북 `testfinal4feautrenocheat.ipynb`의 마지막 `run_best_model_and_report` 로직을 재현
- 시나리오 A/B/C/C-NS에 대해:
  - 모델 탐색 근거(모델 순위, threshold 탐색, ROC/PR, 후보 confusion matrix)
  - 최종 결과(Train/Valid/Test confusion matrix + 지표)
  - 를 한 번에 확인

## 2) 시나리오 정의

- **A**: 상세/수치형, 혈당 포함 (`임신횟수`, `혈당`, `BMI`, `나이`)
- **B**: 상세/수치형, 혈당 미포함 (`임신횟수`, `BMI`, `나이`)
- **C**: 심플/등급형, 혈당 포함
- **C-NS**: 심플/등급형, 혈당 미포함

## 3) 공통 파이프라인

- 데이터: `/Users/cheng80/Desktop/diabetes_python/Data/당뇨.csv`
- 타깃: `당뇨`
- 0 -> NaN 처리 컬럼: `혈당`, `혈압`, `피부두께`, `인슐린`, `BMI`
- 분할: `train/valid/test = 0.6/0.2/0.2`, `random_state=42`, `stratify`

### 수치형(A/B) 전처리

- Train 기준 IQR clipping
- `StandardScaler` + `KNNImputer(n_neighbors=5)`

### 등급형(C/C-NS) 전처리

- Train 분위수(25/50/75%) 기준 1~4 등급화

### 모델 탐색

- 후보 8개: `LR`, `KNN`, `RF`, `GB`, `Ada`, `SVM`, `MLP`, `DT`
- Valid 성능 상위 3개로 `Voting Ensemble (Top 3 Mix)` 생성
- Winner 선택 후 threshold `0.30~0.69` 탐색으로 Valid Accuracy 최대값 채택

## 4) 셀 구성(무엇을 보는지)

- **상단 기본 셀**: 데이터 로드/전처리 함수/최종 confusion matrix 함수
- **Optimization Logs 섹션**
  - 모델 순위 바차트(Valid 기준)
  - threshold 탐색 곡선
  - ROC(AUC), PR(AP)
  - 후보(상위3 + winner) Valid confusion matrix
- **Final 섹션**
  - 시나리오별 Train/Valid/Test confusion matrix
  - 최종 winner/threshold/지표 요약표

## 5) 차트 해석 포인트

- **Model Ranking**: 어떤 모델이 Valid 기준 상위인지
- **Threshold Search**: 0.5 고정보다 더 나은 컷오프가 있는지
- **ROC/PR**: 클래스 불균형에서 분리력/정밀-재현 균형 확인
- **Candidate CM(Valid)**: winner와 상위 후보의 오분류 패턴 비교
- **Final CM(Train/Valid/Test)**:
  - Train만 높고 Test가 낮으면 과적합 의심
  - Test에서 FN(당뇨를 정상으로 놓침) 비율을 반드시 확인

## 6) 현재 기준 결과(앱 반영 메타와 일치)

`fastapi/app/model_scenarios_meta.json` 기준:

- A: winner=`LR`, threshold=`0.50`, test acc=`0.7403`
- B: winner=`SVM`, threshold=`0.36`, test acc=`0.6753`
- C: winner=`Voting Ensemble (Top 3 Mix)`, threshold=`0.48`, test acc=`0.7273`
- C-NS: winner=`Voting Ensemble (Top 3 Mix)`, threshold=`0.38`, test acc=`0.6818`

## 7) 실행 방법

노트북에서 위에서 아래로 순서대로 실행하면 됩니다.

- 권장 커널: Python 3.10+ (현재 프로젝트 fastapi 환경과 동일 권장)
- 필요 패키지: `pandas`, `numpy`, `matplotlib`, `seaborn`, `scikit-learn`, `koreanize_matplotlib`

## 8) 주의사항

- 중간 실험 셀(노트 원본)과 최종 셀 결과는 다를 수 있음
- 이 노트는 **최종 셀 기준 로직**을 재현해 비교/설명 가능성을 높이는 목적
- 앱 반영은 `model_scenarios_meta.json`에 저장된 winner/threshold와 정합성을 유지해야 함
