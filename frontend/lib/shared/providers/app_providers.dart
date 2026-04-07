import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:dio/dio.dart';

import '../../core/api/api_client.dart';
import '../../core/api/import_api.dart';
import '../../core/api/segment_api.dart';
import '../../core/api/user_api.dart';
import '../../core/config/app_config.dart';
import '../models/app_user.dart';
import '../models/timeline_segment.dart';
import '../models/user_profile_view_data.dart';

class ActiveExternalUserIdNotifier extends Notifier<String?> {
  @override
  String? build() => null;

  void setExternalUserId(String? value) {
    state = value;
  }
}

final appConfigProvider = Provider<AppConfig>(
  (ref) => AppConfig.fromEnvironment(),
);

final apiClientProvider = Provider<ApiClient>((ref) {
  final config = ref.watch(appConfigProvider);
  return ApiClient(config.apiBaseUrl);
});

final userApiProvider = Provider<UserApi>(
  (ref) => UserApi(ref.watch(apiClientProvider)),
);
final segmentApiProvider = Provider<SegmentApi>(
  (ref) => SegmentApi(ref.watch(apiClientProvider)),
);
final importApiProvider = Provider<ImportApi>(
  (ref) => ImportApi(ref.watch(apiClientProvider)),
);

final activeExternalUserIdProvider =
    NotifierProvider<ActiveExternalUserIdNotifier, String?>(
      ActiveExternalUserIdNotifier.new,
    );

final currentUserProvider = FutureProvider<AppUser>((ref) async {
  final config = ref.watch(appConfigProvider);
  final overrideExternalUserId = ref.watch(activeExternalUserIdProvider);
  final userApi = ref.watch(userApiProvider);
  final targetExternalUserId = overrideExternalUserId ?? config.externalUserId;

  try {
    return await userApi.fetchBoundUser(targetExternalUserId);
  } on DioException catch (error) {
    if (error.response?.statusCode != 404) rethrow;
  }

  final users = await userApi.fetchUsers(limit: 1);
  if (users.isEmpty) {
    throw StateError('No imported users are available yet.');
  }
  return users.first;
});

final userProfileProvider = FutureProvider<UserProfileViewData>((ref) async {
  final user = await ref.watch(currentUserProvider.future);
  return ref.watch(userApiProvider).fetchProfile(user.id);
});

final timelineProvider = FutureProvider<List<TimelineSegment>>((ref) async {
  final user = await ref.watch(currentUserProvider.future);
  return ref.watch(userApiProvider).fetchTimeline(user.id);
});

final latestSegmentProvider = Provider<TimelineSegment?>((ref) {
  final timeline = ref.watch(timelineProvider);
  final data = timeline.asData?.value;
  return data != null && data.isNotEmpty ? data.first : null;
});
