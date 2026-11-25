import 'dart:async';
import 'package:flutter/material.dart';
import 'package:get/get.dart';
import '../../common.dart';
import '../../models/peer_model.dart';
import '../../models/peer_tab_model.dart';
import 'peers_view.dart';
import 'peer_card.dart';
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
    final details = RdgenNewDeviceDetails(
        age: rdgenDeviceAge(peer.rdgenCreatedAt!, now), ungrouped: ungrouped);
    // Reserve real layout space for metadata; never paint it over native cards.
    if (list) return Row(children: [
      Expanded(child: card),
      SizedBox(width: 158, child: details),
    ]);
    return LayoutBuilder(builder: (context, constraints) => Column(
      mainAxisSize: MainAxisSize.min,
      crossAxisAlignment: CrossAxisAlignment.stretch,
      children: [
        if (constraints.hasBoundedHeight) Expanded(child: card)
        else SizedBox(height: peerCardUiType.value == PeerUiType.grid ? 140 : 42, child: card),
        SizedBox(height: 38, child: details),
      ]));
  });
}

class RdgenNewDeviceDetails extends StatelessWidget {
  final String age;
  final bool ungrouped;
  const RdgenNewDeviceDetails({Key? key, required this.age, required this.ungrouped}) : super(key: key);
  @override
  Widget build(BuildContext context) => Padding(
    padding: const EdgeInsets.symmetric(horizontal: 6),
    child: Column(mainAxisAlignment: MainAxisAlignment.center,
      crossAxisAlignment: CrossAxisAlignment.start, children: [
        Text(age, maxLines: 1, overflow: TextOverflow.ellipsis,
          style: TextStyle(fontSize: 11, height: 1.1, color: Theme.of(context).textTheme.bodySmall?.color)),
        if (ungrouped) Container(
          padding: const EdgeInsets.symmetric(horizontal: 4, vertical: 1),
          decoration: BoxDecoration(color: const Color(0x22D29922),
            borderRadius: BorderRadius.circular(4),
            border: Border.all(color: const Color(0xFFD29922))),
          child: Text(translate('No organization'), maxLines: 1, overflow: TextOverflow.ellipsis,
            style: const TextStyle(fontSize: 10, height: 1.1, color: Color(0xFFEAB84B)))),
      ]));
}
