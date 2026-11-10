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
                dialogButton('Retry',
                    onPressed: () => reconnect(dialogManager, sessionId, false),
                    isOutline: true),
                dialogButton('Connect via relay',
                    onPressed: () => reconnect(dialogManager, sessionId, true),
                    buttonStyle: style),
                dialogButton('Always connect via relay',
                    onPressed: () async {
                      try {
                        await bind.mainSetPeerOption(id: peerId,
                            key: kOptionForceAlwaysRelay,
                            value: bool2option(kOptionForceAlwaysRelay, true));
                        reconnect(dialogManager, sessionId, true);
                      } catch (error) {
                        showToast('${translate('Error')}: $error');
                      }
                    },
                    isOutline: true),
              ],
            ),
          ],
        ),
        onCancel: onClose,
      );
