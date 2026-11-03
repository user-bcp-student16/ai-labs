AMBITO
Workspace: ai-labs, abierto en su raiz. Todas las rutas son relativas
a esa raiz. Lee el codigo solo de api/; escribe codigo, configuracion y
pruebas solo en api/. No leas ni modifiques codigo de otros componentes.
Lee README.md, RETO.md y docs/GOOD_PRACTICES.md. Lee
HALLAZGOS.md, PLAN.md y los demas documentos de docs/ solo si existen.
Escribe evidencias solo en HALLAZGOS.md, PLAN.md, prompts/,
docs/ENDPOINTS.md, docs/TESTING.md y docs/GOOD_PRACTICES.md de la raiz.
Cuando este paso pida un artefacto ausente, crealo. Si ya existe, conserva
las filas y secciones de otros componentes. No las sobrescribas.
Cada hallazgo lleva componente api e ID H-API-NN, por ejemplo H-API-01.
Cita codigo como api/ruta:linea. No renumeres IDs existentes.
Ejecuta Git desde ai-labs/; ejecuta pruebas con cwd api/.
Coordina dependencias externas sin ampliar AMBITO. No inventes aprobaciones
humanas ni resultados de pruebas. Si falta evidencia, registra el pendiente.

CONTEXTO
Lee README.md y RETO.md. Usa HALLAZGOS.md y docs/ENDPOINTS.md
si existen. Mi foco es [pregunta concreta]. Verifica las rutas en codigo.

OBJETIVO
[resultado que quiero poder comprobar].

RESTRICCIONES
No edites codigo en este primer pedido. No uses secretos reales. Conserva
contratos. Declara archivos ausentes y limites de lo que puedes comprobar.

CRITERIOS DE ACEPTACION
[dos criterios observables con evidencia o prueba]. Separa hechos de hipotesis.
No afirmes que ejecutaste pruebas si solo las propusiste.

FORMATO DE RESPUESTA
[formato que usare para revisar]. Incluye evidencia faltante y siguiente paso.