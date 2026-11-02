# CU09 — cobertura y tarifa al admitir el envío

Continuación de `d3ae05c`, sin repetir el cierre de CU08. Alcance: enunciado oficial 5.2 CU09 y 6.6; decisiones D02 y D22 identificadas en la recuperación. No se agregan precios ni cobertura a los datos de desarrollo para conseguir una aceptación.

## Trazabilidad

| Requisito | Implementación | Evidencia ejecutable |
|---|---|---|
| Operador atiende el destino | `shipment_service_offers`, PostGIS `ST_Covers`, operador activo, zona activa, modalidad y versión publicada; validación en servidor antes de crear | `TarifaAdmisionHttpTests`: cobertura válida, Rivera, frontera inclusiva y punto exterior |
| No confiar en el navegador | Punto y servicio declarados se contrastan con publicaciones del operador; importes desconocidos se rechazan; versión esperada detecta cotización vencida | HTTP directo: zona ajena, modalidad inexistente, importe manipulado, publicación cambiada |
| Tarifa inequívoca antes de confirmar | Alta integra selector existente y selección de zona/modalidad; cotización previa y confirmación con versión esperada | `AdmissionSelectsAdjustsQuotesSavesAndReopensBeforeShipping`, `CrearEnvioComponentTests` |
| Todos los bultos y reglas existentes | `CalculadoraTarifas` recibe todos los pesos/volúmenes, tarifas, ajustes y versión existentes | Dos bultos, componentes y ajustes de publicación en pruebas HTTP |
| Atomicidad y procedencia | Creación SECURITY DEFINER de CU08, confirmación del destino y cargo dentro de una transacción; snapshot de cálculo, servicio, punto y revisión de zona | Cargo guardado, rechazo sin envío parcial, importación mixta sin filas persistidas |
| D02: publicación de admisión | Oferta toma publicación vigente y la bloquea durante admisión; confirmación verifica versión cotizada | Cotización obsoleta rechazada; nuevo envío toma publicación nueva |
| D22: historia económica | `TarifasEnvio` append-only, RLS y trigger contra modificación/borrado; lectura no recalcula cargos | Publicar otras tarifas no altera cargo original; historial y trigger verificados |
| Cambios posteriores del destino | Se revalida cobertura y servicio, se usa publicación original y se agrega revisión económica atómicamente | Cambio permitido conserva versión; Rivera y concurrencia rechazan sin cambiar estado |
| Operador | Selección inicial revalida oferta/cotización; no existe operación de cambio de operador en un envío admitido | Aislamiento A/B, tarifa propia distinta y acceso cruzado denegado |
| CSV y consumidores | Contrato formato 2 obligatorio, plantilla de 13 columnas, zona/punto/modalidad y todos los bultos; API, Commerce, ApiClient y OpenAPI actualizados juntos | `ShipmentCsvImportHttpTests`, pruebas HTTP CU09 y contratos del cliente |
| Autorización y RLS | API restringida; consulta SECURITY DEFINER con search_path fijo valida acceso comercial; sin acceso general a borradores; cargos visibles por envío autorizado | Comercio ajeno y operador ajeno no leen historial; anónimo/rol incorrecto no cotizan |

## CSV: transición explícita

`VersionFormato=2` es obligatorio. La cabecera agrega `zonaId,latitud,longitud,modalidad`; zona vacía permite inferencia solamente cuando hay una única oferta compatible. Una zona ambigua se rechaza, no se elige arbitrariamente. Huella v2 incluye punto, zona y modalidad, además de los bultos ordenados; no incluye la publicación actual, de modo que repetir un lote tras publicar tarifas sigue siendo idempotente.

Las referencias históricas con huella v1 permanecen intactas y consultables. Intentar reutilizarlas bajo v2 devuelve conflicto explícito `OriginalDeclarationVersionMismatch`; no se reinterpretan, duplican ni actualizan silenciosamente. El formato antiguo se rechaza con instrucciones para v2. La migración cambia únicamente el requisito de nuevas escrituras de identidad.

## Historia y límites del modelo

Un cargo contiene el desglose completo, versión tarifaria, zona, modalidad, punto y versión/revisión geográfica. Las ediciones de destino conservan las condiciones económicas de la publicación original y revalidan la cobertura activa. Si el nuevo punto coincide con varias ofertas, se conserva la zona original cuando corresponde; de otro modo se exige una selección inequívoca.

Los envíos históricos sin cargo verificable continúan siendo legibles con cargo ausente; no se inventa un precio retrospectivo. Su modificación de destino requiere procedencia tarifaria verificable y se rechaza si falta. No existe un módulo de facturación al cual integrar un cálculo nuevo: D22 queda respaldado por el cargo almacenado e historial expuestos por API/ApiClient, sin recalcular al leer.

Se conserva la migración `AdmitMultipleParcels`, creación SECURITY DEFINER, rol API restringido y contratos multibulto. Las pruebas usan tarifas y polígonos declarados exclusivamente en fixtures sintéticos, sin cambiar cobertura ni publicaciones del entorno utilizado para las capturas.
