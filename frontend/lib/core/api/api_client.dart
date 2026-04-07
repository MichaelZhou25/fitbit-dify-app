import 'package:dio/dio.dart';

class ApiClient {
  ApiClient(String baseUrl)
    : dio = Dio(
        BaseOptions(
          baseUrl: baseUrl,
          connectTimeout: const Duration(seconds: 20),
          receiveTimeout: const Duration(seconds: 30),
          sendTimeout: const Duration(seconds: 30),
          headers: const {'Content-Type': 'application/json'},
        ),
      );

  final Dio dio;
}
