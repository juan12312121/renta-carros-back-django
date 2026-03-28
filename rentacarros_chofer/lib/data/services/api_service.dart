import 'dart:convert';
import 'package:http/http.dart' as http;
import 'package:shared_preferences/shared_preferences.dart';
import '../models/trip_model.dart';

class ApiService {
  static const String baseUrl = 'https://renta-carros-back-django.onrender.com/api';

  Future<Map<String, String>> _getHeaders() async {
    final prefs = await SharedPreferences.getInstance();
    final token = prefs.getString('access_token');
    return {
      'Content-Type': 'application/json',
      'Authorization': 'Bearer $token',
    };
  }

  // Obtener viajes asignados reals desde Django
  Future<List<TripModel>> fetchAssignedTrips() async {
    try {
      final headers = await _getHeaders();
      final response = await http.get(
        Uri.parse('$baseUrl/chofer/asignaciones/'), 
        headers: headers,
      );
      
      if (response.statusCode == 200) {
        final Map<String, dynamic> data = json.decode(response.body);
        final List<dynamic> assignments = data['asignaciones'] ?? [];
        return assignments.map((json) => TripModel.fromJson(json)).toList();
      } else {
        throw Exception('Error al cargar los viajes (${response.statusCode})');
      }
    } catch (e) {
      print('Error en fetchAssignedTrips: $e');
      throw Exception('Error de conexión: $e');
    }
  }

  // Actualizar estado de viaje (pendiente -> en_curso -> completada)
  Future<bool> updateTripStatus(String tripId, String newStatus) async {
    try {
      final headers = await _getHeaders();
      // Mapeo de estados de Flutter UI a Django Backend
      String djangoStatus = newStatus;
      if (newStatus == 'started' || newStatus == 'on_way') djangoStatus = 'en_curso';
      if (newStatus == 'finished') djangoStatus = 'completada';

      final response = await http.patch(
        Uri.parse('$baseUrl/chofer/asignaciones/$tripId/estado/'),
        headers: headers,
        body: json.encode({'estado': djangoStatus}),
      );
      
      return response.statusCode == 200;
    } catch (e) {
      print('Error en updateTripStatus: $e');
      return false;
    }
  }
}
