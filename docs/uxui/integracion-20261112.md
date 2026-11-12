# Integración de PR #77 con develop

## Fuentes inspeccionadas

Al retomar, la PR raíz #77 seguía abierta en `3e8b1969a9b0e4e47915c13d22c05fbf4e28ab76`. El fetch de `develop` resolvió `98aab579c53ec9589e4e0912a366cfc0033b5bc6`.

| Componente | Gitlink de la PR inicial | Gitlink de develop consultado |
| --- | --- | --- |
| Backend | `c786977580dc5fb01839ee8c9816118c7e8dbf1e` | `08eae8af63667fefbbcbb2eb45087e4209abed57` |
| Frontend | `b994957d3ae30c3a6290e8d990b95ba00273232c` | `c34764eb46444007f69cb525df959a7850f7891d` |
| Mobile | `53f6be2cdec48f48e30e390060feeaefb5be0ead` | `329dd3454704c0f45b615d609f469b7fd4b2dd5f` |

Se integró la base mediante `git merge --no-ff --no-commit origin/develop` sobre `fix/uxui`. Los dos conflictos fueron gitlinks. No se reescribió el historial publicado ni se modificaron develop/main.

Las PR de componentes se comprobaron en GitHub, no solo por nombre de rama:

- [Backend #55](https://github.com/NexoRuta/NexoRuta-Backend/pull/55), fusionada en `9cdad17bdc712324edc54abbb9ed1c897f50dcb4`, tiene como padres exactos `08eae8af63667fefbbcbb2eb45087e4209abed57` y `c786977580dc5fb01839ee8c9816118c7e8dbf1e`.
- [Frontend #54](https://github.com/NexoRuta/NexoRuta-Frontend/pull/54), fusionada en `162bf08ec9ad1428fa56dc81b5ce289ac1208a61`, tiene como padres exactos `c34764eb46444007f69cb525df959a7850f7891d` y `b994957d3ae30c3a6290e8d990b95ba00273232c`.

Ambas son fusiones reales, sin squash. Se comprobó la ascendencia de las dos líneas en cada commit. Backend se fija en su merge `9cdad17…`; Frontend parte de su merge `162bf08…` y añade únicamente las correcciones de contrato y foco descritas abajo. Así se conservan UX/UI y AP-04, incluidos los arreglos de publicación/seed y devoluciones de la base. Mobile conserva exactamente el gitlink `329dd345…` incorporado por develop.

## Primer fallo real del CI anterior

Corrida: [42530238114](https://github.com/NexoRuta/NexoRuta/actions/runs/42530238114), PR original `3e8b196…` (GitHub ejecutó su merge sintético `267febdc32a2e453ed2eaf495000e8d55cb1570b`).

En [frontend, job 128882675963](https://github.com/NexoRuta/NexoRuta/actions/runs/42530238114/job/128882675963), checkout, restore y build terminaron correctamente. Falló **Compare the versioned OpenAPI snapshot with the resolved API** con:

> Versioned OpenAPI differs from the API built from the resolved backend SHA.

Las pruebas frontend aún no habían comenzado. El fallo posterior de carga de TRX es secundario: no había resultados de pruebas que subir. [Integrated CI / result, job 128885752227](https://github.com/NexoRuta/NexoRuta/actions/runs/42530238114/job/128885752227) solo propagó el resultado requerido `frontend: failure`; no tenía un fallo independiente.

## Reproducción y arreglo

Se compiló API Release desde Backend `9cdad17…` y Frontend Release desde `162bf08…`, con restores bloqueados por lockfile. Se inició OpenAPI con la misma configuración aislada del workflow: sin migración/seed y una conexión PostgreSQL inutilizable de prueba; no se utilizó una base compartida.

La comparación estricta de objetos JSON —excluyendo únicamente `servers`, como ya hace CI— reprodujo la discrepancia. Faltaban exclusivamente:

- `GET /api/gestion/operadores/{operador}/opciones/{tipo}`.
- Los esquemas `OpcionGestionResponse` y `OpcionesGestionResponse`.

No había rutas/esquemas extra ni contratos existentes distintos. El endpoint de lectura incorporado en #55 no estaba registrado en el snapshot frontend. Actualizar solo los gitlinks no solucionaba esa ausencia.

Se actualizó `frontend/contracts/nexoruta.openapi.json` desde la API de ese Backend, conservando `servers` y el formato del archivo. La comparación estricta posterior coincide en **146 rutas**. Una nueva prueba de contrato verifica la lectura por nombre, sus parámetros de búsqueda/página/selección, los IDs UUID internos, los nombres y `hayMas`. El workflow, sus checks y las aserciones existentes se conservan.

Al ejecutar la suite completa se reprodujo además dos veces una carrera en la reapertura rápida del panel de flota, con movimiento reducido: el título podía heredar visibilidad después del evento `shown` y perder el foco. La prueba aislada pasaba. El arreglo conserva el foco inmediato y lo restaura en el siguiente frame renderizado, solo si el panel sigue abierto. No cambia comandos ni reglas de flota y no debilita la aserción de teclado.

La atribución histórica por diferencias de precisión en timestamps sigue como trabajo separado; esta integración no modifica su reconstrucción ni reescribe hechos o documentos.

## Resolución publicada y verificación local

El arreglo frontend se publica por [Frontend #60](https://github.com/NexoRuta/NexoRuta-Frontend/pull/60), desde `fix/uxui-integration`, sin fusionar ni aprobar. El gitlink final es `723d02ba6cb5d0196a5181e4f4f076c115d7fe6d`, descendiente del merge #54. Backend queda en `9cdad17bdc712324edc54abbb9ed1c897f50dcb4`; Mobile, en `329dd3454704c0f45b615d609f469b7fd4b2dd5f`.

Antes de publicar la raíz, develop avanzó de `98aab579…` a `690ca9673577ba1e4169e09d9c6c190829fe9622` (`fix(gcp): retry transient load balancer health queries`). Esa revisión solo modifica `scripts/gcp/delivery.py` y su prueba, sin cambiar los tres gitlinks. Se conserva mediante otro merge en `fix/uxui`, sin ejecutar despliegues ni operaciones de VM.

Verificaciones locales: restore bloqueado y build Release de API/frontend; comparación estricta de 146 rutas; regresión del snapshot aprobada; suite frontend completa aprobada (**522 pruebas, ninguna fallida u omitida**) con OpenAPI vivo y navegadores habilitados. Las dos primeras suites completas expusieron la carrera de foco descrita; tras corregirla pasó la suite completa, conservando sus aserciones. Las regresiones reales de gestión/webhooks se ejecutan con el mismo par publicado y sus fixtures propios. La corrida integrada final y sus resultados se enlazan en la PR #77 para no generar otra revisión solo por actualizar el enlace de CI.

El manifiesto histórico `scripts/cloud/checkpoint.json` no se usa para elegir fuentes: la autoridad es el HEAD raíz y sus gitlinks exactos, como exige la continuidad vigente.

## Avance de la base durante CI

Durante la corrida sobre `4f7b351…`, develop avanzó a `143105f178b7511006d040ec5a4e579d01c2ced8` y GitHub volvió a marcar conflicto. Se incorporó mediante otro merge en la misma rama. Su backend `3bd94953c032ed28ffb0a6bc518968fa87004541` tiene como padre directo el merge UX/UI `9cdad17bdc712324edc54abbb9ed1c897f50dcb4`: conserva ambas líneas y solo agrega tres líneas a `DatosDemoSeeder.cs` para persistir metadatos del borrador antes de publicarlo. No cambia el contrato ni los controladores API.

El gitlink definitivo de Backend pasa por ello a `3bd94953c032ed28ffb0a6bc518968fa87004541`. Frontend conserva `723d02ba6cb5d0196a5181e4f4f076c115d7fe6d` y Mobile conserva `329dd3454704c0f45b615d609f469b7fd4b2dd5f`. Se vuelve a seguir el CI del nuevo HEAD; la corrida anterior no se presenta como la validación final.
