      return CustomAlertDialog(
        title: null,
        content: Column(
          mainAxisSize: MainAxisSize.min,
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: [
            Row(
              children: [
                Expanded(child: Text(translate(title),
                    style: Theme.of(context).textTheme.titleLarge)),
                IconButton(
                  tooltip: translate('Close'),
                  icon: const Icon(Icons.close),
                  onPressed: onClose,
                ),
              ],
            ),
            const SizedBox(height: 12),
            createDialogContent(text2),
            const SizedBox(height: 24),
            Wrap(
              spacing: 12,
              runSpacing: 12,
              alignment: WrapAlignment.end,
              children: [
                dialogButton('Retry directly',
                    onPressed: () => reconnect(dialogManager, sessionId, false),
                    isOutline: true),
                dialogButton('Connect via relay',
                    onPressed: () async {
                      try {
                        if (rememberRelay) {
                          await bind.mainSetPeerOption(id: peerId,
                              key: kOptionForceAlwaysRelay,
                              value: bool2option(kOptionForceAlwaysRelay, true));
                        }
                        reconnect(dialogManager, sessionId, true);
                      } catch (error) {
                        showToast('${translate('Error')}: $error');
                      }
                    },
                    buttonStyle: style),
              ],
            ),
            const SizedBox(height: 8),
            CheckboxListTile(
              contentPadding: EdgeInsets.zero,
              controlAffinity: ListTileControlAffinity.leading,
              title: Text(translate('Always use relay for this device')),
              value: rememberRelay,
              onChanged: (value) => setState(() => rememberRelay = value ?? false),
            ),
          ],
        ),
        onCancel: onClose,
      );
