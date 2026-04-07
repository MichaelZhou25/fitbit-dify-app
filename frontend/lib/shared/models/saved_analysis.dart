class SavedAnalysis {
  const SavedAnalysis({
    required this.segmentId,
    required this.userId,
    required this.modelOutput,
    required this.llmOutput,
    required this.status,
    this.createdAt,
    this.workflowRunId,
  });

  final String segmentId;
  final String userId;
  final Map<String, dynamic> modelOutput;
  final Map<String, dynamic> llmOutput;
  final String status;
  final DateTime? createdAt;
  final String? workflowRunId;

  List<String> get personalizedAdvice {
    final value = llmOutput['personalized_advice'];
    if (value is List) {
      return value
          .whereType<String>()
          .map((item) => item.trim())
          .where((item) => item.isNotEmpty)
          .toList();
    }
    if (value is String) {
      return value
          .split(RegExp(r'\r?\n+'))
          .map((item) => item.replaceFirst(RegExp(r'^\s*[-*]\s*'), '').trim())
          .where((item) => item.isNotEmpty)
          .toList();
    }
    return const [];
  }

  factory SavedAnalysis.fromJson(Map<String, dynamic> json) {
    return SavedAnalysis(
      segmentId: json['segment_id'] as String,
      userId: json['user_id'] as String,
      modelOutput: Map<String, dynamic>.from(
        json['model_output'] as Map? ?? const {},
      ),
      llmOutput: Map<String, dynamic>.from(
        json['llm_output'] as Map? ?? const {},
      ),
      status: json['status'] as String? ?? 'unknown',
      createdAt: json['created_at'] == null
          ? null
          : DateTime.parse(json['created_at'] as String),
      workflowRunId: json['workflow_run_id'] as String?,
    );
  }
}
