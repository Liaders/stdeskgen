import 'dart:convert';
import 'package:flutter/material.dart';
import '../common.dart';
import 'platform_model.dart';

final rdgenAbAliasRevision = ValueNotifier<int>(0);
String _identity() => jsonEncode([bind.mainGetLocalOption(key: 'user_info'), gFFI.abModel.currentName.value]);
Future<String> _key(String id) async {
  final server = await bind.mainGetApiServer();
  final info = jsonDecode(bind.mainGetLocalOption(key: 'user_info').isEmpty ? '{}' : bind.mainGetLocalOption(key: 'user_info'));
  return 'rdgen-ab-local-alias-v1-' + base64Url.encode(utf8.encode(jsonEncode([
    server, info['id'] ?? info['name'], gFFI.abModel.currentName.value, id])));
}
Future<void> rdgenEditLocalAbAlias(BuildContext context, String id) async {
  final owner = _identity();
  final key = await _key(id);
  if (!context.mounted || owner != _identity()) return;
  var alias = bind.mainGetLocalOption(key: key);
  final value = await showDialog<String>(context: context, builder: (context) => AlertDialog(
    title: Text(translate('Local device alias')),
    content: TextFormField(initialValue: alias, onChanged: (value) => alias = value, autofocus: true,
      decoration: InputDecoration(hintText: translate('Alias'))),
    actions: [TextButton(onPressed: () => Navigator.pop(context), child: Text(translate('Cancel'))),
      TextButton(onPressed: () => Navigator.pop(context, alias.trim()), child: Text(translate('Save')))]));
  if (value == null || owner != _identity() || key != await _key(id)) return;
  await bind.mainSetLocalOption(key: key, value: value);
  rdgenAbAliasRevision.value++;
}
class RdgenAbAliasLabel extends StatefulWidget {
  final String id;
  final Text fallback;
  const RdgenAbAliasLabel({super.key, required this.id, required this.fallback});
  @override
  State<RdgenAbAliasLabel> createState() => _RdgenAbAliasLabelState();
}
class _RdgenAbAliasLabelState extends State<RdgenAbAliasLabel> {
  String alias = '', owner = '';
  int generation = 0;
  @override
  void initState() { super.initState(); rdgenAbAliasRevision.addListener(load); load(); }
  Future<void> load() async {
    final epoch = ++generation;
    final identity = _identity();
    owner = identity;
    try {
      final key = await _key(widget.id);
      if (!mounted || epoch != generation || identity != _identity()) return;
      final value = bind.mainGetLocalOption(key: key);
      setState(() { alias = value; });
    } catch (_) { if (mounted && epoch == generation) setState(() { alias = ''; }); }
  }
  @override
  void didUpdateWidget(RdgenAbAliasLabel old) {
    super.didUpdateWidget(old);
    if (old.id != widget.id || owner != _identity()) { alias = ''; load(); }
  }
  @override
  void dispose() { generation++; rdgenAbAliasRevision.removeListener(load); super.dispose(); }
  @override
  Widget build(BuildContext context) => alias.isEmpty ? widget.fallback : Text(alias,
      style: widget.fallback.style, maxLines: 1, overflow: TextOverflow.ellipsis);
}
