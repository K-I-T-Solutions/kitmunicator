import 'package:flutter/material.dart';

const _navy  = Color(0xFF0A1628);
const _cyan  = Color(0xFF06B6D4);
const _orange = Color(0xFFFF6B35);
const _surface = Color(0xFF1A1D27);
const _surface2 = Color(0xFF22263A);
const _border  = Color(0xFF2E3350);
const _textMuted = Color(0xFF8892B0);

final kitTheme = ThemeData(
  brightness: Brightness.dark,
  scaffoldBackgroundColor: const Color(0xFF0F1117),
  colorScheme: const ColorScheme.dark(
    primary: _cyan,
    secondary: _orange,
    surface: _surface,
    onPrimary: _navy,
    onSurface: Colors.white,
  ),
  fontFamily: 'Montserrat',
  appBarTheme: const AppBarTheme(
    backgroundColor: _surface,
    foregroundColor: Colors.white,
    elevation: 0,
    titleTextStyle: TextStyle(
      fontFamily: 'Montserrat',
      fontWeight: FontWeight.w600,
      fontSize: 18,
      color: Colors.white,
    ),
  ),
  navigationRailTheme: const NavigationRailThemeData(
    backgroundColor: _surface,
    selectedIconTheme: IconThemeData(color: _cyan),
    unselectedIconTheme: IconThemeData(color: _textMuted),
    selectedLabelTextStyle: TextStyle(color: _cyan, fontFamily: 'Montserrat'),
    unselectedLabelTextStyle: TextStyle(color: _textMuted, fontFamily: 'Montserrat'),
  ),
  inputDecorationTheme: InputDecorationTheme(
    filled: true,
    fillColor: _surface2,
    border: OutlineInputBorder(
      borderRadius: BorderRadius.circular(8),
      borderSide: const BorderSide(color: _border),
    ),
    enabledBorder: OutlineInputBorder(
      borderRadius: BorderRadius.circular(8),
      borderSide: const BorderSide(color: _border),
    ),
    focusedBorder: OutlineInputBorder(
      borderRadius: BorderRadius.circular(8),
      borderSide: const BorderSide(color: _cyan),
    ),
  ),
  elevatedButtonTheme: ElevatedButtonThemeData(
    style: ElevatedButton.styleFrom(
      backgroundColor: _cyan,
      foregroundColor: _navy,
      shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(8)),
      textStyle: const TextStyle(fontFamily: 'Montserrat', fontWeight: FontWeight.w700),
    ),
  ),
  extensions: const [KitColors()],
);

class KitColors extends ThemeExtension<KitColors> {
  const KitColors();

  final Color navy   = _navy;
  final Color cyan   = _cyan;
  final Color orange = _orange;
  final Color surface = _surface;
  final Color surface2 = _surface2;
  final Color border  = _border;
  final Color textMuted = _textMuted;

  @override
  KitColors copyWith() => const KitColors();

  @override
  KitColors lerp(KitColors? other, double t) => const KitColors();
}
