import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import 'package:intl/intl.dart';

import '../../shared/providers/app_providers.dart';
import '../../shared/widgets/async_value_builder.dart';

class HistoryPage extends ConsumerWidget {
  const HistoryPage({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final timelineValue = ref.watch(timelineProvider);
    return AsyncValueBuilder(
      value: timelineValue,
      loadingLabel: '正在加载历史时间线...',
      builder: (timeline) {
        if (timeline.isEmpty) {
          return const Center(child: Text('当前还没有历史 segment。'));
        }
        final formatter = DateFormat('yyyy-MM-dd HH:mm');
        return ListView.separated(
          padding: const EdgeInsets.all(20),
          itemBuilder: (context, index) {
            final item = timeline[index];
            return Card(
              child: ListTile(
                title: Text(formatter.format(item.segmentStart)),
                subtitle: Text(
                  '${formatter.format(item.segmentEnd)} · ${item.granularity}',
                ),
                trailing: Chip(label: Text(item.topLabel ?? '尚未预测')),
                onTap: () => context.go('/history/${item.segmentId}'),
              ),
            );
          },
          separatorBuilder: (context, index) => const SizedBox(height: 10),
          itemCount: timeline.length,
        );
      },
    );
  }
}
