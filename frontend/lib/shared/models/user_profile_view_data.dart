class UserProfileViewData {
  const UserProfileViewData({
    required this.id,
    required this.userId,
    required this.profile,
    required this.goals,
    required this.thresholds,
    required this.baselineStats,
    required this.systemPromptPrefix,
    this.updatedAt,
  });

  final String id;
  final String userId;
  final Map<String, dynamic> profile;
  final Map<String, dynamic> goals;
  final Map<String, dynamic> thresholds;
  final Map<String, dynamic> baselineStats;
  final String systemPromptPrefix;
  final DateTime? updatedAt;

  bool get isMeaningful =>
      profile.isNotEmpty ||
      goals.isNotEmpty ||
      thresholds.isNotEmpty ||
      baselineStats.isNotEmpty ||
      systemPromptPrefix.trim().isNotEmpty;

  factory UserProfileViewData.fromJson(Map<String, dynamic> json) {
    return UserProfileViewData(
      id: json['id'] as String,
      userId: json['user_id'] as String,
      profile: Map<String, dynamic>.from(
        json['profile_json'] as Map? ?? const {},
      ),
      goals: Map<String, dynamic>.from(json['goals_json'] as Map? ?? const {}),
      thresholds: Map<String, dynamic>.from(
        json['thresholds_json'] as Map? ?? const {},
      ),
      baselineStats: Map<String, dynamic>.from(
        json['baseline_stats_json'] as Map? ?? const {},
      ),
      systemPromptPrefix: json['system_prompt_prefix'] as String? ?? '',
      updatedAt: json['updated_at'] == null
          ? null
          : DateTime.parse(json['updated_at'] as String),
    );
  }
}
