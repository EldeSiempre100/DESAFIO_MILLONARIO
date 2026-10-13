# Informe de cierre — Millonario educativo V1

Fecha de cierre técnico: 28 de julio de 2026.

## Estado

La V1 quedó construida como una aplicación de escritorio Windows, privada,
educativa, editable y portable. La versión lista para copiar se encuentra en:

`release\Millonario_Educativo_V1\`

Se debe copiar la carpeta completa. El archivo de inicio es:

`MillonarioEducativo.exe`

## Trabajo realizado

- Se incorporó un menú inicial con título, **Iniciar juego** y
  **Editar preguntas**.
- Se recuperaron y validaron las seis preguntas del PPTX.
- Se separó el contenido editable de la lógica del juego.
- Se construyó un editor para crear, duplicar, eliminar, ordenar y modificar
  preguntas y respuestas.
- Se incorporaron conteo de preguntas, aciertos y cierre de partida.
- Se mantuvieron los tres comodines y sus sonidos.
- Los comodines quedan consumidos durante una partida.
- Se incorporaron validaciones de longitud y respuesta correcta.
- El guardado genera tres respaldos rotativos.
- Si el archivo principal se daña, la aplicación intenta recuperarlo desde un
  respaldo.
- Se reconstruyó el fondo en 16:9 con mejor definición y sin paneles
  duplicados; los paneles se dibujan en la interfaz.
- Se creó un icono propio para el ejecutable.
- Se optimizó el empaquetado, excluyendo WebEngine y otros componentes
  pesados que no utiliza el juego.
- Se dejó registrada la idea de V2 en `ROADMAP_V2.md`.

## Validaciones realizadas

- 18 pruebas automáticas superadas.
- Menú verificado en el ejecutable compilado.
- Juego verificado en el ejecutable compilado.
- Editor verificado en el ejecutable compilado.
- Copia completa ejecutada correctamente desde otra carpeta temporal,
  simulando el cambio de ubicación de un pendrive.
- No se incluyeron las DLL principales de WebEngine.

## Tamaño

- PowerPoint original: 9,3 MB.
- Carpeta portable V1: 204,2 MB.
- Ejecutable principal: 6,6 MB.
- Prototipo compilado anterior: aproximadamente 430 MB.

El ejecutable necesita los archivos que lo acompañan; por eso no se debe copiar
solo el `.exe`. La reducción de 430 MB a 204,2 MB mantiene el soporte gráfico,
multimedia y la compatibilidad de Qt.

SHA-256 del ejecutable:

`31CAD04CCE502A74A41C3029CE2AC9EFB2BFA1A7254BF6C5C50CE698BC443712`

## Uso desde un pendrive

1. Copiar `release\Millonario_Educativo_V1` completa al pendrive.
2. Abrir la carpeta copiada.
3. Ejecutar `MillonarioEducativo.exe`.
4. Cerrar el juego antes de retirar el pendrive.

El pendrive debe permitir escritura para guardar cambios en las preguntas y
crear respaldos. Un equipo corporativo puede bloquear ejecutables no firmados;
eso depende de sus políticas de seguridad.

## Continuar manualmente si no está disponible Codex

Todo el trabajo está guardado en esta carpeta local; no depende de la
conversación.

### Abrir y ejecutar desde VS Code

1. Abrir esta carpeta completa en VS Code.
2. Abrir una terminal PowerShell.
3. Ejecutar:

```powershell
.\.venv\Scripts\python.exe main.py
```

### Modificar preguntas sin programar

1. Abrir la aplicación.
2. Seleccionar **Editar preguntas**.
3. Elegir una pregunta o crear una nueva.
4. Modificar el enunciado, las cuatro respuestas y la respuesta correcta.
5. Pulsar **Guardar cambios**.

El banco se guarda en `projects\demo.juego`.

### Ejecutar las pruebas

```powershell
.\.venv\Scripts\python.exe -m pytest -q
```

El resultado esperado actualmente es `18 passed`.

### Volver a construir la carpeta portable

```powershell
.\tools\build_v1.ps1
```

La construcción puede tardar varios minutos. Al finalizar reemplaza la carpeta
`release\Millonario_Educativo_V1`.

### Verificar la portabilidad

```powershell
.\tools\test_portable_v1.ps1
```

La prueba copia temporalmente la aplicación, la abre desde otra ubicación y
elimina esa copia al terminar.

### Archivos principales

- `qml\Main.qml`: presentación del menú, juego y editor.
- `src\millonario\controller.py`: coordinación de la interfaz.
- `src\millonario\engine.py`: reglas y estados del juego.
- `src\millonario\model.py`: preguntas y validaciones.
- `src\millonario\storage.py`: guardado, respaldos y recuperación.
- `projects\demo.juego`: preguntas editables.
- `tools\build_v1.ps1`: construcción del ejecutable portable.
- `ROADMAP_V2.md`: idea futura de importación y rondas sin repetición.

## Antecedente para V2

La V2 evaluará la importación de un banco externo de 10 a 12 preguntas y la
selección de cuatro preguntas por ronda, manteniendo un historial para reducir
o evitar repeticiones entre jugadores consecutivos.
