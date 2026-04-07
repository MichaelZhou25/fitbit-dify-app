class ImportResult {
  const ImportResult({
    required this.mode,
    required this.affectedExternalUserIds,
    required this.generatedSegments,
    required this.insertedSegments,
    required this.insertedUsers,
    required this.skippedExisting,
    required this.discoveredSources,
    required this.processedSources,
    required this.skippedSources,
    required this.metricsDetected,
    required this.warnings,
  });

  final String mode;
  final List<String> affectedExternalUserIds;
  final int generatedSegments;
  final int insertedSegments;
  final int insertedUsers;
  final int skippedExisting;
  final int discoveredSources;
  final int processedSources;
  final int skippedSources;
  final Map<String, dynamic> metricsDetected;
  final List<String> warnings;

  factory ImportResult.fromJson(Map<String, dynamic> json) {
    return ImportResult(
      mode: json['mode'] as String? ?? 'fitbit_export',
      affectedExternalUserIds:
          (json['affected_external_user_ids'] as List? ?? const [])
              .whereType<String>()
              .toList(),
      generatedSegments: json['generated_segments'] as int? ?? 0,
      insertedSegments: json['inserted_segments'] as int? ?? 0,
      insertedUsers: json['inserted_users'] as int? ?? 0,
      skippedExisting: json['skipped_existing'] as int? ?? 0,
      discoveredSources: json['discovered_sources'] as int? ?? 0,
      processedSources: json['processed_sources'] as int? ?? 0,
      skippedSources: json['skipped_sources'] as int? ?? 0,
      metricsDetected: Map<String, dynamic>.from(
        json['metrics_detected'] as Map? ?? const {},
      ),
      warnings: (json['warnings'] as List? ?? const [])
          .whereType<String>()
          .toList(),
    );
  }
}
