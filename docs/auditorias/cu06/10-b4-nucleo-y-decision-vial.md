# CU06 · B4: núcleo implementado, proveedor y convivencia pendientes

Fecha: 2026-11-01. Fuente de implementación: checkout local con B1/B2/B3 sin commit; no GitHub remoto. **B4 no está completo ni conectado a la operación.** Se entregan contratos internos, cálculo secuencial y validaciones probados con respuestas controladas. No hay proveedor vial autorizado ni decisión final D7 sobre horarios manuales/calculados.

## 1. Decisiones encontradas y límite aplicado

- El plan03, tabla1 y §4, separa B4 de B3 y B5. 04§6 requiere tramos ordenados, tiempos de servicio, regreso, procedencia y vigencia, sin optimizar ni liberar recursos por ETA. 09 conserva B4/D7 pendientes.
- `backend/docs/cu/destinos-envios.md:3,25–29`: Geoapify Free fue autorizado para **geocodificación** el20/10/2026. `GeocodificadorGeoapify.cs` consulta `/v1/geocode/search`, no routing. `Infrastructure/Persistence/DependencyInjection.cs:46–48` registra ese cliente con timeout8s y logs suprimidos. No se extiende esa autorización a otro servicio.
- Mapbox existente se usa en mapas/teselas/selectores de coordenadas. No se encontró integración Directions/Routes, configuración vial ni autorización de llamadas viales en código/documentación revisados. No se inspeccionaron ni reutilizaron credenciales de entorno.
- 04§6/D7 y03§4 **no fijan prioridad, espera o reemplazo** de horarios manuales por calculados. B3 persiste llegada manual en `LlegadaEstimadaUtc` y la presenta como manual. Este incremento no modifica ese contrato ni sus valores.

**Qué se puede construir sin decidir D7:** el contrato entre Application y un futuro adaptador, la aritmética pura del recorrido y resultados tipados. **Qué no se activó:** adaptador comercial, DI, endpoint, persistencia de cálculos, contrato público/ApiClient/OpenAPI o pantalla de estimaciones. No se sustituye el estado público `SinEstimacion` de B3 por resultados sintéticos.

## 2. Comparación breve con fuentes oficiales

Consulta documental del01/11/2026. Importes USD publicados, sin impuestos/contrato particular; no son una cotización ni una contratación. Se consultaron documentación y condiciones, **no endpoints viales**, cuentas ni playgrounds con claves.

| Alternativa | Cobertura y capacidades | Límites / costo publicado | Encaje y cautelas |
|---|---|---|---|
| **Geoapify Routing** | Declara cobertura global de routing basada en datos abiertos. No encontré una garantía específica de exactitud/cobertura calle a calle de Uruguay; requiere piloto local autorizado. Modos drive/truck y otros; `free_flow` no incorpora tráfico, `approximated` no es tráfico observado. [Plataforma](https://www.geoapify.com/), [Routing](https://apidocs.geoapify.com/docs/routing/) | Free:3000 créditos/día, hasta5req/s; API10:USD59/mes por10000 créditos/día. Base1 crédito por tramo, extras por opciones/distancia. No se verificó un máximo contractual de waypoints: no se inventa ni se presupone que acepte502. [Precios](https://www.geoapify.com/pricing/), [cómputo](https://www.geoapify.com/pricing-details/) | Reutiliza patrón HTTP/secretos del geocodificador, no su autorización. El proveedor declara permitir almacenar resultados; favorable al snapshot, sujeto a sus condiciones. No garantiza restricciones viales por dimensiones físicas del vehículo a partir de capacidades de carga. |
| **Mapbox Directions** | Uruguay figura expresamente en cobertura de tráfico real/típico. Perfiles driving/driving-traffic y otros; cuando falta tráfico puede caer a datos típicos o driving: debe rotularse, no prometer tráfico observado en todo tramo. [Cobertura](https://docs.mapbox.com/help/dive-deeper/directions/), [API](https://docs.mapbox.com/api/navigation/directions/) | Hasta25 coordenadas,300req/min; la página publica100000 solicitudes mensuales gratuitas y luegoUSD2/1000 en el primer tramo pago. [Límites](https://docs.mapbox.com/api/navigation/directions/#directions-api-restrictions-and-limits), [precios](https://www.mapbox.com/pricing) | Reutiliza mapas del frontend, pero necesita una integración backend nueva. Verificar licencia de conservación de resultados/snapshots y atribución específica de Directions; no inferirlas del token o de la licencia de mapas. |
| **Google Routes** | La tabla oficial incluye Uruguay para conducción y capa de tráfico. Compute Routes diferencia tráfico y perfiles; restricciones de vehículos grandes son prestaciones distintas. [Cobertura](https://developers.google.com/maps/coverage), [uso](https://developers.google.com/maps/documentation/routes/usage-and-billing) | Máximo25 intermedios,3000 consultas/min. Essentials:10000 eventos gratuitos/mes, luegoUSD5/1000 en primer tramo; tráfico activa Pro:5000 gratuitos, luegoUSD10/1000. Requiere facturación habilitada. [Precios](https://developers.google.com/maps/billing-and-pricing/pricing), [límites/SKU](https://developers.google.com/maps/documentation/routes/usage-and-billing) | Mayor cambio de integración. Resultados sobre mapa requieren Google Map; sin mapa requiere atribución. Restricciones de caché y políticas de privacidad hacen necesario resolver conservación histórica antes de elegirlo para el esquema Mapbox/B3. [Políticas](https://developers.google.com/maps/documentation/routes/policies) |

### Ubicaciones, atribución y costo real del recorrido

- **Geoapify:** OSM siempre, Geoapify obligatorio en Free; otros créditos según API. Su política informa cuerpo/headers/IP/instante almacenados para control y diagnóstico; solicitudes exitosas generalmente no más de24h, no una promesa universal de cero retención. Declara hosting UE. Revisar endpoint/región/DPA aplicables con el responsable de datos. [Condiciones](https://www.geoapify.com/terms-and-conditions/), [privacidad](https://www.geoapify.com/privacy-policy/).
- **Mapbox:** política describe recepción de ubicaciones por Navigation APIs y procesamiento en AWS/EEUU. No equiparar telemetría del SDK con una petición servidor-servidor ni dar por acreditada una retención concreta de cada coordenada Directions. Revisar DPA, atribución y derecho de snapshot de la cuenta antes de activar. [Privacidad](https://www.mapbox.com/legal/privacy), [condiciones](https://www.mapbox.com/legal/product-terms).
- **Google:** requiere términos/privacidad públicos y atribución; las restricciones de conservación y de presentación sobre mapas son relevantes al histórico B3. No enviar nombres, direcciones textuales ni IDs si bastan coordenadas. [Políticas Routes](https://developers.google.com/maps/documentation/routes/policies).
- El núcleo solicita **n+1 tramos** en secuencia para respetar el servicio y la salida efectiva prevista de cada tramo. Para30 paradas son31 consultas por cálculo, no una. Ejemplo solo aritmético:100 rutas/día implican3100 créditos base Geoapify/día, antes de geocodificación/extras; excede Free. Equivalen a93000 consultas en30d en los otros proveedores si se mantiene un pedido por tramo. No son volúmenes observados de NexoRuta. Reintentos/recalcular aumentan consumo. El futuro adaptador puede agrupar tramos estáticos si conserva el contrato y su hora/modelo, nunca alterar orden ni omitir el regreso.

**Recomendación técnica, todavía no adoptada:** Geoapify Routing como primer adaptador **estático `drive/free_flow`**, sin contratación paga automática. Motivos: patrón backend existente y almacenamiento de resultados permitido según la plataforma; B4 no exige tráfico real. A cambio, exige verificar cobertura práctica en Uruguay y que presupuesto/cuota compartida alcance. Mapbox Directions es la alternativa preferible si se prioriza tráfico en Uruguay/cuota mensual, previa resolución de licencia histórica. No recomiendo Google para este primer corte por cambio de mapas/condiciones y costo del tráfico. Estas son inferencias de encaje, no benchmarks de precisión ni asesoramiento contractual.

## 3. Semántica de horarios: propuesta para aprobar

| Aspecto | Vigente / implementado sin efectos operativos | Recomendación para conexión pública (pendiente D7) |
|---|---|---|
| Manual | `LlegadaEstimadaUtc` de B3 permanece intacto. El cálculo devuelve copia separada de ese dato y llegada/salida calculadas | Manual como compromiso/entrada del operador; cálculo como orientación paralela, sin sobrescritura ni conversión automática |
| Cálculo | Circuito teórico base snapshot → paradas activas por orden → misma base, incluyendo servicio. **No espera a la hora manual** | Mostrar claramente «calculada sin esperas por horarios manuales» y diferencias, no desplazar otras paradas para reconciliar silenciosamente un compromiso |
| Actualización | Núcleo invocable con entradas/versiones explícitas; ninguna suscripción ni escritura | Acción explícita «Calcular/Recalcular»; conservar versiones anteriores. Si más adelante se desean ventanas horarias/esperas, requieren otro requisito |
| Invalidación | Huella de operador/ruta/versión, base usada, puntos, orden/composición activa, salida, perfil, servicio, margen y manuales. Entradas distintas no admiten reutilizar como vigente un resultado anterior | No aplicar respuesta vieja: revalidar versión/huella al persistir bajo el patrón transaccional del módulo. Un fallo conserva histórico rotulado, no lo vuelve cero ni vigente |
| Vigencia temporal | Caducidad mínima informada por los tramos; sin caducidad informada => **desconocida**. Recibir datos viejos no reinicia su vigencia | Mostrar calculadoEn, modelo/origen, caducidad o «vigencia no informada». No inventar un TTL de30min ni tráfico actual si el proveedor no lo entrega |
| Base / historia | Se recibe la base/versiones **del snapshot B3**. No se cambia ese snapshot ni se lee la ficha actual como reemplazo implícito | Editar catálogo de base no reescribe el circuito histórico. Cambiar explícitamente las entradas usadas exige nueva huella/cálculo; avisar diferencia con catálogo si se presenta |
| Regreso / disponibilidad | Regreso estimado y listo previsto son valores distintos; no existen comandos de retorno/liberación en el núcleo | Presentarlos como previsiones, separados del retorno confirmado y carga pendiente. Nunca liberar, recibir ni cambiar custodia por ETA |

El modo teórico sin esperas solo está probado como aritmética independiente; **no se eligió como política operativa definitiva**. No hay pantalla/API que lo publique como horario autorizado.

### Decisión concreta requerida

1. **Proveedor/perfil:** ¿aprobar Geoapify Routing `drive/free_flow` para el primer adaptador, limitado a vehículos livianos para los que ese perfil sea apropiado, con atribución OSM+Geoapify, envío mínimo de coordenadas, sin upgrade pago ni fallback a otro proveedor? Esto autoriza desarrollar el adaptador; no se presume consentimiento para usar una credencial concreta o ejecutar llamadas facturables. Un piloto vial real y sus límites/credencial se autorizan explícitamente después. Si la flota requiere restricciones de camión, no deducirlas del peso/volumen de carga: resolver primero perfil/datos externos del vehículo.
2. **Horarios:** ¿aprobar convivencia paralela, manual no sobrescrito, cálculo teórico sin esperas por manuales, recalcular explícito e histórico versionado con vigencia desconocida cuando no se informe? Si no, precisar la prioridad/espera requerida antes de cablear la integración pública.

No hay contrato, cuenta o plan pago creado. Tampoco se usa la clave Geoapify ya existente ni un token Mapbox ambiental para probar routing.

## 4. Código ejecutable entregado

Solo tres archivos nuevos; ningún archivo previo de código/contrato se modifica:

- `backend/src/NexoRuta.Application/Reparto/Estimaciones/ContratoEstimacionVial.cs`: DTO internos, estados de cálculo/tramo/vigencia, `IProveedorTramosViales`, fuente real/controlada, perfil/modelo/tráfico/atribución/fecha/caducidad. Un pedido por tramo evita tratar todo el circuito como si saliera a la misma hora cuando hay atención entre paradas.
- `.../EstimadorRutaInicial.cs`: motor sin repositorios, DbContext, buses ni comandos físicos. Valida y congela entradas antes del primer await, filtra suspendidas, ordena por orden declarado, rechaza duplicados/coordenadas no confirmadas/tiempos desconocidos. Usa UTC y conserva zona IANA para presentación futura. No optimiza.
- `backend/tests/NexoRuta.UnitTests/Reparto/EstimadorRutaInicialTests.cs`: proveedor controlado solo en tests y reloj fijo; nunca un proveedor de producción simulado.

Resultados separados: `DatosInsuficientes`, `SinParadas`, `ProveedorNoConfigurado`, `RutaNoEncontrada`, `ProveedorNoDisponible`, `TiempoAgotado`, `CuotaExcedida`, `RespuestaInvalida` y `Calculada`. Se valida eco/huella/índice/origen/destino/perfil, números finitos no negativos, fechas y consistencia de modelo/fuente; exceso de rango temporal o suma extrema de distancias produce rechazo controlado. Un fallo intermedio descarta todo el itinerario parcial. Cancelación del llamador se propaga; timeout/fallo de red no filtra mensajes externos.

Una huella incluye tenant/ruta/versiones pero el contrato del adaptador no necesita nombres, direcciones o IDs personales. La huella sirve para correlación **local del adaptador**, no debe mandarse al vendedor ni loguearse junto con coordenadas. El adaptador futuro debe vincular cada respuesta HTTP con su pedido real; no puede asignar a una respuesta vieja la huella de un pedido nuevo.

### Ejemplo exclusivamente controlado

Salida prevista:01/11/2026 23:50 America/Montevideo (02/11 02:50Z). Tramos sintéticos10/20/15min, servicios10/5min, margen7min:

| Dato | Resultado controlado en hora local |
|---|---|
| Llegada calculada P1 / salida P1 |02/11 00:00 /00:10 |
| Llegada calculada P2 / salida P2 |02/11 00:30 /00:35 |
| Regreso estimado base |02/11 00:50 |
| Listo previsto |02/11 00:57 |

Las horas manuales de la fixture no se reemplazan. Todos los tramos llevan `FuenteVial.RespuestaControlada`, proveedor `CONTROLADO`, modelo `fixture`. **No son tiempos viales reales de Uruguay, no acreditan regreso y no liberan ocupación.**

## 5. Verificación y preservación

Evidencia en [evidencias/b4/](evidencias/b4/):

- RED observado:3 casos iniciales fallaron por `NotImplementedException` del scaffold antes de implementar el motor. GREEN inicial3; ampliación29/32; RED adicional de respuesta sin campos numéricos que era interpretada como cero, corregido a campos nullable; versión final**33 casos B4 aprobados**. No se presenta el scaffold como defecto previo de B3.
- Suite unitaria rápida del backend como comprobación de integración de Application:258 aprobadas cuando B4 tenía29 casos; después se añadieron4 casos y se ejecutaron los33 focalizados. No se afirma una ejecución posterior de262 ni se repitieron suites HTTP/B2/mobile/visual aprobadas.
- Se cubren secuencia completa/medianoche, cada servicio y margen único, desconocidos vs cero explícito, suspendidas/sin paradas, duplicados, coordenadas y datos insuficientes, fallos tipados, cancelación antes/durante, timeout/red, respuesta vieja/índice/perfil/destino incorrecto, no finitos/desbordamiento, origen controlado y caducidad desconocida/vencida, otro operador/ruta/versión y mutación de colección del llamador. Los tests de correlación no sustituyen futuras pruebas HTTP/RLS de un endpoint aún inexistente.
- `dotnet build backend/src/NexoRuta.Api --no-restore`: correcto,0 errores; advertencia NU1510 preexistente. Compilación no acredita un proveedor real.
- **HTTP/contrato público:** sin cambios, no endpoint nuevo ni snapshot OpenAPI regenerado innecesariamente. Sin llamadas a servicios viales.
- **Navegador:** no corresponde en este incremento independiente, porque no se modificó interfaz, JS, CSS, PageModel ni consumidores. No se repitió la revisión B3 ni se atribuyen capturas B3 a B4. La interfaz de cálculos pendiente deberá revisarse con datos aislados al autorizar D7.
- **Arquitectura:** se conserva el fallo preexistente de09 (`ShipmentEndpoints_DeclareApiOwnedResponses`, esperado2/actual7); no se reejecutó una suite de endpoints cuyo código/contratos no cambió. No está resuelto.
- Git inicial/final e inventario: [preservacion.json](evidencias/b4/preservacion.json). Copia inicial con hashes de157 archivos locales en TEMP `NexoRuta-B4-initial-l04ven01`. B1/B2/B3, frontend, mobile, migraciones, contratos, documentos previos y gitlinks permanecen sin cambios de este incremento.

## 6. Lo que permanece bloqueado o pendiente

**Bloqueo de alcance para completar B4:** decisiones de proveedor/perfil y convivencia D7, no falta de código del CRUD ni de capacidad/ocupación. Una vez resueltas: adaptador HTTP con límites/timeout/cuota/privacidad, prueba de contrato con respuestas externas controladas, integración autorizada por operador, persistencia versionada de cálculos conforme a licencia elegida, revalidación transaccional de respuestas viejas y UI/ApiClient/OpenAPI conjuntamente. No se implementan esos puntos por inferir una aprobación.

**Artefacto Stage B2:** sigue siendo necesario un artefacto B2 compatible y acreditado para la conciliación entre Stage y Enforce. No se identificó aquí un artefacto con manifiesto/procedencia/compatibilidad verificados; el binario Debug recompilado de este checkout requiere esquema B3 y no acredita compatibilidad Stage. No se reconstruyó B2 eliminando cambios ni se afirma que un backup de archivos sea un artefacto aprobado. Responsable de operación/DBA debe proporcionar/verificar ese artefacto o resolver expresamente un mecanismo alternativo antes de habilitar operación, conforme07–09. No se ejecutó `database-migrate`, migración ni conciliación operativa.

**Revisión nativa y habilitación operativa pendientes**, igual que09; la capacidad `external.select_intended_untracked` no está expuesta y no se fabricó revisión/aprobación ni se cambiaron preferencias. Engram sin identidad runtime registrada: trazabilidad local, no memoria atribuida guardada. B5 no iniciado. **CU06 no completo.**

Risk: none para el código nuevo aislado y no conectado. No cambia locks, autorización, persistencia ni contratos consumidos; antes de integrar B4 deberán evaluarse los riesgos correspondientes de esa integración.
