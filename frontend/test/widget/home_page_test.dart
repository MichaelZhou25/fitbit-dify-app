import 'package:fitbit_frontend/features/home/home_page.dart';
import 'package:fitbit_frontend/shared/models/app_user.dart';
import 'package:fitbit_frontend/shared/models/timeline_segment.dart';
import 'package:fitbit_frontend/shared/providers/app_providers.dart';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';

void main() {
  testWidgets('HomePage shows empty state when no timeline data exists', (
    tester,
  ) async {
    await tester.pumpWidget(
      ProviderScope(
        overrides: [
          currentUserProvider.overrideWith(
            (ref) async => AppUser(
              id: 'user_1',
              externalUserId: 'fitbit_u001',
              timezone: 'Asia/Shanghai',
              createdAt: DateTime(2026, 4, 6),
            ),
          ),
          timelineProvider.overrideWith((ref) async => <TimelineSegment>[]),
        ],
        child: const MaterialApp(home: HomePage()),
      ),
    );

    await tester.pump();
    await tester.pump(const Duration(milliseconds: 100));

    expect(find.textContaining('还没有导入任何 Fitbit 数据'), findsOneWidget);
  });
}
