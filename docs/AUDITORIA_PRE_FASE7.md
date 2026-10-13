# Auditoría previa — Fase 7 · Editor manual + Excel

Estado: **CERRADA — arquitectura de Fase 7 definida, implementación funcional aún no iniciada**

Rama: `v4-frontend-race`

Fecha: 18 de agosto de 2026

Este documento fija las decisiones técnicas previas a construir el editor web de preguntas y la importación Excel. Debe leerse junto con:

- `CANON_RECONSTRUCCION_FRONTEND_V4.md`
- `GAMEPLAY_V4.md`
- `FRONTEND_V4_PROGRESS.md`

## 1. Objetivo de la auditoría

Recuperar las capacidades V2/V3 sin reescribir el dominio ni comprometer el backend V4:

```text
Editar preguntas
├── Administrador manual
└── Importar banco desde Excel
```

La Fase 7 debe conservar un solo banco canónico para el MVP.

No se implementará `Mis bancos`, múltiples bancos, CMS general, PostgreSQL por conveniencia ni una segunda representación de Question/Project.

## 2. Fuente histórica confirmada

V2 incorporó formalmente:

- administrador manual;
- importación `.xlsx`;
- plantilla `Banco_preguntas_V2.xlsx`;
- validación estructural;
- respaldo del banco anterior al reemplazarlo.

V3 reutiliza ese mismo editor, modelo, importador y storage. La interfaz QML conserva:

- lista de preguntas;
- selección de pregunta;
- `+ Nueva`;
- `Duplicar`;
- subir/bajar;
- `Eliminar` con confirmación;
- enunciado;
- alternativas A/B/C/D;
- respuesta correcta;
- límite de 320 caracteres para pregunta;
- límite de 140 caracteres para cada alternativa;
- manejo de cambios sin guardar;
- importación Excel desde la plantilla histórica.

## 3. Componentes V3 que deben reutilizarse

No duplicar estas reglas en un modelo web nuevo.

### `millonario_v3.model.Question`

Valida:

- pregunta obligatoria;
- máximo 320 caracteres;
- exactamente cuatro respuestas;
- respuestas obligatorias;
- máximo 140 caracteres por respuesta;
- cuatro respuestas diferentes;
- correcta entre A y D.

### `millonario_v3.model.Project`

Aporta:

- normalización;
- reemplazo;
- alta;
- eliminación;
- reordenamiento;
- serialización compatible con `.juego`;
- máximo de 12 preguntas.

### `millonario_v3.excel_import.import_project_from_excel`

Ya resuelve lectura `.xlsx` sin depender de OpenPyXL.

Contrato histórico:

- hoja obligatoria `Preguntas`;
- encabezados requeridos:
  - `Pregunta`;
  - `Alternativa A`;
  - `Alternativa B`;
  - `Alternativa C`;
  - `Alternativa D`;
  - `Respuesta correcta`;
- `Activa` es opcional para el parser y acepta SI/NO;
- respuesta correcta A/B/C/D;
- preguntas duplicadas rechazadas;
- entre 4 y 12 preguntas activas en el contrato legado.

La plantilla oficial además contiene las columnas históricas:

1. ID
2. Pregunta
3. Alternativa A
4. Alternativa B
5. Alternativa C
6. Alternativa D
7. Respuesta correcta
8. Activa
9. Observaciones

### `millonario_v3.storage`

Debe seguir siendo la capa física para `.juego` cuando el almacenamiento sea filesystem persistente.

`save_project()` ya aporta:

- normalización antes de guardar;
- escritura temporal;
- validación del contenedor antes de sustituir el válido;
- `os.replace()` atómico;
- rotación de tres respaldos `.bak`, `.bak2`, `.bak3`.

`load_project_with_recovery()` puede recuperar automáticamente desde respaldos válidos.

**Decisión:** no modificar `v3_1/` para Fase 7. V4 utilizará estas piezas desde una capa adaptadora en `online/src/desafio_online/`.

## 4. Estado actual V4

Actualmente:

- `/admin` ya presenta `Crear sala participativa` y `Editar preguntas`;
- el selector `Administrador manual / Importar banco desde Excel` existe pero está deshabilitado;
- no existen endpoints web CRUD para preguntas;
- `RoomRegistry` carga `v3_1/projects/demo.juego` al crear cada nueva sala;
- cada `OnlineRoom` mantiene su propio objeto `Project` una vez creada.

### Consecuencia positiva

Editar el banco maestro **no debe alterar una sala que ya está jugando**.

El contrato será:

```text
Sala A creada
→ conserva snapshot del banco con el que nació

Moderador edita/publica banco
→ no muta Sala A

Sala B creada después
→ utiliza el banco nuevo
```

Esta separación ya encaja con la arquitectura actual y debe preservarse.

## 5. Hallazgo crítico: persistencia en Render

El servicio actual `desafio-millonario` continúa en plan **Free**, un solo proceso/worker y sin datastore PostgreSQL asociado.

El filesystem local de Render Free es efímero. Una edición escrita directamente en la copia desplegada de `v3_1/projects/demo.juego` puede desaparecer en:

- spin-down;
- restart;
- redeploy.

Por tanto:

> **Fase 7 NO debe presentar como permanente un guardado sobre el filesystem efímero de la instancia actual.**

## 6. Decisión de persistencia

### Arquitectura elegida

Crear una capa V4, tentativamente:

`online/src/desafio_online/bank.py`

Responsabilidades:

- resolver la ruta física del banco;
- cargar el banco actual;
- validar contrato V4;
- calcular revisión;
- serializar modificaciones;
- guardar de forma atómica mediante `millonario_v3.storage.save_project()`;
- importar Excel mediante `millonario_v3.excel_import`;
- bloquear escrituras concurrentes;
- sembrar un banco inicial desde el archivo del repositorio cuando un almacenamiento persistente esté vacío.

### Ruta configurable

No hardcodear la escritura a `v3_1/projects/demo.juego`.

Usar una variable de entorno, por ejemplo:

```text
QUESTION_BANK_PATH
```

Comportamiento previsto:

- desarrollo/local: fallback al banco del repositorio;
- producción con persistencia: ruta dentro del almacenamiento persistente;
- producción sin persistencia configurada: lectura permitida, **escritura bloqueada con error explícito**, nunca un falso “guardado correcto”.

### Persistencia objetivo recomendada para este producto

**Render Persistent Disk + archivo `.juego`**.

Razones:

1. mantiene el formato histórico;
2. reutiliza backups y recuperación existentes;
3. el banco es diminuto;
4. sólo existe un banco;
5. el servicio ya usa un único worker y una única instancia por la arquitectura RAM de salas;
6. evita introducir PostgreSQL para un objeto documental muy pequeño.

Un Persistent Disk requiere instancia Render de pago. Esa modificación de infraestructura **no se realizará durante la auditoría ni sin decisión explícita del usuario**.

### PostgreSQL

No es necesario para Fase 7.

Sería razonable reconsiderarlo sólo si posteriormente se requiere:

- múltiples bancos por cuenta;
- historial/versionado consultable;
- múltiples instancias de aplicación;
- usuarios/roles de contenido;
- auditoría avanzada;
- búsquedas/reportes de preguntas.

Nada de eso forma parte del MVP actual.

## 7. Contrato de banco publicado en V4

Aquí existe una diferencia deliberada respecto de V2.

El importador legado puede parsear 4–12 preguntas activas, pero el gameplay V4 de Fase 6 conserva un plan maestro de 12:

```text
1 clasificatoria
+ 5 potenciales ronda 1
+ 5 potenciales ronda 2
+ 1 reserva
= 12
```

Para no reabrir Fase 6 ni permitir que el usuario publique un banco que después impida crear una sala:

> **El banco publicado en V4 debe contener exactamente 12 preguntas válidas.**

Por tanto:

- el parser Excel histórico se reutiliza;
- si produce 4–11 preguntas, V4 rechazará la publicación con mensaje claro;
- 12 preguntas → publicable;
- más de 12 ya es rechazado por el contrato histórico.

Esto garantiza que 1/3/5 siempre permanezcan disponibles y que exista la reserva canónica.

## 8. Validación V4 adicional

Además de `Question`/`Project`, la capa V4 debe validar antes de publicar:

- exactamente 12 preguntas;
- enunciados no duplicados, ignorando mayúsculas/minúsculas y espacios normalizados;
- revisión esperada del banco para evitar sobrescritura desde dos pestañas.

No modificar el modelo V3 para imponer estas restricciones específicas del producto web.

## 9. Estrategia de concurrencia

Aunque hoy exista un solo moderador, la web permite dos pestañas abiertas.

Se usará:

- `threading.RLock` en la capa de banco;
- una `revision` calculada sobre la representación normalizada del banco;
- las escrituras envían `expected_revision`;
- si el banco cambió desde que se abrió el editor → HTTP 409 y el usuario debe recargar/reconciliar.

Esto evita el patrón “última pestaña en guardar pisa silenciosamente la anterior”.

## 10. API propuesta para Fase 7

Todos los endpoints requieren la sesión de moderador ya existente.

### Leer banco

```text
GET /api/questions
```

Devuelve:

- título;
- 12 preguntas;
- cantidad;
- `revision`;
- estado de persistencia/escritura.

### Guardar banco manual

```text
PUT /api/questions
```

Envía el banco completo como una transacción junto a `expected_revision`.

**Decisión:** el navegador mantiene un draft completo y el servidor publica el banco completo. No crear una API distinta para mover, duplicar, borrar y editar cada fila.

Ventajas:

- menos endpoints;
- no existen estados persistidos a medias;
- add/delete/reorder pueden deshacerse antes de Guardar;
- validación global de 12 preguntas en una sola operación;
- backup único por publicación.

### Descargar plantilla

```text
GET /api/questions/template
```

Debe servir directamente:

`v3_1/templates/Banco_preguntas_V2.xlsx`

En web se reemplaza definitivamente “Abrir carpeta de plantilla” por **Descargar plantilla Excel**.

### Importar Excel

```text
POST /api/questions/import
```

El navegador envía el `.xlsx`; el backend:

1. aplica límite de tamaño;
2. verifica paquete ZIP razonable;
3. crea archivo temporal controlado;
4. llama al importador V3;
5. aplica validación V4 de exactamente 12;
6. verifica `expected_revision`;
7. guarda de forma atómica;
8. conserva backups;
9. elimina temporal;
10. devuelve nuevo banco + nueva revisión.

## 11. Upload web: no agregar dependencias innecesarias

`online/requirements.txt` actualmente no incluye `python-multipart` ni `openpyxl`.

No son necesarios.

### Excel

El importador histórico lee directamente el paquete `.xlsx` con `zipfile` + XML.

### HTTP

El navegador puede enviar el archivo como cuerpo binario (`fetch`) y el endpoint puede leer `Request.body()`.

Así Fase 7 evita incorporar `python-multipart` únicamente para un único archivo pequeño.

## 12. Defensa frente a archivos maliciosos/accidentales

El importador de escritorio recibía archivos locales elegidos por el usuario; en web conviene endurecer el borde de entrada.

Antes de pasar el archivo al parser histórico:

- tamaño HTTP máximo recomendado: 2 MB;
- comprobar tamaño real aunque falte `Content-Length`;
- rechazar extensión/nombre no `.xlsx`;
- comprobar que sea ZIP válido;
- limitar número de entradas del ZIP;
- limitar tamaño descomprimido total declarado;
- nunca extraer rutas del ZIP al filesystem;
- usar temporal generado por servidor, nunca rutas enviadas por usuario.

El parser existente lee archivos concretos dentro del ZIP y no necesita extracción general.

## 13. Editor manual web: contrato UX

La referencia visual sigue siendo V3, no un CRUD SaaS.

Composición prevista:

```text
ADMINISTRADOR MANUAL

┌──────────────────────┬───────────────────────────────────┐
│ Preguntas 12 / 12    │ Enunciado                  0/320 │
│ 1. ...               │ [...............................] │
│ 2. ...               │                                   │
│ ...                  │ A [.........................]     │
│                      │ B [.........................]     │
│ + Nueva   Duplicar   │ C [.........................]     │
│ ↑   ↓    Eliminar    │ D [.........................]     │
│                      │                                   │
│                      │ Correcta [ A ▼ ]                  │
└──────────────────────┴───────────────────────────────────┘

Cancelar / Guardar banco / Cerrar
```

Principios:

- lista izquierda + formulario derecha;
- misma identidad visual V3;
- contador 320 y 140;
- operaciones sobre draft local;
- indicador `Cambios sin guardar`;
- confirmación antes de descartar;
- `Guardar banco` sólo publica si el banco completo es válido y contiene 12;
- error se muestra sin perder el draft.

## 14. Importación Excel web: contrato UX

```text
IMPORTAR BANCO DESDE EXCEL

[ Descargar plantilla Excel ]

Archivo .xlsx
[ Seleccionar archivo ]

La versión web requiere 12 preguntas activas
para conservar los modos 1 / 3 / 5.

[ Cancelar ] [ Cargar banco ]
```

Antes de reemplazar:

- mostrar nombre del archivo;
- informar que el banco actual será respaldado;
- pedir confirmación final;
- si falla validación, no modificar nada.

## 15. Salas activas y publicación de banco

Una publicación nueva no debe cerrar ni alterar salas existentes.

`RoomRegistry.create()` debe continuar cargando el banco en el momento de crear la sala.

Por tanto:

- sala existente → conserva preguntas anteriores;
- banco publicado → disponible para la próxima sala;
- replay dentro de la misma `OnlineRoom` debe conservar su `room.project`, no saltar inesperadamente al banco recién publicado.

Esta última regla es importante: **editar preguntas mientras existe una sesión no debe cambiar el contenido de un replay de esa misma sala.** Para usar el banco nuevo se crea una sala nueva.

## 16. Backup y recuperación

Con almacenamiento persistente configurado:

```text
demo.juego
demo.juego.bak
demo.juego.bak2
demo.juego.bak3
```

La web no necesita exponer esos backups en Fase 7.

Sí debe:

- generarlos al publicar;
- poder recuperar al arrancar si el primario está dañado;
- registrar/loguear que hubo recuperación.

## 17. Qué NO entra en Fase 7

- múltiples bancos;
- categorías/tags;
- búsqueda avanzada;
- historial visual de versiones;
- exportar a Excel;
- Google Drive como almacenamiento runtime;
- GitHub como base de datos de preguntas;
- Postgres;
- edición de una sala ya iniciada;
- modificar `v3_1/`;
- cambiar gameplay 1/3/5;
- desplegar todavía a producción.

## 18. Archivos previstos

La implementación debería concentrarse aproximadamente en:

```text
online/src/desafio_online/bank.py          # nuevo adaptador/persistencia
online/src/desafio_online/app.py           # endpoints protegidos
online/static/admin.html                   # editor + import UI
online/static/admin.js                     # draft/API
online/static/phase7_editor.css            # capa visual aislada
online/tests/test_frontend_phase7.py        # contrato web
online/tests/test_bank_service.py           # dominio/persistencia
```

Reutilizados sin modificar:

```text
v3_1/src/millonario_v3/model.py
v3_1/src/millonario_v3/storage.py
v3_1/src/millonario_v3/excel_import.py
v3_1/templates/Banco_preguntas_V2.xlsx
```

## 19. Orden de implementación recomendado

### 7A — Capa de banco

- ruta configurable;
- lectura;
- revision hash;
- validación V4;
- escritura/backup;
- protección contra concurrencia.

### 7B — API

- GET banco;
- PUT banco;
- GET plantilla;
- POST import Excel;
- errores estructurados.

### 7C — Administrador manual

- recuperar layout V3;
- draft completo;
- nueva/duplicar/reordenar/eliminar;
- validación y guardado.

### 7D — Excel

- descargar plantilla;
- elegir/cargar;
- confirmación;
- errores de fila claros;
- reemplazo atómico.

### 7E — Persistencia/QA

- pruebas local con ruta temporal persistente;
- probar backups;
- probar recovery;
- comprobar que salas ya creadas no mutan;
- comprobar nueva sala con banco nuevo;
- antes de producción, configurar almacenamiento persistente real.

## 20. Criterios de cierre de Fase 7

Fase 7 podrá declararse implementada cuando:

1. el moderador pueda abrir el administrador manual;
2. se rendericen las 12 preguntas actuales;
3. pueda editar texto/A-D/correcta;
4. pueda nueva/duplicar/reordenar/eliminar dentro del draft;
5. no pueda publicar un banco inválido o distinto de 12;
6. pueda descargar la plantilla histórica;
7. pueda importar una plantilla válida de 12;
8. un Excel inválido no modifique el banco;
9. cada publicación genere backup;
10. dos pestañas no puedan pisarse silenciosamente;
11. una sala activa conserve su banco original;
12. una sala nueva use el banco publicado;
13. el backend de juego, WebSockets, audio y móviles no sufran cambios laterales;
14. `v3_1/` permanezca intacto;
15. producción no afirme persistencia mientras no exista almacenamiento durable configurado.

## 21. Decisión final de auditoría

La Fase 7 está **lista para implementarse** con este principio:

> **Reusar el dominio y storage V3, añadir una capa V4 transaccional y configurable, y mantener el banco como archivo `.juego`; no introducir PostgreSQL.**

Para el producto final en Render, la ruta de escritura deberá residir en almacenamiento persistente. En el servicio Free actual, los endpoints de escritura no deben fingir durabilidad.
