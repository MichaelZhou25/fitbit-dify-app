import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import 'package:intl/intl.dart';

import '../../shared/models/saved_analysis.dart';
import '../../shared/providers/app_providers.dart';
import '../../shared/widgets/async_value_builder.dart';

final latestAnalysisProvider = FutureProvider.family<SavedAnalysis?, String>((
  ref,
  segmentId,
) {
  return ref.watch(segmentApiProvider).fetchLatestAnalysis(segmentId);
});

class HomePage extends ConsumerStatefulWidget {
  const HomePage({super.key});

  @override
  ConsumerState<HomePage> createState() => _HomePageState();
}

class _HomePageState extends ConsumerState<HomePage> {
  bool _isAnalyzing = false;

  @override
  Widget build(BuildContext context) {
    final userValue = ref.watch(currentUserProvider);
    final timelineValue = ref.watch(timelineProvider);

    return AsyncValueBuilder(
      value: userValue,
      builder: (user) => AsyncValueBuilder(
        value: timelineValue,
        loadingLabel: '正在加载最近数据...',
        builder: (timeline) {
          if (timeline.isEmpty) {
            return const Center(
              child: Padding(
                padding: EdgeInsets.all(24),
                child: Text('当前绑定用户还没有导入任何 Fitbit 数据。'),
              ),
            );
          }

          final latestSegment = timeline.first;
          final latestAnalysisValue = ref.watch(
            latestAnalysisProvider(latestSegment.segmentId),
          );

          return RefreshIndicator(
            onRefresh: () async {
              ref.invalidate(timelineProvider);
              ref.invalidate(userProfileProvider);
              ref.invalidate(latestAnalysisProvider(latestSegment.segmentId));
            },
            child: ListView(
              padding: const EdgeInsets.all(20),
              children: [
                Card(
                  child: Padding(
                    padding: const EdgeInsets.all(20),
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Text(
                          user.name?.trim().isNotEmpty == true
                              ? user.name!
                              : user.externalUserId,
                          style: Theme.of(context).textTheme.headlineSmall,
                        ),
                        const SizedBox(height: 8),
                        Text(
                          '最新时间段：${_formatRange(latestSegment.segmentStart, latestSegment.segmentEnd)}',
                        ),
                        const SizedBox(height: 8),
                        Wrap(
                          spacing: 8,
                          runSpacing: 8,
                          children: [
                            Chip(
                              label: Text(
                                '预测标签：${latestSegment.topLabel ?? '尚未预测'}',
                              ),
                            ),
                            Chip(label: Text('时区：${user.timezone}')),
                            Chip(
                              label: Text('粒度：${latestSegment.granularity}'),
                            ),
                          ],
                        ),
                        const SizedBox(height: 16),
                        FilledButton.icon(
                          onPressed: _isAnalyzing
                              ? null
                              : () => _analyzeLatestSegment(
                                  latestSegment.segmentId,
                                ),
                          icon: _isAnalyzing
                              ? const SizedBox.square(
                                  dimension: 16,
                                  child: CircularProgressIndicator(
                                    strokeWidth: 2,
                                  ),
                                )
                              : const Icon(Icons.auto_awesome_rounded),
                          label: const Text('重新分析最新一段'),
                        ),
                      ],
                    ),
                  ),
                ),
                const SizedBox(height: 16),
                Card(
                  child: Padding(
                    padding: const EdgeInsets.all(20),
                    child: latestAnalysisValue.when(
                      data: (analysis) => analysis == null
                          ? const Text('这段数据还没有保存的分析结果。')
                          : _AnalysisSummaryCard(
                              analysis: analysis,
                              onOpenHistory: () => context.go(
                                '/history/${latestSegment.segmentId}',
                              ),
                            ),
                      loading: () =>
                          const Center(child: CircularProgressIndicator()),
                      error: (error, _) => Text('读取分析结果失败：$error'),
                    ),
                  ),
                ),
              ],
            ),
          );
        },
      ),
    );
  }

  Future<void> _analyzeLatestSegment(String segmentId) async {
    setState(() => _isAnalyzing = true);
    try {
      await ref.read(segmentApiProvider).analyzeSegment(segmentId);
      ref.invalidate(latestAnalysisProvider(segmentId));
      ref.invalidate(timelineProvider);
      if (mounted) {
        ScaffoldMessenger.of(
          context,
        ).showSnackBar(const SnackBar(content: Text('分析完成，首页已刷新。')));
      }
    } catch (error) {
      if (mounted) {
        ScaffoldMessenger.of(
          context,
        ).showSnackBar(SnackBar(content: Text('分析失败：$error')));
      }
    } finally {
      if (mounted) {
        setState(() => _isAnalyzing = false);
      }
    }
  }

  String _formatRange(DateTime start, DateTime end) {
    final formatter = DateFormat('MM-dd HH:mm');
    return '${formatter.format(start)} - ${formatter.format(end)}';
  }
}

class _AnalysisSummaryCard extends StatelessWidget {
  const _AnalysisSummaryCard({
    required this.analysis,
    required this.onOpenHistory,
  });

  final SavedAnalysis analysis;
  final VoidCallback onOpenHistory;

  @override
  Widget build(BuildContext context) {
    final advice = analysis.personalizedAdvice;
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Row(
          children: [
            Chip(label: Text('状态：${analysis.status}')),
            const Spacer(),
            TextButton(onPressed: onOpenHistory, child: const Text('查看详情')),
          ],
        ),
        const SizedBox(height: 12),
        Text(
          analysis.llmOutput['summary'] as String? ?? '暂无摘要',
          style: Theme.of(context).textTheme.titleLarge,
        ),
        const SizedBox(height: 12),
        Text(analysis.llmOutput['explanation'] as String? ?? '暂无解释'),
        const SizedBox(height: 16),
        Text('建议', style: Theme.of(context).textTheme.titleMedium),
        const SizedBox(height: 8),
        if (advice.isEmpty) const Text('暂无建议'),
        for (final item in advice)
          Padding(
            padding: const EdgeInsets.only(bottom: 6),
            child: Text('• $item'),
          ),
        const SizedBox(height: 12),
        Text(
          analysis.llmOutput['confidence_note'] as String? ?? '暂无置信说明',
          style: Theme.of(context).textTheme.bodySmall,
        ),
      ],
    );
  }
}
