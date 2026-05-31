import 'package:dio/dio.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../auth/auth_service.dart';

const _baseUrl = String.fromEnvironment(
  'API_URL',
  defaultValue: 'https://api.kitmunicator.intern.phudevelopement.xyz',
);

Dio _buildDio(String? token) {
  final dio = Dio(BaseOptions(
    baseUrl: _baseUrl,
    connectTimeout: const Duration(seconds: 10),
    receiveTimeout: const Duration(seconds: 30),
    headers: {
      if (token != null) 'Authorization': 'Bearer $token',
      'Content-Type': 'application/json',
    },
  ));
  return dio;
}

final apiClientProvider = Provider<Dio>((ref) {
  final token = ref.watch(authProvider).accessToken;
  return _buildDio(token);
});
