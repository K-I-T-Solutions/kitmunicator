import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../core/sip/sip_service.dart';
import '../theme/kit_theme.dart';

class DialerScreen extends ConsumerStatefulWidget {
  const DialerScreen({super.key});

  @override
  ConsumerState<DialerScreen> createState() => _DialerScreenState();
}

class _DialerScreenState extends ConsumerState<DialerScreen> {
  final _controller = TextEditingController();

  void _keyPress(String digit) {
    setState(() => _controller.text += digit);
  }

  void _backspace() {
    final t = _controller.text;
    if (t.isNotEmpty) setState(() => _controller.text = t.substring(0, t.length - 1));
  }

  @override
  void dispose() {
    _controller.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final sip = ref.watch(sipProvider);
    final colors = Theme.of(context).extension<KitColors>()!;
    final isConnected = sip.callState == PhoneState.connected;
    final isCalling   = sip.callState == PhoneState.calling;
    final isIncoming  = sip.callState == PhoneState.incoming;

    return Padding(
      padding: const EdgeInsets.symmetric(horizontal: 24, vertical: 16),
      child: Column(
        children: [
          // Status-Badge
          _StatusBadge(callState: sip.callState),
          const SizedBox(height: 24),

          // Anruf aktiv: Nummer anzeigen
          if (isConnected || isCalling || isIncoming) ...[
            Text(
              sip.remoteNumber ?? '',
              style: const TextStyle(fontSize: 28, fontWeight: FontWeight.w700, letterSpacing: 2),
            ),
            const SizedBox(height: 8),
            Text(
              isConnected ? 'Verbunden' : isCalling ? 'Wählt…' : 'Eingehend',
              style: TextStyle(color: colors.textMuted, fontSize: 14),
            ),
            const Spacer(),
            _ActiveCallControls(isMuted: sip.isMuted),
          ] else ...[
            // Eingabefeld
            TextField(
              controller: _controller,
              readOnly: true,
              textAlign: TextAlign.center,
              style: const TextStyle(fontSize: 28, letterSpacing: 4, fontWeight: FontWeight.w300),
              decoration: const InputDecoration(border: InputBorder.none),
            ),
            const SizedBox(height: 16),

            // Keypad
            _Keypad(onDigit: _keyPress, onBackspace: _backspace),
            const SizedBox(height: 24),

            // Anruf-Button
            GestureDetector(
              onTap: sip.isRegistered && _controller.text.isNotEmpty
                  ? () => ref.read(sipProvider.notifier).call(_controller.text)
                  : null,
              child: Container(
                width: 68, height: 68,
                decoration: BoxDecoration(
                  color: sip.isRegistered ? colors.cyan : colors.textMuted,
                  shape: BoxShape.circle,
                ),
                child: const Icon(Icons.call, color: Colors.white, size: 30),
              ),
            ),
          ],
          const SizedBox(height: 16),
        ],
      ),
    );
  }
}

class _ActiveCallControls extends ConsumerWidget {
  final bool isMuted;
  const _ActiveCallControls({required this.isMuted});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final colors = Theme.of(context).extension<KitColors>()!;
    return Row(
      mainAxisAlignment: MainAxisAlignment.spaceEvenly,
      children: [
        _ControlBtn(
          icon: isMuted ? Icons.mic_off : Icons.mic,
          label: isMuted ? 'Stummlos' : 'Stumm',
          active: isMuted,
          onTap: () => ref.read(sipProvider.notifier).toggleMute(),
        ),
        GestureDetector(
          onTap: () => ref.read(sipProvider.notifier).hangup(),
          child: Container(
            width: 68, height: 68,
            decoration: const BoxDecoration(color: Colors.red, shape: BoxShape.circle),
            child: const Icon(Icons.call_end, color: Colors.white, size: 30),
          ),
        ),
        _ControlBtn(
          icon: Icons.dialpad,
          label: 'Tastenfeld',
          active: false,
          onTap: () {},
        ),
      ],
    );
  }
}

class _ControlBtn extends StatelessWidget {
  final IconData icon;
  final String label;
  final bool active;
  final VoidCallback onTap;
  const _ControlBtn({required this.icon, required this.label, required this.active, required this.onTap});

  @override
  Widget build(BuildContext context) {
    final colors = Theme.of(context).extension<KitColors>()!;
    return GestureDetector(
      onTap: onTap,
      child: Column(
        mainAxisSize: MainAxisSize.min,
        children: [
          Container(
            width: 56, height: 56,
            decoration: BoxDecoration(
              color: active ? colors.cyan.withValues(alpha: 0.2) : colors.surface2,
              shape: BoxShape.circle,
            ),
            child: Icon(icon, color: active ? colors.cyan : Colors.white),
          ),
          const SizedBox(height: 6),
          Text(label, style: TextStyle(fontSize: 11, color: colors.textMuted)),
        ],
      ),
    );
  }
}

class _Keypad extends StatelessWidget {
  final void Function(String) onDigit;
  final VoidCallback onBackspace;

  const _Keypad({required this.onDigit, required this.onBackspace});

  static const _keys = [
    ['1', '2', '3'],
    ['4', '5', '6'],
    ['7', '8', '9'],
    ['*', '0', '#'],
  ];

  @override
  Widget build(BuildContext context) {
    return Column(
      children: _keys.map((row) => Padding(
        padding: const EdgeInsets.symmetric(vertical: 4),
        child: Row(
          mainAxisAlignment: MainAxisAlignment.spaceEvenly,
          children: row.map((k) => _KeyButton(digit: k, onTap: () => onDigit(k))).toList(),
        ),
      )).toList(),
    );
  }
}

class _KeyButton extends StatelessWidget {
  final String digit;
  final VoidCallback onTap;
  const _KeyButton({required this.digit, required this.onTap});

  @override
  Widget build(BuildContext context) {
    return GestureDetector(
      onTap: onTap,
      child: Container(
        width: 72, height: 72,
        decoration: BoxDecoration(
          color: Theme.of(context).extension<KitColors>()!.surface2,
          shape: BoxShape.circle,
        ),
        alignment: Alignment.center,
        child: Text(digit, style: const TextStyle(fontSize: 24, fontWeight: FontWeight.w300)),
      ),
    );
  }
}

class _StatusBadge extends StatelessWidget {
  final PhoneState callState;
  const _StatusBadge({required this.callState});

  @override
  Widget build(BuildContext context) {
    final (color, label) = switch (callState) {
      PhoneState.registered  => (Colors.green,  'Bereit'),
      PhoneState.registering => (Colors.orange, 'Registriert…'),
      PhoneState.calling     => (Colors.blue,   'Wählt…'),
      PhoneState.incoming    => (Colors.orange, 'Eingehend'),
      PhoneState.connected   => (Colors.green,  'Im Gespräch'),
      PhoneState.error       => (Colors.red,    'Fehler'),
      _                     => (Colors.grey,   'Nicht verbunden'),
    };
    return Row(
      mainAxisSize: MainAxisSize.min,
      children: [
        Container(width: 8, height: 8, decoration: BoxDecoration(color: color, shape: BoxShape.circle)),
        const SizedBox(width: 6),
        Text(label, style: TextStyle(fontSize: 12, color: Theme.of(context).extension<KitColors>()!.textMuted)),
      ],
    );
  }
}
