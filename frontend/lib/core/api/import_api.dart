import 'package:dio/dio.dart';

import '../../shared/models/import_result.dart';
import 'api_client.dart';

class ImportApi {
  const ImportApi(this._client);

  final ApiClient _client;

  Future<ImportResult> uploadFitbitArchive({
    required String fileName,
    required List<int> bytes,
    required String externalUserId,
    required String timezone,
    String? name,
  }) async {
    final formData = FormData.fromMap({
      'archive': MultipartFile.fromBytes(bytes, filename: fileName),
      'external_user_id': externalUserId,
      'timezone': timezone,
      if (name != null && name.trim().isNotEmpty) 'name': name.trim(),
    });
    final response = await _client.dio.post(
      '/api/v1/imports/fitbit',
      data: formData,
      options: Options(
        sendTimeout: const Duration(minutes: 5),
        receiveTimeout: const Duration(minutes: 10),
      ),
    );
    return ImportResult.fromJson(
      Map<String, dynamic>.from(response.data as Map),
    );
  }
}
