# Rent-A-Car System - Project Overview

Este proyecto es una plataforma integral de gestión de alquiler de vehículos que conecta a **Administradores**, **Clientes** y **Choferes** en un ecosistema premium y eficiente.

## 🚀 Arquitectura Tecnológica

- **Frontend:** Vue 3 (Composition API) + Vite.
- **Styling:** CSS variables con sistema de temas (Light Mode prioritario para clientes).
- **Backend:** Django REST Framework.
- **Base de Datos:** PostgreSQL (Aiven).
- **Iconografía:** Lucide Vue Next.

## 👥 Modulos y Roles

### 1. Modulo de Cliente (Terminado)
- **Catálogo Premium:** Exploración de flota con filtros avanzados.
- **Detalle de Vehículo:** Especificaciones técnicas y visualización de imágenes.
- **Flujo de Reserva:** Sistema de reserva multi-paso con cálculo de tarifas en tiempo real.
- **Perfil de Usuario:** Gestión de documentos, historial de rentas y seguimiento de estados.

### 2. Modulo de Administrador (En Refinamiento)
- **Dashboard Operativo:** Métricas clave de flota y rentas.
- **Gestión de Flota:** CRUD completo de vehículos y gestión de estados.
- **Mantenimiento:** Seguimiento de servicios técnicos y reparaciones.
- **Finanzas:** Reportes de ingresos y gestión de pagos.
- **Usuarios:** Control de accesos y verificación de documentos.

### 3. Modulo de Chofer (Pendiente)
- **Interfaz Móvil:** Diseñada para uso en dispositivos móviles.
- **Asignaciones:** Recepción de rutas y vehículos asignados.
- **Bitácora:** Registro de entregas y estados del vehículo.

## 🛠️ Próximos Pasos (Finalización del Frontend)

1. **Refinamiento Admin:** Pulir las vistas de Finanzas, Reservas y Notificaciones para que coincidan con la estética premium del cliente.
2. **Modulo Chofer:** Implementar la estructura base de la vista móvil para choferes.
3. **Sincronización:** Asegurar que todos los formularios tengan validación y feedback visual (toasts/modales).

---
*Desarrollado con enfoque en excelencia visual y rendimiento.*
