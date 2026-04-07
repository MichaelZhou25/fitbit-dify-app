import 'package:fitbit_frontend/shared/models/saved_analysis.dart';
import 'package:flutter_test/flutter_test.dart';

void main() {
  test('SavedAnalysis normalizes string and list advice', () {
    final listAnalysis = SavedAnalysis.fromJson({
      'segment_id': 'seg_1',
      'user_id': 'user_1',
      'model_output': const {},
      'llm_output': {
        'personalized_advice': ['Walk more today', 'Sleep earlier tonight'],
      },
      'status': 'sent',
    });

    final stringAnalysis = SavedAnalysis.fromJson({
      'segment_id': 'seg_1',
      'user_id': 'user_1',
      'model_output': const {},
      'llm_output': {
        'personalized_advice': '- Walk more today\n- Sleep earlier tonight',
      },
      'status': 'sent',
    });

    expect(listAnalysis.personalizedAdvice, [
      'Walk more today',
      'Sleep earlier tonight',
    ]);
    expect(stringAnalysis.personalizedAdvice, [
      'Walk more today',
      'Sleep earlier tonight',
    ]);
  });
}
