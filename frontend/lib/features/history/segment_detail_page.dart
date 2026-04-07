import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:intl/intl.dart';

import '../../shared/models/segment_detail.dart';
import '../../shared/providers/app_providers.dart';
import '../../shared/widgets/async_value_builder.dart';

final segmentDetailProvider = FutureProvider.family<SegmentDetail, String>((
  ref,
  segmentId,
) {
  return ref.watch(segmentApiProvider).fetchSegmentDetail(segmentId);
});

class SegmentDetailPage extends ConsumerStatefulWidget {
  const SegmentDetailPage({super.key, required this.segmentId});

  final String segmentId;

  @override
  ConsumerState<SegmentDetailPage> createState() => _SegmentDetailPageState();
}

class _SegmentDetailPageState extends ConsumerState<SegmentDetailPage> {
  bool _isAnalyzing = false;

  @override
  Widget build(BuildContext context) {
    final detailValue = ref.watch(segmentDetailProvider(widget.segmentId));

    return AsyncValueBuilder(
      value: detailValue,
      loadingLabel: '正在加载 segment 详情...',
      builder: (detail) {
        final formatter = DateFormat('yyyy-MM-dd HH:mm');
        return ListView(
          padding: const EdgeInsets.all(20),
          children: [
            Card(
              child: Padding(
                padding: const EdgeInsets.all(20),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(
                      '${formatter.format(detail.segmentStart)} - ${formatter.format(detail.segmentEnd)}',
                      style: Theme.of(context).textTheme.titleLarge,
                    ),
                    const SizedBox(height: 8),
                    Text('来源：${detail.sourceType} · 粒度：${detail.granularity}'),
                    const SizedBox(height: 16),
                    FilledButton.icon(
                      onPressed: _isAnalyzing ? null : _analyze,
                      icon: _isAnalyzing
                          ? const SizedBox.square(
                              dimension: 16,
                              child: CircularProgressIndicator(strokeWidth: 2),
                            )
                          : const Icon(Icons.auto_awesome_rounded),
                      label: const Text('分析这一段'),
                    ),
                  ],
                ),
              ),
            ),
            const SizedBox(height: 16),
            Card(
              child: Padding(
                padding: const EdgeInsets.all(20),
                child: _MetricsGrid(rawPayload: detail.rawPayload),
              ),
            ),
            const SizedBox(height: 16),
            Card(
              child: Padding(
                padding: const EdgeInsets.all(20),
                child: _PredictionSection(detail: detail),
              ),
            ),
            const SizedBox(height: 16),
            Card(
              child: Padding(
                padding: const EdgeInsets.all(20),
                child: _SavedAnalysisSection(detail: detail),
              ),
            ),
          ],
        );
      },
    );
  }

  Future<void> _analyze() async {
    setState(() => _isAnalyzing = true);
    try {
      await ref.read(segmentApiProvider).analyzeSegment(widget.segmentId);
      ref.invalidate(segmentDetailProvider(widget.segmentId));
      ref.invalidate(timelineProvider);
      if (mounted) {
        ScaffoldMessenger.of(
          context,
        ).showSnackBar(const SnackBar(content: Text('分析完成，详情已刷新。')));
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
}

class _MetricsGrid extends StatelessWidget {
  const _MetricsGrid({required this.rawPayload});

  final Map<String, dynamic> rawPayload;

  @override
  Widget build(BuildContext context) {
    final items = <MapEntry<String, String>>[
      MapEntry('步数', '${rawPayload['steps'] ?? 0}'),
      MapEntry('卡路里', '${rawPayload['calories'] ?? 0}'),
      MapEntry('睡眠分钟', '${rawPayload['sleep_minutes'] ?? 0}'),
      MapEntry('静坐分钟', '${rawPayload['sedentary_minutes'] ?? 0}'),
      MapEntry('活跃分钟', '${rawPayload['active_minutes'] ?? 0}'),
      MapEntry(
        '心率样本数',
        '${(rawPayload['heart_rate_series'] as List? ?? const []).length}',
      ),
    ];
    return Wrap(
      spacing: 12,
      runSpacing: 12,
      children: items
          .map(
            (entry) => SizedBox(
              width: 180,
              child: DecoratedBox(
                decoration: BoxDecoration(
                  color: Colors.white,
                  borderRadius: BorderRadius.circular(18),
                ),
                child: Padding(
                  padding: const EdgeInsets.all(16),
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text(
                        entry.key,
                        style: Theme.of(context).textTheme.bodySmall,
                      ),
                      const SizedBox(height: 6),
                      Text(
                        entry.value,
                        style: Theme.of(context).textTheme.titleMedium,
                      ),
                    ],
                  ),
                ),
              ),
            ),
          )
          .toList(),
    );
  }
}

class _PredictionSection extends StatelessWidget {
  const _PredictionSection({required this.detail});

  final SegmentDetail detail;

  @override
  Widget build(BuildContext context) {
    if (detail.predictions.isEmpty) {
      return const Text('当前还没有保存的预测结果。');
    }
    final prediction = detail.predictions.first;
    final probabilities = Map<String, dynamic>.from(
      prediction['probabilities'] as Map? ?? const {},
    );
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Text('模型预测', style: Theme.of(context).textTheme.titleMedium),
        const SizedBox(height: 8),
        Text('主标签：${prediction['top_label'] ?? '未知'}'),
        const SizedBox(height: 12),
        for (final entry in probabilities.entries)
          Padding(
            padding: const EdgeInsets.only(bottom: 6),
            child: Text('${entry.key}: ${entry.value}'),
          ),
      ],
    );
  }
}

class _SavedAnalysisSection extends StatelessWidget {
  const _SavedAnalysisSection({required this.detail});

  final SegmentDetail detail;

  @override
  Widget build(BuildContext context) {
    final analysis = detail.savedAnalysis;
    if (analysis == null) {
      return const Text('当前还没有保存的 AI 分析结果。请点击上方按钮开始分析。');
    }
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Text('AI 分析', style: Theme.of(context).textTheme.titleMedium),
        const SizedBox(height: 8),
        Text(analysis.llmOutput['summary'] as String? ?? '暂无摘要'),
        const SizedBox(height: 12),
        Text(analysis.llmOutput['explanation'] as String? ?? '暂无解释'),
        const SizedBox(height: 12),
        Text('建议', style: Theme.of(context).textTheme.titleSmall),
        const SizedBox(height: 8),
        if (analysis.personalizedAdvice.isEmpty) const Text('暂无建议'),
        for (final item in analysis.personalizedAdvice)
          Padding(
            padding: const EdgeInsets.only(bottom: 6),
            child: Text('• $item'),
          ),
      ],
    );
  }
}
