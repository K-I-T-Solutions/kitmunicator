import 'package:firebase_core/firebase_core.dart';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import 'core/auth/auth_service.dart';
import 'core/push/push_service.dart';
import 'core/sip/sip_credentials.dart';
import 'core/sip/sip_service.dart';
import 'screens/login_screen.dart';
import 'screens/dialer_screen.dart';
import 'theme/kit_theme.dart';
import 'widgets/incoming_call_overlay.dart';

void main() async {
  WidgetsFlutterBinding.ensureInitialized();
  await Firebase.initializeApp();
  await PushService.instance.init();
  runApp(const ProviderScope(child: KitmunicatorApp()));
}

final _router = GoRouter(
  routes: [
    GoRoute(path: '/', builder: (_, __) => const AppShell()),
  ],
);

class KitmunicatorApp extends StatelessWidget {
  const KitmunicatorApp({super.key});

  @override
  Widget build(BuildContext context) {
    return MaterialApp.router(
      title: 'KITmunicator',
      theme: kitTheme,
      routerConfig: _router,
      debugShowCheckedModeBanner: false,
    );
  }
}

class AppShell extends ConsumerWidget {
  const AppShell({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final auth = ref.watch(authProvider);

    if (!auth.isAuthenticated) return const LoginScreen();

    return Stack(
      children: [
        Scaffold(
          appBar: AppBar(
            title: Row(
              children: [
                Image.asset('assets/images/kitmunicator_icon.png', height: 28),
                const SizedBox(width: 8),
                RichText(
                  text: const TextSpan(
                    children: [
                      TextSpan(
                        text: 'KIT',
                        style: TextStyle(
                          fontFamily: 'Montserrat',
                          fontWeight: FontWeight.w800,
                          fontSize: 20,
                          color: Color(0xFF06B6D4),
                        ),
                      ),
                      TextSpan(
                        text: 'municator',
                        style: TextStyle(
                          fontFamily: 'Montserrat',
                          fontWeight: FontWeight.w400,
                          fontSize: 20,
                          color: Colors.white,
                        ),
                      ),
                    ],
                  ),
                ),
              ],
            ),
            actions: [
              IconButton(
                icon: const Icon(Icons.logout, size: 20),
                tooltip: 'Abmelden',
                onPressed: () => ref.read(authProvider.notifier).logout(),
              ),
            ],
          ),
          body: const _DialerWithSip(),
        ),
        const IncomingCallOverlay(),
      ],
    );
  }
}

class _DialerWithSip extends ConsumerWidget {
  const _DialerWithSip();

  static const _sipDomain = String.fromEnvironment('SIP_DOMAIN', defaultValue: 'kitmunicator.intern.phudevelopement.xyz');
  static const _wsServer  = String.fromEnvironment('SIP_WS_SERVER', defaultValue: 'wss://sip.kitmunicator.intern.phudevelopement.xyz/ws');

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final auth  = ref.watch(authProvider);
    final sip   = ref.watch(sipProvider);
    final creds = ref.watch(sipCredentialsProvider);

    if (creds.hasError) {
      return const Center(child: Text('Kein SIP-Account eingerichtet oder Server nicht erreichbar'));
    }

    final account = creds.valueOrNull;
    if (account != null && sip.callState == PhoneState.idle) {
      WidgetsBinding.instance.addPostFrameCallback((_) {
        ref.read(sipProvider.notifier).setup(
          sipUri: 'sip:${account.username}@$_sipDomain',
          password: account.password,
          wsServer: _wsServer,
          displayName: auth.displayName ?? '',
        );
      });
    }

    return const DialerScreen();
  }
}
