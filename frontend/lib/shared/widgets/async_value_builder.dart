import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

class AsyncValueBuilder<T> extends StatelessWidget {
  const AsyncValueBuilder({
    super.key,
    required this.value,
    required this.builder,
    this.loadingLabel = '正在加载...',
  });

  final AsyncValue<T> value;
  final Widget Function(T data) builder;
  final String loadingLabel;

  @override
  Widget build(BuildContext context) {
    return value.when(
      data: builder,
      loading: () => Center(
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            const CircularProgressIndicator(),
            const SizedBox(height: 12),
            Text(loadingLabel),
          ],
        ),
      ),
      error: (error, _) => Center(
        child: Padding(
          padding: const EdgeInsets.all(24),
          child: Text('加载失败：$error', textAlign: TextAlign.center),
        ),
      ),
    );
  }
}
