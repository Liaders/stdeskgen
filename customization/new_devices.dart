import 'dart:async';
import 'package:flutter/material.dart';
import 'package:get/get.dart';
import '../../common.dart';
import '../../models/peer_model.dart';
import '../../models/peer_tab_model.dart';
import 'peers_view.dart';
import 'peer_card.dart';
import 'rdgen_new_device_row_metadata.dart';
import '../../models/rdgen_device_organization_origin.dart';

bool rdgenIsNewDevice(Peer peer, DateTime now) {
  final date = peer.rdgenCreatedAt;
  return date != null && !date.isAfter(now) &&
      now.difference(date) < const Duration(hours: 24);
}

String rdgenDeviceAge(DateTime date, DateTime now) {
  final age = now.difference(date);
  if (age.inMinutes < 1) return translate('Just now');
  final hours = age.inHours;
  final n = hours == 0 ? age.inMinutes : hours;
  final key = hours == 0 ? 'Minutes ago' : 'Hours ago';
  // Russian plural forms; other languages use the ordinary translation fallback.
  final language = WidgetsBinding.instance.platformDispatcher.locale.languageCode;
  final translated = translate(key);
  if (language == 'ru' || translated == 'минут назад' || translated == 'часов назад') {
    final one = n % 10 == 1 && n % 100 != 11;
    final few = n % 10 >= 2 && n % 10 <= 4 && !(n % 100 >= 12 && n % 100 <= 14);
    final unit = hours == 0 ? (one ? 'минуту' : few ? 'минуты' : 'минут')
        : (one ? 'час' : few ? 'часа' : 'часов');
    return '$n $unit назад';
  }
  return '$n $translated';
}

/// A slow tick updates relative ages and removes devices at the 24h boundary.
/// It never requests data from the server.
class RdgenNewDeviceClock extends StatefulWidget {
  final Widget Function(DateTime) builder;
  const RdgenNewDeviceClock({Key? key, required this.builder}) : super(key: key);
  @override
  State<RdgenNewDeviceClock> createState() => _RdgenNewDeviceClockState();
}

class _RdgenNewDeviceClockState extends State<RdgenNewDeviceClock> {
  Timer? _timer;
  @override
  void initState() {
    super.initState();
    _timer = Timer.periodic(const Duration(seconds: 30), (_) {
      if (mounted) setState(() {});
    });
  }
  @override
  void dispose() { _timer?.cancel(); super.dispose(); }
  @override
  Widget build(BuildContext context) => widget.builder(DateTime.now());
}

class RdgenNewDevices extends StatelessWidget {
  final EdgeInsets? menuPadding;
  const RdgenNewDevices({Key? key, this.menuPadding}) : super(key: key);
  @override
  Widget build(BuildContext context) => RdgenNewDeviceClock(builder: (now) =>
      _RdgenNewPeers(now: now, menuPadding: menuPadding));
}

class _RdgenNewPeers extends BasePeersView {
  _RdgenNewPeers({required DateTime now, EdgeInsets? menuPadding}) : super(
    peerTabIndex: PeerTabIndex.group,
    rdgenCardFooterHeight: 38,
    peerFilter: (peer) => rdgenIsNewDevice(peer, now),
    rdgenComparator: (a, b) {
      final date = b.rdgenCreatedAt!.compareTo(a.rdgenCreatedAt!);
      return date != 0 ? date : a.id.compareTo(b.id);
    },
    peerCardBuilder: (peer) => RdgenDeviceCard(peer: peer, now: now, menuPadding: menuPadding));
}

class RdgenDeviceCard extends StatelessWidget {
  final Peer peer;
  final DateTime? now;
  final Widget? child;
  final EdgeInsets? menuPadding;
  const RdgenDeviceCard({required this.peer, this.now, this.child, this.menuPadding});

  @override
  Widget build(BuildContext context) => Obx(() {
    final list = peerCardUiType.value == PeerUiType.list;
    final ungrouped = gFFI.groupModel.rdgenOrganizations
        .isConfirmedUngrouped(peer.id, peer.device_group_name);
    final organization = gFFI.groupModel.rdgenOrganizations.deviceOrganizationLabel(peer.id, peer.device_group_name);
    final card = child ?? RdgenDeviceOrganizationOrigin(
        child: MyGroupPeerCard(peer: peer, menuPadding: menuPadding));
    final age = now == null ? null : rdgenDeviceAge(peer.rdgenCreatedAt!, now!);
    // Reserve real layout space for metadata; never paint it over native cards.
    return LayoutBuilder(builder: (context, constraints) {
      final details = RdgenNewDeviceDetails(age: age, ungrouped: ungrouped, organizationName: organization);
      if (list) {
        final name = peer.alias.trim().isEmpty ? (peer.hostname.isEmpty ? peer.id : peer.hostname) : peer.alias;
        final style = Theme.of(context).textTheme.titleSmall;
        double measure(String text, TextStyle? style) {
          final painter = TextPainter(text: TextSpan(text: text, style: style),
            textDirection: Directionality.of(context), textScaler: MediaQuery.textScalerOf(context))..layout();
          final width = painter.width;
          painter.dispose();
          return width;
        }
        final identity = (measure(name, style) > measure(formatID(peer.id), style)
            ? measure(name, style) : measure(formatID(peer.id), style)) + 112;
        final available = (constraints.maxWidth - identity).clamp(0.0, constraints.maxWidth * .65).toDouble();
        final orgLabel = organization ?? (ungrouped ? translate('No organization') : '');
        final metadataStyle = const TextStyle(fontSize: 11, height: 1.1);
        final natural = measure(String.fromCharCodes(orgLabel.runes.take(25)), metadataStyle) + 33 +
            (age == null ? 0 : measure(age, metadataStyle) + 34);
        return RdgenNewDeviceRowMetadata(
          details: SizedBox(width: available < natural ? available : natural,
            child: RdgenNewDeviceDetails(age: age, ungrouped: ungrouped,
              organizationName: organization, inline: true)), child: card);
      }
      return Column(mainAxisSize: MainAxisSize.min,
        crossAxisAlignment: CrossAxisAlignment.stretch, children: [
          if (constraints.hasBoundedHeight) Expanded(child: card)
          else SizedBox(height: peerCardUiType.value == PeerUiType.grid ? 140 : 45, child: card),
          SizedBox(height: 38, child: details),
        ]);
    });
  });
}

class RdgenNewDeviceDetails extends StatelessWidget {
  final String? age;
  final String? organizationName;
  final bool ungrouped;
  final bool inline;
  const RdgenNewDeviceDetails({Key? key, required this.age, required this.ungrouped, this.organizationName, this.inline = false}) : super(key: key);
  @override
  Widget build(BuildContext context) {
    final muted = Theme.of(context).textTheme.bodySmall?.color;
    final amber = Theme.of(context).brightness == Brightness.dark
        ? const Color(0xFFEAB84B) : const Color(0xFF936310);
    Widget item(IconData icon, String text, Color? color) => Row(
      mainAxisSize: MainAxisSize.min, children: [
        Icon(icon, size: 13, color: color), const SizedBox(width: 4),
        Flexible(child: Text(text, maxLines: 1, overflow: TextOverflow.ellipsis,
          style: TextStyle(fontSize: 11, height: 1.1, color: color))),
      ]);
    final assignedColor = Theme.of(context).brightness == Brightness.dark ? Colors.white : Theme.of(context).textTheme.bodyMedium?.color;
    final fullOrganization = organizationName ?? (ungrouped ? translate('No organization') : '');
    final shortOrganization = String.fromCharCodes(fullOrganization.runes.take(25));
    final label = shortOrganization == fullOrganization ? fullOrganization : '$shortOrganization…';
    final orgColor = ungrouped ? amber : assignedColor;
    final style = TextStyle(fontSize: 11, height: 1.1, color: muted);
    double measure(String value) {
      final painter = TextPainter(text: TextSpan(text: value, style: style),
        textDirection: Directionality.of(context), textScaler: MediaQuery.textScalerOf(context))..layout();
      final width = painter.width;
      painter.dispose();
      return width;
    }
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 4),
      decoration: inline ? null : BoxDecoration(
        color: Theme.of(context).colorScheme.background,
        border: Border(top: BorderSide(color: Theme.of(context).dividerColor.withOpacity(0.2))),
        borderRadius: const BorderRadius.vertical(bottom: Radius.circular(6))),
      child: LayoutBuilder(builder: (context, constraints) {
        final width = constraints.maxWidth;
        if (width < 20) return const SizedBox.shrink();
        final hasOrg = label.isNotEmpty;
        final hasTime = age != null;
        final separator = hasOrg && hasTime ? 17.0 : 0.0;
        final orgMin = hasOrg ? measure('…') + 17 : 0.0;
        final timeNatural = hasTime ? measure(age!) + 17 : 0.0;
        final timeWidth = timeNatural < width - orgMin - separator
          ? timeNatural : (width - orgMin - separator).clamp(0.0, width).toDouble();
        final orgWidth = hasOrg ? (width - timeWidth - separator).clamp(0.0, width).toDouble() : 0.0;
        Widget organization() => Tooltip(message: fullOrganization, child: Row(children: [
          Expanded(child: Text(orgWidth <= orgMin + 1 ? '…' : label,
            maxLines: 1, overflow: TextOverflow.ellipsis, textAlign: TextAlign.right,
            style: style.copyWith(color: orgColor))),
          const SizedBox(width: 4), Icon(Icons.apartment_outlined, size: 13, color: orgColor),
        ]));
        Widget time() => Tooltip(message: age!, child: item(Icons.schedule_outlined, age!, muted));
        if (!hasOrg && !hasTime) return const SizedBox.shrink();
        // At extremely narrow widths retain the native identity and omit metadata
        // that cannot fit even its icons. Never overflow or add another line.
        if (hasOrg && orgWidth < 17) return hasTime && width >= 17 ? time() : const SizedBox.shrink();
        return Row(children: [
          if (hasOrg) SizedBox(width: orgWidth, child: organization()),
          if (hasOrg && hasTime && timeWidth >= 17) ...[
            const SizedBox(width: 8), Container(width: 1, height: 14,
              color: Theme.of(context).dividerColor.withOpacity(0.3)), const SizedBox(width: 8),
          ],
          if (hasTime && timeWidth >= 17) SizedBox(width: timeWidth, child: time()),
        ]);
      }));
  }
}

class RdgenNewDeviceCount extends StatelessWidget {
  final int count;
  final bool selected;
  const RdgenNewDeviceCount({Key? key, required this.count, required this.selected}) : super(key: key);
  @override
  Widget build(BuildContext context) {
    if (count <= 0) return const SizedBox.shrink();
    final color = selected ? const Color(0xFFEAB84B) : const Color(0xFFD29922);
    return Padding(padding: const EdgeInsets.only(top: 1), child: Container(
      height: MediaQuery.textScalerOf(context).scale(13) + 2,
      constraints: const BoxConstraints(minWidth: 16),
      padding: const EdgeInsets.symmetric(horizontal: 2),
      decoration: BoxDecoration(color: color.withOpacity(selected ? 0.22 : 0.12),
        borderRadius: BorderRadius.circular(4),
        border: Border.all(color: color.withOpacity(selected ? 0.55 : 0.35))),
      child: Center(widthFactor: 1, child: Text('$count', textAlign: TextAlign.center,
        style: TextStyle(fontSize: 12, height: 1, fontWeight: FontWeight.w700, color: color)))));
  }
}
