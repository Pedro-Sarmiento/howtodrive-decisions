# Preparación del repositorio público

Revisión: 2026-10-28.

- README con instalación, controles, arquitectura, créditos a RunOnWeb de midudev y límites del prototipo.
- Panel simplificado: micrófono, transcripción, decisión de Kev y sus dos probabilidades. Sin HUD ni mensajes promocionales.
- Activación explícita de voz; espacio inicia y termina la grabación.
- Comentarios históricos reducidos; se conservan explicaciones necesarias sobre compatibilidad y geometría.
- Dos pruebas de regresión: las negaciones no llaman al modelo; el umbral decide cuándo aplicar una acción.
- CI con instalación reproducible, pruebas y build.
- Sin coincidencias en la búsqueda de patrones comunes de credenciales en el historial Git. No equivale a una auditoría exhaustiva.
- Referencias visuales locales y configuración privada excluidas mediante `.gitignore`.
- Las eliminaciones de `lab/` ya estaban presentes al comenzar esta preparación.

Pendientes antes del despliegue: validar más voces y equipos, revisar el tamaño de los WASM y confirmar los límites del alojamiento. La publicación de GitHub no despliega automáticamente una demo web.
