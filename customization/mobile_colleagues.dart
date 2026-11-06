import 'package:flutter/material.dart';
import '../../common.dart';
import '../../common/widgets/rdgen_colleagues.dart';
import '../../models/platform_model.dart';
import 'home_page.dart';

class RdgenColleaguesPage extends StatefulWidget implements PageShape {
  @override
  final String title = translate('Colleagues');
  @override
  final Widget icon = const Icon(Icons.people);
  @override
  final List<Widget> appBarActions = [
    IconButton(
      tooltip: translate('Refresh'),
      icon: const Icon(Icons.refresh),
      onPressed: () => gFFI.groupModel.pull(force: true),
    ),
  ];

  @override
  State<RdgenColleaguesPage> createState() => _RdgenColleaguesPageState();
}

class _RdgenColleaguesPageState extends State<RdgenColleaguesPage> {
  @override
  void initState() {
    super.initState();
    gFFI.groupModel.pull(force: true);
  }

  @override
  Widget build(BuildContext context) {
    return const Padding(
      padding: EdgeInsets.all(12),
      child: RdgenColleagues(),
    );
  }
}
