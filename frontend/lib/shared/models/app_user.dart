class AppUser {
  const AppUser({
    required this.id,
    required this.externalUserId,
    required this.timezone,
    required this.createdAt,
    this.name,
  });

  final String id;
  final String externalUserId;
  final String timezone;
  final DateTime createdAt;
  final String? name;

  factory AppUser.fromJson(Map<String, dynamic> json) {
    return AppUser(
      id: json['id'] as String,
      externalUserId: json['external_user_id'] as String,
      timezone: json['timezone'] as String? ?? 'Asia/Shanghai',
      createdAt: DateTime.parse(json['created_at'] as String),
      name: json['name'] as String?,
    );
  }
}
