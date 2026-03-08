class StrokePredictMapping {
  // Approximate scaler stats for user-friendly raw input -> scaled feature space.
  // The backend models are trained on scaled stroke dataset columns.
  static const double _ageMean = 43.2266;
  static const double _ageStd = 22.6126;
  static const double _bmiMean = 28.8932;
  static const double _bmiStd = 7.8541;
  static const double _glucoseMean = 106.1477;
  static const double _glucoseStd = 45.2836;

  static const int glucoseMin = 55;
  static const int glucoseMax = 207;

  static const List<(int, int)> glucoseRanges = [
    (55, 90),
    (91, 120),
    (121, 160),
    (161, 207),
  ];

  static const List<String> smokingOptions = [
    'never smoked',
    'Unknown',
    'formerly smoked',
    'smokes',
  ];

  // Encoded/scaled constants from the provided stroke datasets.
  static const Map<String, double> _smokingToScaled = {
    'never smoked': -1.0320923658581076,
    'Unknown': -0.0956320042965032,
    'formerly smoked': 0.8408283572651013,
    'smokes': 1.7772887188267057,
  };

  static const double _hypertensionNo = -0.3183229500664172;
  static const double _hypertensionYes = 3.1414637235277976;
  static const double _heartDiseaseNo = -0.2483056542979963;
  static const double _heartDiseaseYes = 4.02729451661975;

  static double scaleAge(num age) => (age - _ageMean) / _ageStd;
  static double scaleBmi(num bmi) => (bmi - _bmiMean) / _bmiStd;
  static double scaleGlucose(num glucose) =>
      (glucose - _glucoseMean) / _glucoseStd;

  static double scaleHypertension(bool hasHypertension) {
    return hasHypertension ? _hypertensionYes : _hypertensionNo;
  }

  static double scaleHeartDisease(bool hasHeartDisease) {
    return hasHeartDisease ? _heartDiseaseYes : _heartDiseaseNo;
  }

  static double scaleSmoking(String smokingStatus) {
    return _smokingToScaled[smokingStatus] ?? _smokingToScaled['Unknown']!;
  }

  static bool isGlucoseOutOfRange(num glucose) {
    return glucose < glucoseMin || glucose > glucoseMax;
  }
}
