import 'package:flutter/material.dart';
import '../../core/constants/app_colors.dart';
import '../../data/models/trip_model.dart';
import '../../data/services/api_service.dart';

class TripDetailScreen extends StatefulWidget {
  final TripModel trip;

  const TripDetailScreen({Key? key, required this.trip}) : super(key: key);

  @override
  State<TripDetailScreen> createState() => _TripDetailScreenState();
}

class _TripDetailScreenState extends State<TripDetailScreen> {
  final ApiService _apiService = ApiService();
  bool _isLoading = false;
  late String _currentStatus;

  @override
  void initState() {
    super.initState();
    _currentStatus = widget.trip.status;
  }

  Future<void> _updateStatus(String newStatus) async {
    setState(() {
      _isLoading = true;
    });

    bool success = await _apiService.updateTripStatus(widget.trip.id, newStatus);
    
    if (!mounted) return;

    setState(() {
      _isLoading = false;
      if (success) {
        _currentStatus = newStatus;
      }
    });

    ScaffoldMessenger.of(context).showSnackBar(
      SnackBar(
        content: Text(
          success ? 'Estado actualizado correctamente' : 'Error al actualizar',
        ),
        backgroundColor: success ? AppColors.secondary : Colors.red,
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text('Detalle de Renta'),
      ),
      body: SingleChildScrollView(
        padding: const EdgeInsets.all(16.0),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            _buildInfoCard(),
            const SizedBox(height: 24),
            _buildActionButtons(),
          ],
        ),
      ),
    );
  }

  Widget _buildInfoCard() {
    return Card(
      elevation: 3,
      child: Padding(
        padding: const EdgeInsets.all(16.0),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            const Text(
              'Información del Cliente',
              style: TextStyle(fontSize: 18, fontWeight: FontWeight.bold, color: AppColors.primary),
            ),
            const Divider(),
            ListTile(
              leading: const Icon(Icons.person, color: AppColors.primaryLight),
              title: const Text('Cliente'),
              subtitle: Text(widget.trip.clientName, style: const TextStyle(fontWeight: FontWeight.w500)),
              contentPadding: EdgeInsets.zero,
            ),
            ListTile(
              leading: const Icon(Icons.directions_car, color: AppColors.primaryLight),
              title: const Text('Vehículo'),
              subtitle: Text(widget.trip.carModel),
              contentPadding: EdgeInsets.zero,
            ),
            ListTile(
              leading: const Icon(Icons.location_on, color: AppColors.primaryLight),
              title: const Text('Destino de entrega'),
              subtitle: Text(widget.trip.address),
              contentPadding: EdgeInsets.zero,
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildActionButtons() {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.stretch,
      children: [
        const Text(
          'Actualizar Estado',
          style: TextStyle(fontSize: 18, fontWeight: FontWeight.bold),
        ),
        const SizedBox(height: 16),
        if (_isLoading)
          const Center(child: CircularProgressIndicator())
        else
          ...[
            _buildStatusButton('on_way', 'En Camino al Cliente', Icons.directions_car),
            const SizedBox(height: 12),
            _buildStatusButton('started', 'Auto Entregado (Iniciado)', Icons.check_circle_outline),
            const SizedBox(height: 12),
            _buildStatusButton('finished', 'Viaje Finalizado (Devuelto)', Icons.flag),
          ]
      ],
    );
  }

  Widget _buildStatusButton(String statusValue, String text, IconData icon) {
    bool isCurrent = _currentStatus == statusValue;
    return ElevatedButton.icon(
      style: ElevatedButton.styleFrom(
        backgroundColor: isCurrent ? AppColors.secondary : AppColors.primary,
      ),
      onPressed: isCurrent ? null : () => _updateStatus(statusValue),
      icon: Icon(icon, color: Colors.white),
      label: Text(
        isCurrent ? '$text (Actual)' : text,
        style: const TextStyle(fontSize: 16),
      ),
    );
  }
}
