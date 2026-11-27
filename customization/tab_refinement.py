from pathlib import Path

def add_tab_refinement(root, edits):
    page=root/'flutter/lib/common/widgets/peer_tab_page.dart'
    text=edits[page]
    text="import 'rdgen_tab_drag.dart';\n"+text
    text=text.replace('return ReorderableDragStartListener(', 'return RdgenTabDragListener(\n              activate: () { if (!isOptionFixed(kOptionPeerTabIndex)) {\n                handleTabSelection(t);\n                bind.setLocalFlutterOption(k: kOptionPeerTabIndex, v: t.toString());\n              } },')
    text=text.replace('Offset(0, 5)', 'Offset(0, 2)').replace('_rdgenTextTabs ? 5 : 0','_rdgenTextTabs ? 2 : 0')
    # Text navigation hover matches the rounded 28px active target in the reference.
    text=text.replace('borderRadius: BorderRadius.circular(6)', 'borderRadius: BorderRadius.circular(5)')
    old='''decoration: (hover.value
                            ? (selected ? decoBorder : deco)
                            : (selected ? decoBorder : null)),'''
    new='''decoration: isDesktop && _rdgenTextTabs
                          ? (hover.value ? deco : null)
                          : (hover.value ? (selected ? decoBorder : deco) : (selected ? decoBorder : null)),
                        foregroundDecoration: isDesktop && _rdgenTextTabs && selected ? decoBorder : null,'''
    if text.count(old)!=1: raise ValueError('Incompatible tab hover surface')
    text=text.replace(old,new)
    text=text.replace('await handleTabSelection(t);', 'if (model.currentTab != t) await handleTabSelection(t);')
    text=text.replace('child: InkWell(', 'child: SizedBox(height: isDesktop && _rdgenTextTabs ? 28 : null, child: InkWell(', 1)
    text=text.replace('onHover: (value) => hover.value = value,\n                    ),', 'onHover: (value) => hover.value = value,\n                    )),', 1)
    edits[page]=text
    edits[root/'flutter/lib/common/widgets/rdgen_tab_drag.dart']=Path(__file__).with_name('tab_drag.dart').read_text(encoding='utf-8-sig')
