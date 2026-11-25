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
    peerCardBuilder: (peer) => _RdgenNewDeviceCard(peer: peer, now: now, menuPadding: menuPadding));
}

class _RdgenNewDeviceCard extends StatelessWidget {
  final Peer peer;
  final DateTime now;
  final EdgeInsets? menuPadding;
  const _RdgenNewDeviceCard({required this.peer, required this.now, this.menuPadding});

  @override
  Widget build(BuildContext context) => Obx(() {
    final list = peerCardUiType.value == PeerUiType.list;
    final ungrouped = gFFI.groupModel.rdgenOrganizations
        .isConfirmedUngrouped(peer.id, peer.device_group_name);
    final card = RdgenDeviceOrganizationOrigin(
        child: MyGroupPeerCard(peer: peer, menuPadding: menuPadding));
    final age = rdgenDeviceAge(peer.rdgenCreatedAt!, now);
    // Reserve real layout space for metadata; never paint it over native cards.
    if (list) return RdgenNewDeviceRowMetadata(
      details: SizedBox(width: 260, child: RdgenNewDeviceDetails(
        age: age, ungrouped: ungrouped, inline: true)), child: card);
    return LayoutBuilder(builder: (context, constraints) => Column(
      mainAxisSize: MainAxisSize.min,
      crossAxisAlignment: CrossAxisAlignment.stretch,
      children: [
        if (constraints.hasBoundedHeight) Expanded(child: card)
        else SizedBox(height: peerCardUiType.value == PeerUiType.grid ? 140 : 42, child: card),
        SizedBox(height: 38, child: RdgenNewDeviceDetails(age: age, ungrouped: ungrouped)),
      ]));
  });
}

class RdgenNewDeviceDetails extends StatelessWidget {
  final String age;
  final bool ungrouped;
  final bool inline;
  const RdgenNewDeviceDetails({Key? key, required this.age, required this.ungrouped, this.inline = false}) : super(key: key);
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
    final time = item(Icons.schedule_outlined, age, muted);
    final organization = item(Icons.apartment_outlined, translate('No organization'), amber);
    final divider = Container(width: 1, height: 14, color: Theme.of(context).dividerColor.withOpacity(0.3));
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 8),
      decoration: inline ? null : BoxDecoration(
        color: Theme.of(context).colorScheme.background,
        border: Border(top: BorderSide(color: Theme.of(context).dividerColor.withOpacity(0.2))),
        borderRadius: const BorderRadius.vertical(bottom: Radius.circular(6))),
      child: LayoutBuilder(builder: (context, constraints) {
        if (inline) return Row(children: [
          if (ungrouped) Expanded(child: organization) else const Spacer(),
          Padding(padding: const EdgeInsets.symmetric(horizontal: 8), child: divider),
          Expanded(child: time),
        ]);
        if (!ungrouped) return Align(alignment: Alignment.centerLeft, child: time);
        if (constraints.maxWidth >= 204 * MediaQuery.textScalerOf(context).scale(11) / 11) return Row(children: [
          Expanded(flex: 11, child: time),
          Padding(padding: const EdgeInsets.symmetric(horizontal: 4), child: divider),
          Expanded(flex: 12, child: organization),
        ]);
        // At increased text scale, wrap within the same strip rather than
        // overlap or shrink the text on native 220px tiles.
        return Column(mainAxisAlignment: MainAxisAlignment.center, children: [
          Align(alignment: Alignment.centerLeft, child: time),
          const SizedBox(height: 3),
          Align(alignment: Alignment.centerRight, child: organization),
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
      child: Center(widthFactor: 1, child: Transform.translate(
        offset: const Offset(0, 0.5), child: Text('$count', textAlign: TextAlign.center,
        style: TextStyle(fontSize: 13, height: 1, fontWeight: FontWeight.w700, color: color))))));
  }
}
