String? resolveSessionTitle(String id, dynamic serverAlias, dynamic deviceGroup) {
  final alias = serverAlias is String ? serverAlias.trim() : '';
  final group = deviceGroup is String ? deviceGroup.trim() : '';
  if (group.isNotEmpty) return '${alias.isEmpty ? id : alias} ($group)';
  if (alias.isNotEmpty) return '$id ($alias)';
  return null;
}
