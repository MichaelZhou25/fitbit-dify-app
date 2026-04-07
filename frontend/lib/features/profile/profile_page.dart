import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../shared/providers/app_providers.dart';
import '../../shared/widgets/async_value_builder.dart';

class ProfilePage extends ConsumerStatefulWidget {
  const ProfilePage({super.key});

  @override
  ConsumerState<ProfilePage> createState() => _ProfilePageState();
}

class _ProfilePageState extends ConsumerState<ProfilePage> {
  bool _isBootstrapping = false;

  @override
  Widget build(BuildContext context) {
    final userValue = ref.watch(currentUserProvider);
    final profileValue = ref.watch(userProfileProvider);

    return AsyncValueBuilder(
      value: userValue,
      builder: (user) => AsyncValueBuilder(
        value: profileValue,
        loadingLabel: '正在加载用户画像...',
        builder: (profile) {
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
                        '绑定用户',
                        style: Theme.of(context).textTheme.titleMedium,
                      ),
                      const SizedBox(height: 8),
                      Text(
                        user.name?.trim().isNotEmpty == true
                            ? user.name!
                            : user.externalUserId,
                      ),
                      const SizedBox(height: 4),
                      Text('external_user_id: ${user.externalUserId}'),
                      const SizedBox(height: 4),
                      Text('timezone: ${user.timezone}'),
                      const SizedBox(height: 16),
                      if (!profile.isMeaningful)
                        FilledButton.icon(
                          onPressed: _isBootstrapping
                              ? null
                              : () => _bootstrap(user.id),
                          icon: _isBootstrapping
                              ? const SizedBox.square(
                                  dimension: 16,
                                  child: CircularProgressIndicator(
                                    strokeWidth: 2,
                                  ),
                                )
                              : const Icon(Icons.tune_rounded),
                          label: const Text('自动生成画像'),
                        ),
                    ],
                  ),
                ),
              ),
              const SizedBox(height: 16),
              _MapSection(title: '画像', data: profile.profile),
              const SizedBox(height: 16),
              _MapSection(title: '目标', data: profile.goals),
              const SizedBox(height: 16),
              _MapSection(title: '阈值', data: profile.thresholds),
              const SizedBox(height: 16),
              _MapSection(title: '基线', data: profile.baselineStats),
            ],
          );
        },
      ),
    );
  }

  Future<void> _bootstrap(String userId) async {
    setState(() => _isBootstrapping = true);
    try {
      await ref.read(userApiProvider).bootstrapProfile(userId);
      ref.invalidate(userProfileProvider);
      if (mounted) {
        ScaffoldMessenger.of(
          context,
        ).showSnackBar(const SnackBar(content: Text('画像已生成并刷新。')));
      }
    } catch (error) {
      if (mounted) {
        ScaffoldMessenger.of(
          context,
        ).showSnackBar(SnackBar(content: Text('生成画像失败：$error')));
      }
    } finally {
      if (mounted) {
        setState(() => _isBootstrapping = false);
      }
    }
  }
}

class _MapSection extends StatelessWidget {
  const _MapSection({required this.title, required this.data});

  final String title;
  final Map<String, dynamic> data;

  @override
  Widget build(BuildContext context) {
    return Card(
      child: Padding(
        padding: const EdgeInsets.all(20),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(title, style: Theme.of(context).textTheme.titleMedium),
            const SizedBox(height: 12),
            if (data.isEmpty) const Text('暂无数据'),
            for (final entry in data.entries)
              Padding(
                padding: const EdgeInsets.only(bottom: 8),
                child: Row(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Expanded(flex: 2, child: Text(entry.key)),
                    Expanded(flex: 3, child: Text('${entry.value}')),
                  ],
                ),
              ),
          ],
        ),
      ),
    );
  }
}
