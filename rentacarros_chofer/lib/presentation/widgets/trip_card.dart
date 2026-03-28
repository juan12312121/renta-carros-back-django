import 'package:flutter/material.dart';
import '../../core/constants/app_colors.dart';
import '../../data/models/trip_model.dart';
import '../screens/trip_detail_screen.dart'; // We'll create this later

class TripCard extends StatelessWidget {
  final TripModel trip;

  const TripCard({Key? key, required this.trip}) : super(key: key);

  Color _getStatusColor(String status) {
    switch (status) {
      case 'pending': return AppColors.statusPending;
      case 'on_way': return AppColors.statusOnWay;
      case 'started': return AppColors.statusStarted;
      case 'finished': return AppColors.statusFinished;
      default: return AppColors.textSecondary;
    }
  }

  String _getStatusText(String status) {
    switch (status) {
      case 'pending': return 'Pendiente';
      case 'on_way': return 'En camino';
      case 'started': return 'Iniciado / Entregado';
      case 'finished': return 'Finalizado';
      default: return 'Desconocido';
    }
  }

  @override
  Widget build(BuildContext context) {
    return Card(
      margin: const EdgeInsets.symmetric(horizontal: 16, vertical: 8),
      child: InkWell(
        borderRadius: BorderRadius.circular(16),
        onTap: () {
          Navigator.push(
            context,
            MaterialPageRoute(
              builder: (context) => TripDetailScreen(trip: trip),
            ),
          );
        },
        child: Padding(
          padding: const EdgeInsets.all(16.0),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Row(
                mainAxisAlignment: MainAxisAlignment.spaceBetween,
                children: [
                  Text(
                    trip.carModel,
                    style: const TextStyle(
                      fontSize: 18,
                      fontWeight: FontWeight.bold,
                    ),
                  ),
                  Container(
                    padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 6),
                    decoration: BoxDecoration(
                      color: _getStatusColor(trip.status).withOpacity(0.1),
                      borderRadius: BorderRadius.circular(20),
                    ),
                    child: Text(
                      _getStatusText(trip.status),
                      style: TextStyle(
                        color: _getStatusColor(trip.status),
                        fontWeight: FontWeight.w600,
                        fontSize: 12,
                      ),
                    ),
                  ),
                ],
              ),
              const SizedBox(height: 12),
              Row(
                children: [
                  const Icon(Icons.person, size: 20, color: AppColors.textSecondary),
                  const SizedBox(width: 8),
                  Text(
                    trip.clientName,
                    style: const TextStyle(color: AppColors.textSecondary, fontSize: 16),
                  ),
                ],
              ),
              const SizedBox(height: 8),
              Row(
                children: [
                  const Icon(Icons.location_on, size: 20, color: AppColors.textSecondary),
                  const SizedBox(width: 8),
                  Expanded(
                    child: Text(
                      trip.address,
                      style: const TextStyle(color: AppColors.textSecondary, fontSize: 14),
                      maxLines: 1,
                      overflow: TextOverflow.ellipsis,
                    ),
                  ),
                ],
              ),
            ],
          ),
        ),
      ),
    );
  }
}
