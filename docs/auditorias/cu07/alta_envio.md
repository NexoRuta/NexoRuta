# Alta de un envío por API con Postman

Revisé el código, el OpenAPI del checkout y el OpenAPI servido por la API local. No hice login ni creé envíos. Las rutas y los campos relevantes coinciden entre ambos contratos; la API local responde por HTTP, pero Docker no expone una revisión Git que permita confirmar que su binario sea exactamente el checkout.

## 1. Preparar Postman

Compose publica la API en el puerto 5000. La comprobación de solo lectura GET http://localhost:5000/health/ready respondió 200.

Creá un environment local con estas variables:

| Variable | Valor |
|---|---|
| baseUrl | http://localhost:5000 |
| commerceEmail | ingresalo localmente |
| commercePassword | ingresala localmente; marcala como secreta |
| accessToken | se guarda al iniciar sesión; tratala como secreta |
| operadorId | copialo del catálogo real de operadores |
| envioId | se guarda de la respuesta de creación |

No exportes ni compartas el environment si contiene credenciales o token.

## 2. Iniciar sesión como Commerce

Usá el login general de la API, no el login móvil del repartidor.

Método y URL

POST {{baseUrl}}/api/auth/login

Headers

Content-Type: application/json
Accept: application/json

Body → raw → JSON

{
  "email": "{{commerceEmail}}",
  "password": "{{commercePassword}}"
}

La respuesta correcta es 200 OK. Ejemplo ilustrativo: el token se omite deliberadamente.

{
  "accessToken": "<token devuelto por la API>",
  "tokenType": "Bearer",
  "expiresAtUtc": "<fecha y hora de expiración>",
  "contexto": "Comercio",
  "tipoOrganizacion": "Comercio"
}

En Tests de esa solicitud podés guardar el token:

const body = pm.response.json();
pm.test("La sesión usa Bearer", () =>
  pm.expect(body.tokenType).to.eql("Bearer")
);
pm.environment.set("accessToken", body.accessToken);

La API devuelve JWT en JSON; este recorrido no usa cookies. Para las solicitudes siguientes enviá Authorization: Bearer {{accessToken}}. La cuenta debe tener un acceso de tipo Comercio activo. La creación exige además el permiso envios.crear.

Opcionalmente, comprobá los permisos con:

GET {{baseUrl}}/api/usuarios/actual/permisos
Authorization: Bearer {{accessToken}}
Accept: application/json

La respuesta es una lista de códigos; buscá envios.crear. Para consultar el listado luego también se necesita envios.consultar.

El código devuelve 401 para credenciales incorrectas. El OpenAPI local anuncia 200 para login, pero no documenta ese 401. El endpoint limita los intentos: el código contempla 429 Too Many Requests si se supera el límite de cinco solicitudes por minuto desde la misma IP.

## 3. Obtener un operador activo

Método y URL

GET {{baseUrl}}/api/operadores

Headers

Authorization: Bearer {{accessToken}}
Accept: application/json

Respuesta ilustrativa; los valores reales dependen de tu base:

[
  {
    "operadorId": "<ID real devuelto por la API>",
    "nombre": "<nombre devuelto por la API>"
  }
]

Elegí el operador que corresponda y copiá su operadorId en la variable de Postman operadorId. El endpoint devuelve operadores activos visibles para el acceso Commerce y exige identidad de tipo Comercio. El alta vuelve a validar que el operador seleccionado siga activo. Según la ADR, la selección es por envío; no presupongas una membresía permanente comercio–operador.

## 4. Crear el envío individual

Método y URL

POST {{baseUrl}}/api/envios

Headers

Authorization: Bearer {{accessToken}}
Content-Type: application/json
Accept: application/json

Body → raw → JSON

{
  "operadorId": "{{operadorId}}",
  "destinatarioNombre": "Destinatario de prueba",
  "destinatarioEmail": "destinatario@example.test",
  "direccion": "Calle de prueba 123, Montevideo",
  "codigoBulto": "PM-DEMO-001",
  "pesoGramos": 1250.5,
  "largoCentimetros": 32,
  "anchoCentimetros": 24,
  "altoCentimetros": 18
}

Son campos requeridos por CrearEnvioRequest; el contrato individual no define campos opcionales. Los textos admiten hasta 160 caracteres para nombre, 254 para email, 240 para dirección y 80 para código de bulto. El email debe tener formato válido. Peso y dimensiones se expresan en gramos y centímetros, respectivamente; cada decimal debe estar entre 0.01 y 999999999. En JSON usá punto decimal.

referenciaExterna no forma parte del alta individual: aparece en el formato de importación CSV, no en CrearEnvioRequest ni en el esquema OpenAPI de POST /api/envios.

No envíes comercioId, creadoPorUsuarioId, estado ni version. El servidor obtiene el comercio y el usuario creador del acceso autenticado y su contexto validado. El cliente solo selecciona operadorId.

## 5. Confirmar la creación y consultar el estado

La creación exitosa devuelve 201 Created. El código fija Location: /api/envios —es la colección, no una URL individual— y un body como este:

{
  "id": "<ID real del envío>",
  "operadorId": "<operador seleccionado>",
  "comercioId": "<comercio del contexto autenticado>",
  "creadoPorUsuarioId": "<usuario autenticado>",
  "usuarioEmail": "<correo del acceso>",
  "operadorNombre": "<nombre del operador>",
  "comercioNombre": "<nombre del comercio>",
  "codigoBulto": "PM-DEMO-001",
  "pesoGramos": 1250.5,
  "largoCentimetros": 32,
  "anchoCentimetros": 24,
  "altoCentimetros": 18
}

El response de creación no incluye estado. El constructor del dominio inicia un envío nuevo en Admitido. Guardá el ID real con este script de Postman:

const body = pm.response.json();
pm.test("El envío fue creado", () =>
  pm.response.to.have.status(201)
);
pm.environment.set("envioId", body.id);

No hay un endpoint general GET /api/envios/{id} en el OpenAPI actual. La consulta disponible es la colección:

GET {{baseUrl}}/api/envios
Authorization: Bearer {{accessToken}}
Accept: application/json

Requiere envios.consultar. Si responde correctamente, buscá el objeto cuyo id coincide con {{envioId}}; debería mostrar estado: "Admitido" y el bulto creado.

Advertencia sobre esa consulta: en el checkout actual, EfEnviosRepository.ListarAsync hace un join directo con la tabla privada de identidades de importación, mientras que el rol API tiene revocado el acceso directo. La auditoría previa reprodujo un error PostgreSQL 42501 en esa lectura con un rol API restringido. No prueba que la imagen Docker activa tenga el mismo código: su OpenAPI coincide con el checkout, pero no pude vincular el binario a una revisión Git. Si el POST devuelve 201 y el GET falla, conservá envioId y no repitas el POST para “probar de nuevo”.

En Commerce, el formulario individual está en /envios/crear y la lista en /envios (“Mis envíos”). La lista también requiere permiso de consulta.

## 6. Errores que pueden aparecer

| Código | Dónde / significado |
|---|---|
| 400 Bad Request | Login con body inválido; o alta con campos requeridos, email, longitudes o medidas inválidos. También puede indicar operador inexistente/inactivo. |
| 401 Unauthorized | Credenciales incorrectas en login; token faltante, inválido o vencido en una operación protegida. |
| 403 Forbidden | El acceso no es de tipo Comercio, o no tiene envios.crear para crear. Para consultar la lista hace falta envios.consultar. |
| 409 Conflict | En alta, por reglas de envío no disponibles, conflicto operativo o comercio suspendido. |
| 429 Too Many Requests | Login limitado a cinco intentos por minuto por IP. Esperá antes de volver a intentar; no cambies el body para eludir el límite. |
| 503 Service Unavailable | El servidor no pudo validar el acceso actual o tuvo una indisponibilidad contemplada por el endpoint. |

El OpenAPI de creación contempla 201, 400, 401, 403, 409 y 503. Para operadores contempla 200, 401 y 403. Si recibís un 403, distinguí el tipo de acceso y los permisos antes de volver a enviar la solicitud; no es un error de formato.

Reintentos: el POST individual no tiene referenciaExterna ni una clave idempotente. Repetirlo después de una respuesta perdida puede crear otro envío. Primero buscá el envioId si recibiste 201 o consultá el listado si está disponible. La idempotencia por referencia externa corresponde a la importación CSV y no se aplica automáticamente a este POST.

Fuentes verificadas: AuthController, LoginRequest/Response, OperadoresDisponiblesController, EfOperadoresRepository, UsuarioActualController, EnviosController, CrearEnvioRequest, EnvioCreado y el agregado Envio; OpenAPI local y http://localhost:5000/openapi/v1.json. El healthcheck local respondió 200. No se usaron credenciales ni se crearon envíos.