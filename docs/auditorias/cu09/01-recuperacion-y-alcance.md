# Recuperación CU09 y decisiones oficiales

Base raíz `d3ae05c`; backend `00fad6f`, frontend `5a9ab7d`, mobile `5302b20`. Árboles limpios al retomar. Ramas raíz/backend/frontend: `task-cu09-tarifa-cobertura-20261102`; mobile: `task-cu08-consumidores-20261102`. CU08 conserva su cierre técnico y función SECURITY DEFINER.

## Trabajo exploratorio preservado

- `.local/codex-cloud/cu09-wip/backend.patch`: SHA256 `4c8806cf5c02438473a6bd5b356201153ee2c1b418b97a41d2967d9097b3556f`.
- `.local/codex-cloud/cu09-wip/frontend.patch`: SHA256 `7a744e86e308592cdd4547b02b5ad77e065765110636025aebe2bb289394682a`.
- `.local/codex-cloud/cu09-wip/revision-2/backend/src/NexoRuta.Api/Features/Envios/Contracts/Responses/TarifaEnvioResponse.cs`: SHA256 `8dd381e04bd3d809dead3195db00c018a1eea355bec32cbdc240fa28802744ce`.
- `.local/codex-cloud/cu09-wip/revision-2/backend/src/NexoRuta.Application/Envios/Repositories/IServiciosEnvioRepository.cs`: SHA256 `074058ebbbd941c80d03946e516e8ade11437e2627f9447119e06bd6308f6432`.
- `.local/codex-cloud/cu09-wip/revision-2/backend/src/NexoRuta.Infrastructure/Envios/Repositories/EfServiciosEnvioRepository.cs`: SHA256 `e2dc2bd3ed628e5b242c136b6ada056b64feb64ae6c06dad5f1c94f8cb4c3188`.
- `.local/codex-cloud/cu09-wip/revision-2/backend/src/NexoRuta.Infrastructure/Envios/Repositories/TarifasAdmision.cs`: SHA256 `96d94cc7218e15587b22f6faceef9e4a4c6aee0de4731ea1baf3471856c5cbab`.
- `.local/codex-cloud/cu09-wip/revision-2/backend/src/NexoRuta.Infrastructure/Persistence/Migrations/20261102030000_ApplyShipmentTariffs.cs`: SHA256 `f9cdf2edfb9ca1e8065583777506a15c07f3d6870a564cc735a9c5633f989364`.
- `.local/codex-cloud/cu09-wip/revision-2/backend.patch`: SHA256 `10f8e75cebd43c9229425449758ac980e54b71d1e26219a794d1f82467315aae`.
- `.local/codex-cloud/cu09-wip/revision-2/frontend/src/NexoRuta.ApiClient/Features/Envios/Contracts/Responses/TarifaEnvioResponse.cs`: SHA256 `57bebcb5d1de6562c2b2c20409333ff9a187f8515f6fa379864c94e38f398e52`.
- `.local/codex-cloud/cu09-wip/revision-2/frontend.patch`: SHA256 `60cb1884300166a3c4cca5ec98b7c50283ff56f220ef347054e2bce5c5ea4454`.

## Fuentes oficiales

PDF `Laboratorio__NET_2026.pdf`: 5.2 numeral9 exige tarifa automática al alta; 6.6 exige conservar tratamiento original bajo cambios de publicación. XLSM leído como XML, sin ejecutar macros:

- CU-09 | 9 | Cálculo de tarifa | Calcular la tarifa automáticamente al alta según el cuadro vigente. | M02 | 5.2 | Portal / API | Comercio | Obligatorio
- D02 | M02 | M01 | CU-09 | CU-03 | Regla / datos | El precio usa la versión tarifaria vigente al alta. | Servicio de cálculo + ID de versión de tarifa | Cambios retroactivos de precio.
- D22 | M06 | M02 | CU-30 | CU-09 | Datos | La liquidación usa cargos calculados al alta. | Tarifa aplicada e historial | Liquidación recalculada con reglas nuevas.

## Revisión del borrador

Se reutilizan contratos explícitos de servicio, CalculadoraTarifas y lectura restringida de publicaciones/zonas existentes. Se corrigen las partes incompletas: selector antes del alta, confirmación inicial de dirección/coordenadas, cotización visible, traducción de errores, atomicidad del lote, huella/formato CSV explícitos, consumidores y pruebas. No se configura ninguna tarifa o cobertura de producción para admitir envíos. Los fixtures declaran sus datos sintéticos expresamente.

El cambio de operador no existe como mutación del agregado publicado: la selección previa al alta se revalida; el operador de un envío persistido y su identidad de importación se conservan. Los cambios de destino permitidos mantienen la publicación tarifaria original y registran una nueva aplicación sin sobrescribir el cargo anterior.
