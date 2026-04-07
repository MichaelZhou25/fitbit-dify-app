import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';

class AppShell extends StatelessWidget {
  const AppShell({super.key, required this.child});

  final Widget child;

  static const _destinations = [
    (label: '首页', icon: Icons.home_rounded, path: '/'),
    (label: '历史', icon: Icons.timeline_rounded, path: '/history'),
    (label: '画像', icon: Icons.person_rounded, path: '/profile'),
    (label: '导入', icon: Icons.upload_file_rounded, path: '/import'),
  ];

  @override
  Widget build(BuildContext context) {
    final location = GoRouterState.of(context).uri.toString();
    final selectedIndex = _selectedIndex(location);
    final isWide = MediaQuery.sizeOf(context).width >= 900;

    return Scaffold(
      appBar: AppBar(title: Text(_destinations[selectedIndex].label)),
      body: Row(
        children: [
          if (isWide)
            NavigationRail(
              selectedIndex: selectedIndex,
              onDestinationSelected: (index) =>
                  context.go(_destinations[index].path),
              labelType: NavigationRailLabelType.all,
              destinations: _destinations
                  .map(
                    (item) => NavigationRailDestination(
                      icon: Icon(item.icon),
                      label: Text(item.label),
                    ),
                  )
                  .toList(),
            ),
          Expanded(child: child),
        ],
      ),
      bottomNavigationBar: isWide
          ? null
          : NavigationBar(
              selectedIndex: selectedIndex,
              onDestinationSelected: (index) =>
                  context.go(_destinations[index].path),
              destinations: _destinations
                  .map(
                    (item) => NavigationDestination(
                      icon: Icon(item.icon),
                      label: item.label,
                    ),
                  )
                  .toList(),
            ),
    );
  }

  int _selectedIndex(String location) {
    if (location.startsWith('/history')) return 1;
    if (location.startsWith('/profile')) return 2;
    if (location.startsWith('/import')) return 3;
    return 0;
  }
}
