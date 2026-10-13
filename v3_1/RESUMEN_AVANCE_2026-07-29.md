# Resumen de avance — Desafío Millonario

Fecha: 29 de julio de 2026.

## Estado alcanzado

El código de la revisión **V3.1.3** quedó terminado y pasó **46 pruebas
automatizadas**.

Cambios principales realizados:

- Acceso móvil simplificado mediante `http://IP:8787/`, sin código de sala en
  la dirección.
- Compatibilidad con Chrome móvil sobre una red local sin Internet.
- Un solo botón cierra la sala e inicia inmediatamente la clasificación.
- Pregunta y alternativas aparecen en la pantalla principal.
- Los pulsadores A–D se activan automáticamente durante 30 segundos.
- Al terminar el tiempo aparece el gráfico de resultados.
- Se eliminaron el botón intermedio, «Cerrar ahora» y el desempate.
- Se conservan únicamente dos jugadores clasificados.
- Si faltan aciertos, los cupos se completan con participantes disponibles.
- Los demás teléfonos permanecen conectados como público.
- Durante las rondas, el público solo recibe A–D cuando se activa el comodín
  Consulta con el público, durante 15 segundos.
- Se corrigieron pulsadores que quedaban detenidos después de responder o
  perder momentáneamente la conexión.
- Se agregó **Repetir juego**: conserva los teléfonos enrolados, restablece
  todos los roles y prepara una clasificación nueva.

## Validaciones realizadas

- Flujo completo de dos rondas.
- Tres sesiones móviles simultáneas.
- Dos jugadores seleccionados y un teléfono disponible como público.
- Activación exclusiva del comodín para el público.
- Repetición del juego sin volver a escanear el QR.
- Control visual de la clasificación de 30 segundos y de los dos jugadores.
- La V2 continúa intacta.
- Las tres capturas de errores reportadas están preservadas en
  `v3_1/docs/errores_reportados`.

## Continuación del 30 de julio de 2026

La compilación y validación pendientes quedaron terminadas:

- ejecutable identificado por Windows como **V3.1.3**;
- **46 pruebas automatizadas** superadas;
- prueba portable superada desde una copia temporal independiente;
- carpeta final preparada para copiar completa a un pendrive;
- V2 comprobada sin modificaciones;
- tamaño total de la carpeta portable: **243,58 MiB**;
- SHA-256 del ejecutable:
  `AAA75EB4FA82767D76C1F683C03C5C4BED690644CAE313A7C646C3EB1043203A`.

La entrega se encuentra en:

```text
release\Millonario_Educativo_V3_1
```

## Actualización V3.1.4 — 30 de julio de 2026

- El pulsador móvil adoptó una identidad visual genérica y reutilizable.
- Se agregaron ocho avatares seleccionables durante el enrolamiento.
- El avatar acompaña al alias en la pantalla del anfitrión.
- Se conservan la clasificación, las rondas, el público y la repetición.
- La revisión superó 47 pruebas y la prueba portable.
- Tamaño final: **243,76 MiB**, incluida la vista previa del pulsador.
- SHA-256:
  `6522C30AE1217219462AF24797B1A98243ED7070D095505E75AB032C53F4D870`.
