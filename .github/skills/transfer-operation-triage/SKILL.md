---
name: transfer-operation-triage
description: "Investiga operaciones de transferencia con errores: localiza la operación, agrupa reintentos, elimina copias duplicadas de eventos, redacta datos sensibles y prepara un ticket que distingue timeout, rechazo y completado. Úsala para analizar trazas, incidencias o decidir qué confirmar antes de otro intento."
---

# Diagnóstico de operaciones de transferencia

## Objetivo

Preparar un diagnóstico y un ticket trazable para una operación de transferencia con errores, evitando exponer información sensible o recomendar un reintento mientras el resultado sea incierto.

## Procedimiento

1. **Localiza la operación**
   - Busca por el identificador de operación o correlación disponible y confirma que los eventos pertenecen al mismo flujo.
   - Si solo hay referencias parciales, usa únicamente las necesarias para acotar la búsqueda y señala la ambigüedad. No unas operaciones distintas por compartir cliente, importe o una ventana de tiempo.
   - Conserva las marcas de tiempo, el sistema de origen, los estados y los códigos de resultado necesarios para reconstruir la secuencia.

2. **Agrupa los reintentos**
   - Agrupa los intentos que tengan el mismo identificador de operación/correlación y, cuando estén disponibles, la misma clave de idempotencia y referencia de transferencia.
   - Ordena los intentos cronológicamente e identifica cada intento por su propio ID o número, hora y resultado.
   - No confundas una repetición de la solicitud con una copia duplicada de un evento. Si faltan identificadores para determinar si son reintentos de la misma operación, registra esa limitación y no los combines como un hecho.

3. **Descarta solo copias de eventos**
   - Elimina una entrada únicamente cuando puedas identificarla como copia de otra: prioriza un mismo ID inmutable de evento; si no existe, exige que coincidan el origen, la marca de tiempo y el contenido relevante del evento.
   - Conserva un registro de la copia descartada en el análisis (criterio y evento original al que corresponde), sin incluir su contenido sensible en el ticket.
   - Mantén eventos parecidos que tengan IDs, horas o resultados diferentes: podrían representar intentos reales o transiciones de estado.

4. **Oculta los datos sensibles**
   - Antes de compartir resultados, redacta nombres, correos, teléfonos, direcciones, números de cuenta o tarjeta, identificadores personales, credenciales, tokens, cookies, claves de idempotencia y encabezados de autorización.
   - Sustituye los valores por etiquetas como `[REDACTADO]`. Si hace falta correlacionar el caso, conserva solo un identificador enmascarado y estable, por ejemplo los últimos cuatro caracteres, siempre que sea suficiente y esté permitido.
   - No copies logs completos ni datos de pago al ticket. Incluye solo los campos mínimos, ya saneados, necesarios para investigar.

5. **Determina el resultado**
   - **Tiempo de espera agotado (timeout):** el sistema no recibió respuesta dentro del plazo. Esto no demuestra que la transferencia haya fallado; el resultado es **desconocido** hasta consultar una fuente autoritativa.
   - **Rechazada:** existe una respuesta explícita de rechazo para ese intento. Registra el código y motivo no sensible si están disponibles. No la describas como timeout ni como transferencia completada.
   - **Completada:** hay una confirmación autoritativa de éxito asociada a la misma operación. No recomiendes otro intento.
   - **Pendiente, contradictoria o sin confirmación:** no infieras éxito o rechazo a partir de la ausencia de eventos. Indica qué fuente y confirmación faltan; no recomiendes reintentar hasta resolver el estado.

6. **Redacta el ticket**
   - Separa hechos observados, hipótesis y datos faltantes.
   - Explica qué confirmación falta (por ejemplo, consulta de estado en el procesador/ledger o confirmación de liquidación) y quién o qué sistema debe proporcionarla.
   - Antes de considerar otro intento, pide revisar el estado autoritativo actual, los intentos previos, la clave de idempotencia, posibles operaciones duplicadas y la respuesta/código del proveedor. Para un timeout, la consulta de estado debe preceder a cualquier reintento.
   - Recomienda un reintento solo si el estado está confirmado como no completado, se descartó una operación ya aceptada y el procedimiento del sistema permite repetirlo de forma segura. Si no puedes verificarlo, deja la decisión como bloqueada por falta de confirmación.

## Formato de salida

Entrega un resumen saneado y un ticket con estos campos:

```markdown
## Resumen del diagnóstico
- Operación (referencia enmascarada):
- Resultado observado: timeout / rechazada / completada / pendiente o desconocida
- Intentos agrupados: cantidad y secuencia cronológica
- Copias de eventos descartadas: cantidad y criterio de deduplicación
- Datos redactados:

## Ticket
- Título:
- Impacto:
- Operación y correlación (enmascaradas):
- Línea de tiempo de intentos:
- Evidencia y resultado observado:
- Confirmación faltante:
- Revisión requerida antes de otro intento:
- Recomendación: no reintentar / esperar confirmación / reintento seguro condicionado
- Motivo de la recomendación y responsable de la siguiente comprobación:
```

## Reglas de seguridad y calidad

- Nunca inventes una confirmación, un estado final, un código de error ni una causa raíz.
- Nunca presentes un timeout como prueba de rechazo o de fallo definitivo.
- No recomiendes reintentar una operación completada, pendiente o de resultado desconocido.
- No publiques valores sin redactar, aunque aparezcan en logs o en el ticket original.
- Si la evidencia es insuficiente o contradictoria, indícalo expresamente y solicita la comprobación autoritativa necesaria.
