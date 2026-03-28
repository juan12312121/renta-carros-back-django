import 'package:flutter/material.dart';
import 'package:google_maps_flutter/google_maps_flutter.dart';
import '../../data/models/trip_model.dart';
import '../../data/services/api_service.dart';
import '../../core/constants/app_colors.dart';

class MapScreen extends StatefulWidget {
  const MapScreen({Key? key}) : super(key: key);

  @override
  State<MapScreen> createState() => _MapScreenState();
}

class _MapScreenState extends State<MapScreen> {
  final ApiService _apiService = ApiService();
  GoogleMapController? _mapController;
  Set<Marker> _markers = {};
  bool _isLoading = true;

  @override
  void initState() {
    super.initState();
    _loadMarkers();
  }

  Future<void> _loadMarkers() async {
    try {
      final trips = await _apiService.fetchAssignedTrips();
      final activeTrips = trips.where((t) => t.status != 'completada').toList();

      setState(() {
        _markers = activeTrips.map((trip) {
          return Marker(
            markerId: MarkerId(trip.id),
            position: LatLng(trip.latitude, trip.longitude),
            infoWindow: InfoWindow(
              title: trip.clientName,
              snippet: '${trip.carModel} - ${trip.address}',
            ),
            icon: BitmapDescriptor.defaultMarkerWithHue(
              trip.status == 'pendiente' ? BitmapDescriptor.hueOrange : BitmapDescriptor.hueBlue,
            ),
          );
        }).toSet();
        _isLoading = false;
      });

      if (_markers.isNotEmpty && _mapController != null) {
        _centerMap();
      }
    } catch (e) {
      setState(() => _isLoading = false);
    }
  }

  void _centerMap() {
    if (_markers.isEmpty) return;
    
    // Zoom to show all markers
    double minLat = _markers.first.position.latitude;
    double maxLat = _markers.first.position.latitude;
    double minLng = _markers.first.position.longitude;
    double maxLng = _markers.first.position.longitude;

    for (var m in _markers) {
      if (m.position.latitude < minLat) minLat = m.position.latitude;
      if (m.position.latitude > maxLat) maxLat = m.position.latitude;
      if (m.position.longitude < minLng) minLng = m.position.longitude;
      if (m.position.longitude > maxLng) maxLng = m.position.longitude;
    }

    _mapController?.animateCamera(
      CameraUpdate.newLatLngBounds(
        LatLngBounds(
          southwest: LatLng(minLat - 0.01, minLng - 0.01),
          northeast: LatLng(maxLat + 0.01, maxLng + 0.01),
        ),
        50,
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text('Rutas de Entrega'),
        actions: [
          IconButton(
            icon: const Icon(Icons.refresh),
            onPressed: _loadMarkers,
          ),
        ],
      ),
      body: _isLoading
          ? const Center(child: CircularProgressIndicator())
          : GoogleMap(
              initialCameraPosition: const CameraPosition(
                target: LatLng(19.432608, -99.133209), // CDMX default
                zoom: 12,
              ),
              markers: _markers,
              myLocationEnabled: true,
              myLocationButtonEnabled: true,
              onMapCreated: (controller) {
                _mapController = controller;
                if (_markers.isNotEmpty) _centerMap();
              },
            ),
    );
  }
}
