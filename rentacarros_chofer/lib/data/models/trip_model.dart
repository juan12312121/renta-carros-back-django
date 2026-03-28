class TripModel {
  final String id;
  final String clientName;
  final String carModel;
  final String address;
  final DateTime assignedAt;
  final String status; // 'pending', 'on_way', 'started', 'finished'
  final double latitude;
  final double longitude;

  TripModel({
    required this.id,
    required this.clientName,
    required this.carModel,
    required this.address,
    required this.assignedAt,
    required this.status,
    required this.latitude,
    required this.longitude,
  });

  factory TripModel.fromJson(Map<String, dynamic> json) {
    final client = json['cliente'] as Map<String, dynamic>?;
    final vehicle = json['vehiculo'] as Map<String, dynamic>?;

    return TripModel(
      id: json['id'].toString(),
      clientName: client?['nombre_completo'] ?? 'Cliente Desconocido',
      carModel: vehicle != null 
          ? '${vehicle['marca']} ${vehicle['modelo']}' 
          : 'Vehículo',
      address: json['lugar_recogida'] ?? json['address'] ?? 'Sin dirección',
      assignedAt: json['fecha_inicio'] != null 
          ? DateTime.parse(json['fecha_inicio']) 
          : DateTime.now(),
      status: json['estado'] ?? 'pendiente',
      latitude: json['latitud_recogida'] != null 
          ? double.parse(json['latitud_recogida'].toString()) 
          : 0.0,
      longitude: json['longitud_recogida'] != null 
          ? double.parse(json['longitud_recogida'].toString()) 
          : 0.0,
    );
  }

  Map<String, dynamic> toJson() {
    return {
      'id': id,
      'clientName': clientName,
      'carModel': carModel,
      'address': address,
      'assignedAt': assignedAt.toIso8601String(),
      'status': status,
      'latitude': latitude,
      'longitude': longitude,
    };
  }
}
