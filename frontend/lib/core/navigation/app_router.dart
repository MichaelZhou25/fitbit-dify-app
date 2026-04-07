import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../../features/history/history_page.dart';
import '../../features/history/segment_detail_page.dart';
import '../../features/home/home_page.dart';
import '../../features/imports/import_page.dart';
import '../../features/profile/profile_page.dart';
import '../../shared/widgets/app_shell.dart';

final goRouterProvider = Provider<GoRouter>((ref) {
  return GoRouter(
    routes: [
      ShellRoute(
        builder: (context, state, child) => AppShell(child: child),
        routes: [
          GoRoute(path: '/', builder: (context, state) => const HomePage()),
          GoRoute(
            path: '/history',
            builder: (context, state) => const HistoryPage(),
            routes: [
              GoRoute(
                path: ':segmentId',
                builder: (context, state) => SegmentDetailPage(
                  segmentId: state.pathParameters['segmentId']!,
                ),
              ),
            ],
          ),
          GoRoute(
            path: '/profile',
            builder: (context, state) => const ProfilePage(),
          ),
          GoRoute(
            path: '/import',
            builder: (context, state) => const ImportPage(),
          ),
        ],
      ),
    ],
  );
});
