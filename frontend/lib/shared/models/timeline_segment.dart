class TimelineSegment {
  const TimelineSegment({
    required this.segmentId,
    required this.segmentStart,
    required this.segmentEnd,
    required this.granularity,
    this.topLabel,
    this.probabilities,
  });

  final String segmentId;
  final DateTime segmentStart;
  final DateTime segmentEnd;
  final String granularity;
  final String? topLabel;
  final Map<String, dynamic>? probabilities;

  factory TimelineSegment.fromJson(Map<String, dynamic> json) {
    return TimelineSegment(
      segmentId: json['segment_id'] as String,
      segmentStart: DateTime.parse(json['segment_start'] as String),
      segmentEnd: DateTime.parse(json['segment_end'] as String),
      granularity: json['granularity'] as String? ?? '1h',
      topLabel: json['top_label'] as String?,
      probabilities: json['probabilities'] == null
          ? null
          : Map<String, dynamic>.from(json['probabilities'] as Map),
    );
  }
}
