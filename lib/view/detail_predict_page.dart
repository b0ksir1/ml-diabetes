import 'dart:convert';

import 'package:diabetes_app/constants/diabetes_predict_mapping.dart';
import 'package:diabetes_app/models/predict_input_profile.dart';
import 'package:diabetes_app/utils/app_storage.dart';
import 'package:diabetes_app/utils/custom_common_util.dart';
import 'package:diabetes_app/view/address_search_page.dart';
import 'package:diabetes_app/view/hospital_search_page.dart';
import 'package:diabetes_app/widgets/age_picker.dart';
import 'package:diabetes_app/widgets/height_weight_picker.dart';
import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:http/http.dart' as http;

class DetailPredictPage extends StatefulWidget {
  const DetailPredictPage({super.key});

  @override
  State<DetailPredictPage> createState() => _DetailPredictPageState();
}

class _DetailPredictPageState extends State<DetailPredictPage> {
  double _bmi = 0;
  int _age = 30;
  int _heightCm = 170;
  int _weightKg = 70;

  bool _hasHypertension = false;
  bool _hasHeartDisease = false;
  String _smokingStatus = StrokePredictMapping.smokingOptions.first;

  final _glucoseCtrl = TextEditingController();
  VoidCallback? _unlistenProfile;

  @override
  void initState() {
    super.initState();
    _applyProfile(PredictInputProfile.load());
    _unlistenProfile = AppStorage.rawStorage.listenKey(
      PredictInputProfile.storageKey,
      (_) {
        if (!mounted) return;
        setState(() => _applyProfile(PredictInputProfile.load()));
      },
    );
  }

  @override
  void dispose() {
    _unlistenProfile?.call();
    _glucoseCtrl.dispose();
    super.dispose();
  }

  void _applyProfile(PredictInputProfile profile) {
    _age = profile.age;
    _heightCm = profile.heightCm;
    _weightKg = profile.weightKg;
    _bmi = profile.bmi;
  }

  Future<void> _saveProfile() {
    return PredictInputProfile(
      age: _age,
      heightCm: _heightCm,
      weightKg: _weightKg,
    ).save();
  }

  bool _isGlucoseOut() {
    final text = _glucoseCtrl.text.trim();
    if (text.isEmpty) return false;
    final v = double.tryParse(text);
    if (v == null) return true;
    return StrokePredictMapping.isGlucoseOutOfRange(v);
  }

  bool get _ok => _bmi > 0 && !_isGlucoseOut();

  Color _riskColor(String label) {
    if (label.contains('고위험')) return Colors.red.shade600;
    if (label.contains('중위험')) return Colors.orange.shade700;
    return Colors.green.shade600;
  }

  Future<void> _onPredict() async {
    CustomCommonUtil.showLoadingOverlay(
      context,
      message: '뇌졸중 위험도를 분석 중입니다...',
    );

    try {
      final url = '${CustomCommonUtil.getApiBaseUrlSync()}/predict';

      final body = {
        'input_mode': 'detail',
        'age': StrokePredictMapping.scaleAge(_age),
        'bmi': StrokePredictMapping.scaleBmi(_bmi),
        'hypertension': StrokePredictMapping.scaleHypertension(
          _hasHypertension,
        ),
        'heart_disease': StrokePredictMapping.scaleHeartDisease(
          _hasHeartDisease,
        ),
        'smoking_status': StrokePredictMapping.scaleSmoking(_smokingStatus),
      };

      if (_glucoseCtrl.text.trim().isNotEmpty) {
        body['avg_glucose_level'] = StrokePredictMapping.scaleGlucose(
          double.parse(_glucoseCtrl.text.trim()),
        );
      }

      final response = await http.post(
        Uri.parse(url),
        headers: {'Content-Type': 'application/json'},
        body: jsonEncode(body),
      );

      if (!mounted) return;
      CustomCommonUtil.hideLoadingOverlay(context);

      if (response.statusCode == 200) {
        final data = jsonDecode(utf8.decode(response.bodyBytes));
        _showResultDialog(data);
      } else {
        CustomCommonUtil.showErrorSnackbar(
          context: context,
          message: '예측 실패: 상태 코드 ${response.statusCode}',
        );
      }
    } catch (e) {
      if (!mounted) return;
      CustomCommonUtil.hideLoadingOverlay(context);
      CustomCommonUtil.logError(functionName: '_onPredict (Detail)', error: e);
      CustomCommonUtil.showErrorSnackbar(
        context: context,
        message: '서버 연결에 실패했습니다. 네트워크 상태를 확인해주세요.',
      );
    }
  }

  void _showResultDialog(Map<String, dynamic> data) {
    final label = data['label'] as String;
    final probability = (data['probability'] as double) * 100;
    final chartBase64 = data['chart_image_base64'] as String?;

    showModalBottomSheet(
      context: context,
      isScrollControlled: true,
      shape: const RoundedRectangleBorder(
        borderRadius: BorderRadius.vertical(top: Radius.circular(20)),
      ),
      builder: (context) {
        return DraggableScrollableSheet(
          initialChildSize: 0.9,
          minChildSize: 0.5,
          maxChildSize: 0.95,
          expand: false,
          builder: (context, scrollController) {
            return SafeArea(
              child: Column(
                children: [
                  const Padding(
                    padding: EdgeInsets.symmetric(vertical: 16),
                    child: Text(
                      '분석 결과',
                      style: TextStyle(
                        fontSize: 18,
                        fontWeight: FontWeight.bold,
                      ),
                    ),
                  ),
                  const Divider(height: 1),
                  Expanded(
                    child: ListView(
                      controller: scrollController,
                      padding: const EdgeInsets.all(20),
                      children: [
                        Text(
                          label,
                          textAlign: TextAlign.center,
                          style: TextStyle(
                            fontSize: 22,
                            fontWeight: FontWeight.bold,
                            color: _riskColor(label),
                          ),
                        ),
                        const SizedBox(height: 8),
                        Text(
                          '뇌졸중 위험 확률: ${probability.toStringAsFixed(1)}%',
                          textAlign: TextAlign.center,
                          style: const TextStyle(fontSize: 16),
                        ),
                        if (chartBase64 != null) ...[
                          const SizedBox(height: 24),
                          Image.memory(
                            base64Decode(chartBase64),
                            fit: BoxFit.contain,
                          ),
                        ],
                        const SizedBox(height: 24),
                        const Text(
                          '이 결과는 의료 진단이 아닌 참고용 위험도 정보입니다. 이상 징후가 있으면 의료진 상담을 권장합니다.',
                          textAlign: TextAlign.center,
                          style: TextStyle(fontSize: 13, color: Colors.grey),
                        ),
                      ],
                    ),
                  ),
                  const Divider(height: 1),
                  Padding(
                    padding: const EdgeInsets.all(16),
                    child: Row(
                      children: [
                        Expanded(
                          child: OutlinedButton(
                            onPressed: () => Navigator.pop(context),
                            child: const Text('확인'),
                          ),
                        ),
                        const SizedBox(width: 12),
                        Expanded(
                          child: FilledButton(
                            onPressed: () {
                              Navigator.pop(context);
                              final latStr = AppStorage.getLat();
                              final lngStr = AppStorage.getLng();

                              if (latStr != null && lngStr != null) {
                                final lat = double.tryParse(latStr) ?? 0.0;
                                final lng = double.tryParse(lngStr) ?? 0.0;
                                Navigator.push(
                                  context,
                                  MaterialPageRoute(
                                    builder: (context) =>
                                        HospitalSearchPage(lat: lat, lng: lng),
                                  ),
                                );
                              } else {
                                CustomCommonUtil.showErrorSnackbar(
                                  context: context,
                                  message: '저장된 주소가 없습니다. 주소를 먼저 설정해주세요.',
                                );
                                Navigator.push(
                                  context,
                                  MaterialPageRoute(
                                    builder: (context) =>
                                        const AddressSearchPage(),
                                  ),
                                );
                              }
                            },
                            child: const Text('주변 병원 찾기'),
                          ),
                        ),
                      ],
                    ),
                  ),
                ],
              ),
            );
          },
        );
      },
    );
  }

  @override
  Widget build(BuildContext context) {
    return GestureDetector(
      behavior: HitTestBehavior.translucent,
      onTap: () => FocusScope.of(context).unfocus(),
      child: SafeArea(
        child: SingleChildScrollView(
          keyboardDismissBehavior: ScrollViewKeyboardDismissBehavior.onDrag,
          padding: const EdgeInsets.all(20),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.stretch,
            spacing: 24,
            children: [
              Column(
                crossAxisAlignment: CrossAxisAlignment.stretch,
                spacing: 12,
                children: [
                  const Text('나이'),
                  AgePicker(
                    initialAge: _age,
                    onChanged: (age) {
                      setState(() => _age = age);
                      _saveProfile();
                    },
                  ),
                ],
              ),
              Column(
                crossAxisAlignment: CrossAxisAlignment.stretch,
                spacing: 12,
                children: [
                  const Text('키/몸무게 (BMI 자동 계산)'),
                  HeightWeightPicker(
                    initialHeight: _heightCm,
                    initialWeight: _weightKg,
                    onChanged: (height, weight, bmi) {
                      setState(() {
                        _heightCm = height;
                        _weightKg = weight;
                        _bmi = bmi;
                      });
                      _saveProfile();
                    },
                  ),
                ],
              ),
              SwitchListTile.adaptive(
                contentPadding: EdgeInsets.zero,
                title: const Text('고혈압 진단 경험'),
                value: _hasHypertension,
                onChanged: (v) => setState(() => _hasHypertension = v),
              ),
              SwitchListTile.adaptive(
                contentPadding: EdgeInsets.zero,
                title: const Text('심장질환 진단 경험'),
                value: _hasHeartDisease,
                onChanged: (v) => setState(() => _hasHeartDisease = v),
              ),
              DropdownButtonFormField<String>(
                value: _smokingStatus,
                decoration: const InputDecoration(labelText: '흡연 상태'),
                items: StrokePredictMapping.smokingOptions
                    .map(
                      (e) => DropdownMenuItem<String>(value: e, child: Text(e)),
                    )
                    .toList(),
                onChanged: (v) {
                  if (v == null) return;
                  setState(() => _smokingStatus = v);
                },
              ),
              Column(
                crossAxisAlignment: CrossAxisAlignment.stretch,
                spacing: 8,
                children: [
                  const Text('평균 혈당 (mg/dL, 선택)'),
                  TextFormField(
                    controller: _glucoseCtrl,
                    keyboardType: const TextInputType.numberWithOptions(
                      decimal: true,
                    ),
                    inputFormatters: [
                      FilteringTextInputFormatter.allow(RegExp(r'[0-9.]')),
                    ],
                    decoration: InputDecoration(
                      hintText:
                          '최소 ${StrokePredictMapping.glucoseMin}, 최대 ${StrokePredictMapping.glucoseMax}',
                      hintStyle: Theme.of(context).textTheme.bodySmall,
                      errorText:
                          _glucoseCtrl.text.trim().isNotEmpty && _isGlucoseOut()
                          ? '범위를 벗어났습니다 (${StrokePredictMapping.glucoseMin}~${StrokePredictMapping.glucoseMax})'
                          : null,
                      errorBorder: OutlineInputBorder(
                        borderSide: BorderSide(color: Colors.red.shade400),
                      ),
                      focusedErrorBorder: OutlineInputBorder(
                        borderSide: BorderSide(color: Colors.red.shade400),
                      ),
                      filled: true,
                      fillColor: Theme.of(
                        context,
                      ).colorScheme.surfaceContainerHighest,
                    ),
                    onChanged: (_) => setState(() {}),
                  ),
                  Text(
                    '평균 혈당을 모르면 비워둔 채로 예측할 수 있습니다.',
                    style:
                        (Theme.of(context).textTheme.bodySmall ??
                                const TextStyle())
                            .copyWith(color: Colors.red.shade400),
                  ),
                ],
              ),
              FilledButton(
                onPressed: _ok ? _onPredict : null,
                child: const Text('예측하기'),
              ),
            ],
          ),
        ),
      ),
    );
  }
}
