import 'package:fitbit_frontend/shared/models/import_result.dart';
import 'package:flutter_test/flutter_test.dart';

void main() {
  test('ImportResult parses summary fields', () {
    final result = ImportResult.fromJson({
      'mode': 'fitbit_export',
      'affected_external_user_ids': ['fitbit_u001'],
      'generated_segments': 12,
      'inserted_segments': 10,
      'inserted_users': 1,
      'skipped_existing': 2,
      'discovered_sources': 3,
      'processed_sources': 3,
      'skipped_sources': 0,
      'metrics_detected': {'steps': 1},
      'warnings': ['demo warning'],
    });

    expect(result.mode, 'fitbit_export');
    expect(result.generatedSegments, 12);
    expect(result.affectedExternalUserIds, ['fitbit_u001']);
    expect(result.warnings, ['demo warning']);
  });
}
