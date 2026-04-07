class AppConfig {
  const AppConfig({
    required this.apiBaseUrl,
    required this.externalUserId,
    required this.defaultTimezone,
  });

  final String apiBaseUrl;
  final String externalUserId;
  final String defaultTimezone;

  factory AppConfig.fromEnvironment() {
    return const AppConfig(
      apiBaseUrl: String.fromEnvironment(
        'API_BASE_URL',
        defaultValue: 'http://127.0.0.1:8000',
      ),
      externalUserId: String.fromEnvironment(
        'FITBIT_EXTERNAL_USER_ID',
        defaultValue: 'fitbit_u001',
      ),
      defaultTimezone: String.fromEnvironment(
        'FITBIT_DEFAULT_TIMEZONE',
        defaultValue: 'Asia/Shanghai',
      ),
    );
  }
}
