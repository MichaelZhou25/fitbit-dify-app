import 'package:dio/dio.dart';

import '../../shared/models/saved_analysis.dart';
import '../../shared/models/segment_detail.dart';
import 'api_client.dart';

class SegmentApi {
  const SegmentApi(this._client);

  final ApiClient _client;

  Future<SegmentDetail> fetchSegmentDetail(String segmentId) async {
    final detailResponse = await _client.dio.get('/api/v1/segments/$segmentId');
    final savedAnalysis = await fetchLatestAnalysis(segmentId);
    return SegmentDetail.fromJson(
      Map<String, dynamic>.from(detailResponse.data as Map),
      savedAnalysis: savedAnalysis,
    );
  }

  Future<SavedAnalysis?> fetchLatestAnalysis(String segmentId) async {
    try {
      final response = await _client.dio.get(
        '/api/v1/segments/$segmentId/latest-analysis',
      );
      return SavedAnalysis.fromJson(
        Map<String, dynamic>.from(response.data as Map),
      );
    } on DioException catch (error) {
      if (error.response?.statusCode == 404) {
        return null;
      }
      rethrow;
    }
  }

  Future<SavedAnalysis> analyzeSegment(
    String segmentId, {
    String? userQuery,
  }) async {
    final response = await _client.dio.post(
      '/api/v1/segments/$segmentId/analyze',
      data: {'user_query': userQuery ?? '请解释这一段 Fitbit 数据，并给出个性化建议。'},
    );
    return SavedAnalysis.fromJson(
      Map<String, dynamic>.from(response.data as Map),
    );
  }
}
