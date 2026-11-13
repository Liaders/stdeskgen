import 'dart:convert';
import 'rdgen_session_work_groups.dart';

class WorkOrganization {
  final int? id;
  final String name;
  final Set<String> peerIds;
  WorkOrganization(this.id, this.name, this.peerIds);
  String get selectionKey => id?.toString() ?? name;
}

// Separate from access-control group models and their on-disk caches.
Future<List<WorkOrganization>?> loadWorkOrganizations(Uri base, String token,
    WorkGroupRequest request, bool Function() authorized) async {
  if (!['http', 'https'].contains(base.scheme) || !base.hasAuthority ||
      base.userInfo.isNotEmpty || token.isEmpty) throw FormatException('Invalid API URL');
  final result = <WorkOrganization>[];
  final seen = <int>{};
  var total = 0;
  for (var page = 1; ; page++) {
    if (!authorized()) throw StateError('Account changed');
    final uri = base.replace(path: base.path.replaceFirst(RegExp(r'/$'), '') +
        '/api/statusdesk/organizations', queryParameters: {'current': '$page', 'pageSize': '100'});
    final reply = await request('GET', uri, token, null);
    if (!authorized()) throw StateError('Account changed');
    if (page == 1 && [404, 405, 501].contains(reply.code)) return null;
    if (reply.code != 200) throw StateError('Organizations: ${reply.code}');
    final data = jsonDecode(reply.body);
    if (data is! Map || data['total'] is! int || data['total'] < 0 || data['data'] is! List) {
      throw FormatException('Invalid organizations response');
    }
    total = data['total'] as int;
    final rows = data['data'] as List;
    if (rows.isEmpty && result.length < total) throw FormatException('Incomplete organizations');
    for (final row in rows) {
      if (row is! Map || row['id'] is! int || row['id'] <= 0 ||
          row['name'] is! String || row['peer_ids'] is! List ||
          (row['peer_ids'] as List).any((id) => id is! String) || !seen.add(row['id'] as int)) {
        throw FormatException('Invalid organization');
      }
      result.add(WorkOrganization(row['id'] as int, row['name'] as String,
          (row['peer_ids'] as List).cast<String>().toSet()));
    }
    if (result.length >= total) break;
  }
  result.sort((a, b) => a.name.compareTo(b.name));
  return result;
}
