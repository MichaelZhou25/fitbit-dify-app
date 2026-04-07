import 'saved_analysis.dart';

class SegmentDetail {
  const SegmentDetail({
    required this.id,
    required this.userId,
    required this.segmentStart,
    required this.segmentEnd,
    required this.granularity,
    required this.sourceType,
    required this.rawPayload,
    required this.predictions,
    this.savedAnalysis,
  });

  final String id;
  final String userId;
  final DateTime segmentStart;
  final DateTime segmentEnd;
  final String granularity;
  final String sourceType;
  final Map<String, dynamic> rawPayload;
  final List<Map<String, dynamic>> predictions;
  final SavedAnalysis? savedAnalysis;

  factory SegmentDetail.fromJson(
    Map<String, dynamic> json, {
    SavedAnalysis? savedAnalysis,
  }) {
    return SegmentDetail(
      id: json['id'] as String,
      userId: json['user_id'] as String,
      segmentStart: DateTime.parse(json['segment_start'] as String),
      segmentEnd: DateTime.parse(json['segment_end'] as String),
      granularity: json['granularity'] as String? ?? '1h',
      sourceType: json['source_type'] as String? ?? 'fitbit_export',
      rawPayload: Map<String, dynamic>.from(
        json['raw_payload_json'] as Map? ?? const {},
      ),
      predictions: (json['predictions'] as List? ?? const [])
          .map((item) => Map<String, dynamic>.from(item as Map))
          .toList(),
      savedAnalysis: savedAnalysis,
    );
  }
}
