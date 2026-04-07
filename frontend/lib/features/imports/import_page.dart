import 'package:file_picker/file_picker.dart';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../shared/models/import_result.dart';
import '../../shared/providers/app_providers.dart';

class ImportPage extends ConsumerStatefulWidget {
  const ImportPage({super.key});

  @override
  ConsumerState<ImportPage> createState() => _ImportPageState();
}

class _ImportPageState extends ConsumerState<ImportPage> {
  PlatformFile? _selectedFile;
  ImportResult? _lastResult;
  bool _isUploading = false;

  late final TextEditingController _externalUserIdController;
  late final TextEditingController _timezoneController;
  final TextEditingController _nameController = TextEditingController();

  @override
  void initState() {
    super.initState();
    final config = ref.read(appConfigProvider);
    _externalUserIdController = TextEditingController(
      text: config.externalUserId,
    );
    _timezoneController = TextEditingController(text: config.defaultTimezone);
  }

  @override
  void dispose() {
    _externalUserIdController.dispose();
    _timezoneController.dispose();
    _nameController.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
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
                  '导入 Fitbit 数据',
                  style: Theme.of(context).textTheme.titleLarge,
                ),
                const SizedBox(height: 12),
                const Text('第一版仅支持上传 zip 压缩包。导入完成后会自动刷新当前用户相关页面。'),
                const SizedBox(height: 16),
                TextField(
                  controller: _externalUserIdController,
                  decoration: const InputDecoration(
                    labelText: 'external_user_id',
                  ),
                ),
                const SizedBox(height: 12),
                TextField(
                  controller: _timezoneController,
                  decoration: const InputDecoration(labelText: 'timezone'),
                ),
                const SizedBox(height: 12),
                TextField(
                  controller: _nameController,
                  decoration: const InputDecoration(labelText: '显示名称（可选）'),
                ),
                const SizedBox(height: 16),
                OutlinedButton.icon(
                  onPressed: _pickZip,
                  icon: const Icon(Icons.folder_zip_rounded),
                  label: Text(_selectedFile?.name ?? '选择 zip 文件'),
                ),
                const SizedBox(height: 16),
                FilledButton.icon(
                  onPressed: _isUploading ? null : _upload,
                  icon: _isUploading
                      ? const SizedBox.square(
                          dimension: 16,
                          child: CircularProgressIndicator(strokeWidth: 2),
                        )
                      : const Icon(Icons.upload_rounded),
                  label: const Text('开始导入'),
                ),
              ],
            ),
          ),
        ),
        if (_lastResult != null) ...[
          const SizedBox(height: 16),
          Card(
            child: Padding(
              padding: const EdgeInsets.all(20),
              child: _ImportSummary(result: _lastResult!),
            ),
          ),
        ],
      ],
    );
  }

  Future<void> _pickZip() async {
    final result = await FilePicker.platform.pickFiles(
      type: FileType.custom,
      allowedExtensions: const ['zip'],
      withData: true,
    );
    if (result == null || result.files.isEmpty) return;
    setState(() => _selectedFile = result.files.single);
  }

  Future<void> _upload() async {
    final file = _selectedFile;
    if (file == null || file.bytes == null) {
      ScaffoldMessenger.of(
        context,
      ).showSnackBar(const SnackBar(content: Text('请先选择一个 zip 文件。')));
      return;
    }
    setState(() => _isUploading = true);
    try {
      final result = await ref
          .read(importApiProvider)
          .uploadFitbitArchive(
            fileName: file.name,
            bytes: file.bytes!,
            externalUserId: _externalUserIdController.text.trim(),
            timezone: _timezoneController.text.trim(),
            name: _nameController.text.trim().isEmpty
                ? null
                : _nameController.text.trim(),
          );
      setState(() => _lastResult = result);
      if (result.affectedExternalUserIds.isNotEmpty) {
        ref
            .read(activeExternalUserIdProvider.notifier)
            .setExternalUserId(result.affectedExternalUserIds.first);
      }
      ref.invalidate(currentUserProvider);
      ref.invalidate(userProfileProvider);
      ref.invalidate(timelineProvider);
      if (mounted) {
        ScaffoldMessenger.of(
          context,
        ).showSnackBar(const SnackBar(content: Text('导入完成，页面已刷新。')));
      }
    } catch (error) {
      if (mounted) {
        ScaffoldMessenger.of(
          context,
        ).showSnackBar(SnackBar(content: Text('导入失败：$error')));
      }
    } finally {
      if (mounted) {
        setState(() => _isUploading = false);
      }
    }
  }
}

class _ImportSummary extends StatelessWidget {
  const _ImportSummary({required this.result});

  final ImportResult result;

  @override
  Widget build(BuildContext context) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Text('导入结果', style: Theme.of(context).textTheme.titleMedium),
        const SizedBox(height: 12),
        Text('模式：${result.mode}'),
        Text('生成的 segments：${result.generatedSegments}'),
        Text('新增 segments：${result.insertedSegments}'),
        Text('跳过已存在：${result.skippedExisting}'),
        Text('影响用户：${result.affectedExternalUserIds.join(', ')}'),
        const SizedBox(height: 12),
        if (result.metricsDetected.isNotEmpty) ...[
          Text('检测到的指标', style: Theme.of(context).textTheme.titleSmall),
          const SizedBox(height: 8),
          for (final entry in result.metricsDetected.entries)
            Text('${entry.key}: ${entry.value}'),
        ],
        if (result.warnings.isNotEmpty) ...[
          const SizedBox(height: 12),
          Text('警告', style: Theme.of(context).textTheme.titleSmall),
          const SizedBox(height: 8),
          for (final item in result.warnings)
            Padding(
              padding: const EdgeInsets.only(bottom: 6),
              child: Text('• $item'),
            ),
        ],
      ],
    );
  }
}
