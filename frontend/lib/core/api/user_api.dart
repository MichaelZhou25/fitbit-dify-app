import '../../shared/models/app_user.dart';
import '../../shared/models/timeline_segment.dart';
import '../../shared/models/user_profile_view_data.dart';
import 'api_client.dart';

class UserApi {
  const UserApi(this._client);

  final ApiClient _client;

  Future<AppUser> fetchBoundUser(String externalUserId) async {
    final response = await _client.dio.get(
      '/api/v1/users/by-external-id/$externalUserId',
    );
    return AppUser.fromJson(Map<String, dynamic>.from(response.data as Map));
  }

  Future<List<AppUser>> fetchUsers({int limit = 20}) async {
    final response = await _client.dio.get(
      '/api/v1/users',
      queryParameters: {'limit': limit, 'offset': 0},
    );
    final items = (response.data['items'] as List? ?? const []);
    return items
        .map((item) => AppUser.fromJson(Map<String, dynamic>.from(item as Map)))
        .toList();
  }

  Future<UserProfileViewData> fetchProfile(String userId) async {
    final response = await _client.dio.get('/api/v1/users/$userId/profile');
    return UserProfileViewData.fromJson(
      Map<String, dynamic>.from(response.data as Map),
    );
  }

  Future<List<TimelineSegment>> fetchTimeline(
    String userId, {
    int limit = 40,
  }) async {
    final response = await _client.dio.get(
      '/api/v1/users/$userId/timeline',
      queryParameters: {'limit': limit},
    );
    final items = (response.data['items'] as List? ?? const []);
    return items
        .map(
          (item) =>
              TimelineSegment.fromJson(Map<String, dynamic>.from(item as Map)),
        )
        .toList();
  }

  Future<UserProfileViewData> bootstrapProfile(String userId) async {
    final response = await _client.dio.post(
      '/api/v1/users/$userId/bootstrap-profile',
    );
    return UserProfileViewData.fromJson(
      Map<String, dynamic>.from(response.data as Map),
    );
  }
}
