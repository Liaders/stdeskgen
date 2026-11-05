"""Apply the supported UI profile to a clean RustDesk source checkout."""
import argparse
import json
from pathlib import Path
import re

SUPPORTED_VERSION = "1.5.0"


def apply(root, version, profile, check=False):
    if version != SUPPORTED_VERSION:
        raise ValueError(f"UI customization is not supported for RustDesk {version}")
    allowed = {"schema_version", "accent", "button", "navigation", "group_width", "address_book_width", "device_names", "resizable_panels", "colleagues"}
    if set(profile) - allowed:
        raise ValueError("Unknown profile fields: " + ", ".join(sorted(set(profile) - allowed)))
    if type(profile.get("schema_version")) is not int or profile["schema_version"] != 1:
        raise ValueError("Expected profile schema_version 1")
    edits = {}

    def replace(relative, old, new):
        path = root / relative
        text = edits.get(path, path.read_text(encoding="utf-8"))
        if text.count(old) != 1:
            raise ValueError(f"Incompatible source: expected one match in {relative}: {old!r}")
        edits[path] = text.replace(old, new, 1)

    for name in ("accent", "button"):
        if name not in profile:
            continue
        color = profile[name]
        if not isinstance(color, str) or not re.fullmatch(r"#[0-9a-fA-F]{6}", color):
            raise ValueError(f"{name} must be #RRGGBB")
        rgb = color[1:].upper()
        old = "0071FF" if name == "accent" else "2C8CFF"
        replace("flutter/lib/common.dart", f"{name} = Color(0xFF{old})", f"{name} = Color(0xFF{rgb})")
        if name == "accent":
            for suffix, alpha in (("50", "77"), ("80", "AA")):
                replace("flutter/lib/common.dart", f"accent{suffix} = Color(0x{alpha}0071FF)", f"accent{suffix} = Color(0x{alpha}{rgb})")
    for key, file, initial in (("group_width", "my_group.dart", 150), ("address_book_width", "address_book.dart", 200)):
        if key in profile:
            value = profile[key]
            if type(value) is not int or not 150 <= value <= 480:
                raise ValueError(f"{key} must be an integer between 150 and 480")
            replace("flutter/lib/common/widgets/" + file, f"width: {initial},", f"width: {value},")
    if "resizable_panels" in profile and type(profile["resizable_panels"]) is not bool:
        raise ValueError("resizable_panels must be boolean")
    if profile.get("resizable_panels", False):
        target = root / "flutter/lib/common/widgets/rdgen_resizable_panel.dart"
        if target.exists():
            raise ValueError("Resizable panel module already exists")
        edits[target] = Path(__file__).with_name("resizable_panel.dart").read_text(encoding="utf-8")
        for file, method, key, default in (
            ("my_group.dart", "_buildLandscape", "group_width", 150),
            ("address_book.dart", "_buildAddressBookLandscape", "address_book_width", 200),
        ):
            relative = "flutter/lib/common/widgets/" + file
            replace(relative, "import 'package:flutter/material.dart';", "import 'package:flutter/material.dart';\nimport 'rdgen_resizable_panel.dart';")
            if file == "my_group.dart":
                replace(relative, "import '../../common.dart';", "import '../../common.dart';\nimport '../../models/platform_model.dart';")
            path = root / relative
            source = edits.get(path, path.read_text(encoding="utf-8"))
            start = source.index("  Widget " + method + "() {")
            end = source.index("\n  Widget ", start + 1)
            old = source[start:end]
            width = profile.get(key, default)
            opening = re.search(r"(?P<indent> +)child: Container\(\n(?P=indent)  width: " + str(width) + ",", old)
            if not opening:
                raise ValueError("Incompatible sidebar structure: " + relative)
            indent = opening.group("indent")
            container_start = old.index("Container(", opening.start())
            position = container_start + len("Container(")
            depth = 1
            while depth and position < len(old):
                if old[position] == "(": depth += 1
                elif old[position] == ")": depth -= 1
                position += 1
            if depth:
                raise ValueError("Unbalanced sidebar source: " + relative)
            container = old[container_start:position].replace("width: " + str(width) + ",", "width: width,", 1)
            option = "rdgen-panel-" + key.replace("_", "-") + "-v1"
            wrapper = ("RdgenResizablePanel(\n" + indent + "  initialWidth: " + str(width) + ",\n"
                + indent + "  availableWidth: constraints.maxWidth,\n"
                + indent + "  readWidth: () => bind.getLocalFlutterOption(k: '" + option + "'),\n"
                + indent + "  saveWidth: (value) => bind.setLocalFlutterOption(k: '" + option + "', v: value),\n"
                + indent + "  restoreLabel: translate('Restore'),\n"
                + indent + "  builder: (width) => " + container + ")")
            updated = old[:container_start] + wrapper + old[position:]
            reactive = file == "address_book.dart"
            row = "return LayoutBuilder(builder: (context, constraints) => " + ("Obx(() => " if reactive else "") + "Row("
            updated = updated.replace("return Row(", row, 1)
            closing = updated.rfind("    );")
            if closing < 0:
                raise ValueError("Incompatible sidebar closure: " + relative)
            updated = updated[:closing] + updated[closing:].replace("    );", "    )));" if reactive else "    ));", 1)
            replace(relative, old, updated)
    navigation = profile.get("navigation", "icons")
    if navigation not in ("icons", "text"):
        raise ValueError("navigation must be icons or text")
    if navigation == "text":
        file = "flutter/lib/common/widgets/peer_tab_page.dart"
        replace(file, "physics: NeverScrollableScrollPhysics(),", "physics: ClampingScrollPhysics(),")
        replace(file, "child: Icon(model.tabIcon(t), color: color)", "child: Text(model.tabTooltip(t), style: TextStyle(color: color))")
    if "device_names" in profile and type(profile["device_names"]) is not bool:
        raise ValueError("device_names must be boolean")
    if profile.get("device_names", False):
        model = "flutter/lib/models/group_model.dart"
        resolver = Path(__file__).with_name("device_display_name.dart")
        target = root / "flutter/lib/models/rdgen_device_display_name.dart"
        if target.exists():
            raise ValueError("UI name resolver already exists")
        edits[target] = resolver.read_text(encoding="utf-8")
        replace(model, "import 'dart:convert';", "import 'dart:convert';\nimport 'rdgen_device_display_name.dart';")
        replace(model, "                final peer = PeerPayload.toPeer(peerPayload);", """                final peer = PeerPayload.toPeer(peerPayload);
                peer.alias = p['alias'] is String ? (p['alias'] as String).trim() : '';""")
        replace(model, "'peers': peers.map((e) => e.toGroupCacheJson()).toList()", "'peers': peers.map((e) => e.toGroupCacheJson()..['alias'] = e.alias).toList()")
        replace(model, "  late final Peers peersModel;", """  final Map<String, String> deviceUserNames = {};

  Future<String> _deviceNameKey() async =>
      'rdgen-device-name-v1:' + base64Url.encode(utf8.encode(await bind.mainGetApiServer()));

  Future<void> loadDeviceUserNames(Iterable<Peer> devices) async {
    final key = await _deviceNameKey();
    for (final peer in devices) {
      deviceUserNames[peer.id] = await bind.mainGetPeerOption(id: peer.id, key: key);
    }
  }

  String deviceDisplayName(Peer peer) {
    return resolveDeviceName(serverAlias: peer.alias,
        localAlias: deviceUserNames[peer.id] ?? '', hostname: peer.hostname, id: peer.id);
  }

  Future<void> setDeviceUserName(Peer peer, String name) async {
    await bind.mainSetPeerOption(id: peer.id, key: await _deviceNameKey(), value: name.trim());
    deviceUserNames[peer.id] = name.trim();
    platformFFI.tryHandle({'name': LoadEvent.group});
  }

  late final Peers peersModel;""")
        replace(model, "    deviceGroups.value = tmpDeviceGroups;", "    await loadDeviceUserNames(tmpPeers);\n    deviceGroups.value = tmpDeviceGroups;")
        replace(model, "        _callbackPeerUpdate();", "        await loadDeviceUserNames(peers);\n        _callbackPeerUpdate();")
        replace(model, "    peers.clear();\n    selectedAccessibleItemName", "    peers.clear();\n    deviceUserNames.clear();\n    selectedAccessibleItemName")
        cards = "flutter/lib/common/widgets/peer_card.dart"
        old = "peer.alias.isEmpty ? formatID(peer.id) : peer.alias,"
        # The first two occurrences are the tile and grid title; the delete dialog is untouched.
        path = root / cards
        text = edits.get(path, path.read_text(encoding="utf-8"))
        if text.count(old) != 2:
            raise ValueError("Incompatible device card titles")
        edits[path] = text.replace(old, "widget.tab == PeerTabIndex.group ? gFFI.groupModel.deviceDisplayName(peer) : (peer.alias.isEmpty ? formatID(peer.id) : peer.alias),")
        replace(cards, "    // menuItems.add(_renameAction(peer.id));", """    menuItems.add(MenuEntryButton<String>(
      childBuilder: (TextStyle? style) => Text(translate('Alias'), style: style),
      proc: () {
        final controller = TextEditingController(text: gFFI.groupModel.deviceUserNames[peer.id] ?? '');
        gFFI.dialogManager.show((setState, close, context) {
          return CustomAlertDialog(
            title: Text(translate('Alias')),
            content: Column(mainAxisSize: MainAxisSize.min, children: [
              Text('${peer.hostname} (${peer.id})'),
              if (peer.alias.trim().isNotEmpty)
                Text('${translate('Server')}: ${peer.alias}'),
              TextField(controller: controller, autofocus: true,
                maxLength: 128,
                decoration: InputDecoration(labelText: '${translate('Alias')} (${translate('Local')})', hintText: peer.hostname)),
            ]),
            actions: [
              dialogButton('Cancel', onPressed: close),
              dialogButton('OK', onPressed: () async {
                await gFFI.groupModel.setDeviceUserName(peer, controller.text);
                close();
              }),
            ],
            onCancel: close,
          );
        }).whenComplete(controller.dispose);
      },
      padding: menuPadding,
      dismissOnClicked: true,
    ));""")
        replace("flutter/lib/common.dart", "  if (peer.alias.toLowerCase().contains(searchText)) {", """  if (peerTabIndex == PeerTabIndex.group &&
      (gFFI.groupModel.deviceUserNames[peer.id] ?? '').toLowerCase().contains(searchText)) {
    return true;
  }
  if (peer.alias.toLowerCase().contains(searchText)) {""")
    if "colleagues" in profile and type(profile["colleagues"]) is not bool:
        raise ValueError("colleagues must be boolean")
    if profile.get("colleagues", False):
        from colleagues import add_colleagues
        add_colleagues(root, edits, replace, profile)
    # Validate all anchors and inputs before writing any source file.
    if not check:
        for path, text in edits.items():
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(text, encoding="utf-8")
    return len(edits)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--version", required=True)
    parser.add_argument("--profile", type=Path, required=True)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    try:
        count = apply(args.source, args.version, json.loads(args.profile.read_text(encoding="utf-8-sig")), args.check)
    except (ValueError, OSError) as exc:
        parser.exit(1, f"Customization failed: {exc}\n")
    print(f"Profile {'validated' if args.check else 'applied'}: {count} source files")
