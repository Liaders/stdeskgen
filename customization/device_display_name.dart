String resolveDeviceName({
  required String serverAlias,
  required String localAlias,
  required String hostname,
  required String id,
}) {
  if (serverAlias.trim().isNotEmpty) return serverAlias.trim();
  if (localAlias.trim().isNotEmpty) return localAlias.trim();
  return hostname.isNotEmpty ? hostname : id;
}
