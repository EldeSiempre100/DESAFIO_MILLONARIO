# Implementación V2

Estado: construida sobre la base estable de la V1.

## Decisión de formato

La importación utiliza Excel `.xlsx` en vez de Word. La estructura tabular
permite validar de forma confiable cada pregunta, sus cuatro alternativas, la
respuesta correcta y si la fila está activa.

Plantilla:

`templates\Banco_preguntas_V2.xlsx`

## Funciones incorporadas

- El menú **Editar preguntas** ofrece dos caminos:
  - Administrador manual.
  - Importar banco desde Excel.
- La plantilla acepta entre 4 y 12 preguntas activas.
- El importador valida columnas, textos, alternativas y respuesta correcta.
- Un banco importado reemplaza al anterior después de crear un respaldo.
- Cada ronda utiliza cuatro preguntas.
- El historial se guarda en `projects\demo.history.json`.
- Con 12 preguntas, las tres primeras rondas pueden transcurrir sin repetir.
- Cuando el banco se agota, se reutilizan primero las preguntas menos recientes.
- Al importar un banco nuevo se reinicia el historial de rondas.

## Banco de demostración

La plantilla incluye cinco preguntas recuperadas del PPTX y siete preguntas
educativas nuevas. Estas últimas están marcadas en la columna Observaciones
para que sean validadas internamente antes de una actividad formal.

## Posibles mejoras posteriores

- Permitir elegir entre rondas de 4, 5 o 6 preguntas.
- Mostrar un panel de historial de rondas.
- Añadir un botón visible para reiniciar manualmente el historial.
- Permitir exportar el banco actual nuevamente a Excel.
