using System.Net;
using NexoRuta.Mobile.Presentacion;
using NexoRuta.Mobile.Captura;
using NexoRuta.Mobile.Core.Identidad;
using NexoRuta.Mobile.Ubicacion;
using System.Text.Json;
using NexoRuta.Mobile.Api.Identidad;
using NexoRuta.Mobile.Api.Reparto;
using NexoRuta.Mobile.Core.Jornadas;
using NexoRuta.Mobile.Core.Rutas;
using NexoRuta.Mobile.Application;
using NexoRuta.Mobile.Storage;

var root=Path.GetFullPath(args[0]);var modo=args[1];
var state=Path.Combine(root,".local/codex-cloud");
var secret=JsonDocument.Parse(await File.ReadAllTextAsync(Path.Combine(state,"private.json"))).RootElement;
if(secret.GetProperty("purpose").GetString()!="nexoruta-disposable-cloud")throw new InvalidOperationException("Owned synthetic runtime required.");
var demo=JsonDocument.Parse(await File.ReadAllTextAsync(Path.Combine(state,"demo-cambios.json"))).RootElement;
var directory=Path.Combine(state,"demo-mobile");Directory.CreateDirectory(directory);
var transport=new LoopbackTransport();using var cliente=new ClienteSesionMovil(new Uri("https://demo.cloud.test/"),new Sesion(Path.Combine(directory,"session.json")),transport);
var claves=new Claves(Path.Combine(directory,"keys.json"));
using var datos=new RepositorioJornadasSqlite(Path.Combine(directory,"sqlite"),claves);
using var archivos=new RepositorioArchivosCifrados(Path.Combine(directory,"evidence"),claves);
using var sync=new SincronizadorJornada(cliente,datos,archivos);
var ruta=demo.GetProperty("rutaId").GetGuid();var jornadaId=demo.GetProperty("jornadaId").GetGuid();
var entregaId=demo.GetProperty("entregaId").GetGuid();var retiroId=demo.GetProperty("retiroId").GetGuid();
CuentaMovil cuenta;
if(modo=="offline")
{
 cuenta=await cliente.IngresarAsync(secret.GetProperty("operatorEmail").GetString()!,secret.GetProperty("operatorPassword").GetString()!);
 var hoja=(await cliente.ObtenerHojasAsync(DateOnly.FromDateTime(DateTime.UtcNow.AddHours(-3)))).Single(h => h.Id == ruta);
 await datos.GuardarHojaAsync(cuenta,ruta,SerializadorHojaRuta.Serializar(hoja));
 var jornada=JornadaLocal.Iniciar(jornadaId,ruta,cuenta,DateTimeOffset.UtcNow);await datos.CrearAsync(jornada);
 await sync.SincronizarAsync(cuenta,jornadaId);
 var entrega=hoja.Paradas.Single(p=>p.EnvioId==entregaId);
 foreach(var b in entrega.Bultos.Take(2))await datos.ModificarAsync(cuenta,jornadaId,j=>j.RegistrarCarga(entregaId,Elemento(new DatosOperacionMovil{BultoId=b.Id}),DateTimeOffset.UtcNow));
 await datos.ModificarAsync(cuenta,jornadaId,j=>j.ConfirmarCarga(DateTimeOffset.UtcNow));
 await sync.SincronizarAsync(cuenta,jornadaId);
 // The transport rejects every HTTP call. No in-memory queue or fake server is used.
 transport.Offline=true;
 var io=new InteraccionDemo();
 var padre=new HojaRutaViewModel(hoja,cuenta,datos,io,io,io,cliente,sync);await padre.Refrescar();
 var evidencias=new EvidenciasLocales(datos,archivos);
 var formulario=new EntregaViewModel(padre,entrega,datos,evidencias,io);await formulario.InicializarAsync();
 foreach(var b in formulario.Seleccion.Take(2))b.Escaneado=true;
 formulario.Seleccion.Last().Motivo=entrega.Reglas.Motivos.Single(m=>m.Codigo=="AUSENTE");formulario.Nombre="Receptor sintético";
 if(!formulario.Entregar.CanExecute(null))throw new InvalidOperationException("Delivery form disabled before physical declaration");
 await formulario.Entregar.EjecutarAsync();
 if(!formulario.PuedeRegistrar||!formulario.TomarFoto.CanExecute(null))throw new InvalidOperationException("H3: offline evidence capture disabled");
 await formulario.TomarFoto.EjecutarAsync();await formulario.Entregar.EjecutarAsync();formulario.Desconectar();
 var retiro=hoja.Paradas.Single(p=>p.EnvioId==retiroId);
 var retirar=new EntregaViewModel(padre,retiro,datos,evidencias,io);await retirar.InicializarAsync();
 foreach(var b in retirar.Seleccion)b.Escaneado=true;
 await retirar.TomarFoto.EjecutarAsync();await retirar.Firmar.EjecutarAsync();await retirar.Entregar.EjecutarAsync();
 if(!retirar.Mensaje.Contains("pendiente"))throw new InvalidOperationException("Unconfirmed pickup presented as success");retirar.Desconectar();
 try { await sync.SincronizarAsync(cuenta,jornadaId);throw new InvalidOperationException("Network was not blocked."); }
 catch(HttpRequestException) { }
 if((await datos.LeerAsync(cuenta,jornadaId))!.CantidadPendientes!=3)throw new InvalidOperationException("Missing durable operations.");
 Console.WriteLine("Red bloqueada: 3 operaciones mediante ViewModels y 3 evidencias persistidas. El proceso termina; ejecutar sync en un proceso nuevo.");
}
else if(modo=="sync")
{
 cuenta=await cliente.ObtenerCuentaLocalAsync()??throw new InvalidOperationException("Missing persisted session.");
 var pendientes=(await datos.LeerAsync(cuenta,jornadaId))!.CantidadPendientes;
 if(pendientes!=3)throw new InvalidOperationException("Expected the offline queue from the previous process.");
 await sync.SincronizarAsync(cuenta,jornadaId);
 var acuses=(await datos.LeerConfirmacionesAsync(cuenta,jornadaId)).Select(b=>JsonSerializer.Deserialize(b,ContratosRepartoJson.Default.ConfirmacionOperacion)!).ToArray();
 if(acuses.Any(a=>a.Resultado!="Aplicada"))throw new InvalidOperationException(string.Join("; ",acuses.Where(a=>a.Resultado!="Aplicada").Select(a=>a.Detalle)));
 var actual=(await cliente.ObtenerHojasAsync(DateOnly.FromDateTime(DateTime.UtcNow.AddHours(-3)))).Single(h => h.Id == ruta);
 if(actual.Paradas.Single(p=>p.EnvioId==entregaId).Estado!="EntregadoParcialmente"||actual.Paradas.Single(p=>p.EnvioId==retiroId).Estado!="Retirado")throw new InvalidOperationException("Unexpected remote results.");
 await datos.ModificarAsync(cuenta,jornadaId,j=>j.DeclararRendicion(Elemento(new DatosOperacionMovil{BultoIds=actual.Paradas.Where(p=>p.EsRetiro).SelectMany(p=>p.Bultos).Select(b=>b.Id).ToArray()}),DateTimeOffset.UtcNow));
 await datos.ModificarAsync(cuenta,jornadaId,j=>j.Finalizar(DateTimeOffset.UtcNow));
 await sync.SincronizarPendientesAsync(cuenta);
 Console.WriteLine("Proceso nuevo: cola y evidencias recuperadas; API real confirmó parcial 2/3, retiro y cierre. Retorno/liberación quedan para constatación física en Backoffice.");
}
else if(modo=="revisit")
{
 cuenta=await cliente.ObtenerCuentaLocalAsync()??throw new InvalidOperationException("Missing persisted session");
 var id=demo.GetProperty("revisitaId").GetGuid();
 var hoja=(await cliente.ObtenerHojasAsync(DateOnly.FromDateTime(DateTime.UtcNow.AddHours(-3)))).Single(h=>h.Id==id);
 if(hoja.Paradas.Single().Bultos.Length!=1)throw new InvalidOperationException("The revisit must contain only the outstanding parcel");
 await datos.GuardarHojaAsync(cuenta,id,SerializadorHojaRuta.Serializar(hoja));
 var jornada=JornadaLocal.Iniciar(hoja.JornadaId,id,cuenta,DateTimeOffset.UtcNow);await datos.CrearAsync(jornada);await sync.SincronizarAsync(cuenta,hoja.JornadaId);
 var bulto=hoja.Paradas.Single().Bultos.Single();
 await datos.ModificarAsync(cuenta,hoja.JornadaId,j=>j.RegistrarCarga(entregaId,Elemento(new(){BultoId=bulto.Id}),DateTimeOffset.UtcNow));
 await datos.ModificarAsync(cuenta,hoja.JornadaId,j=>j.ConfirmarCarga(DateTimeOffset.UtcNow));await sync.SincronizarAsync(cuenta,hoja.JornadaId);
 var io=new InteraccionDemo();var padre=new HojaRutaViewModel(hoja,cuenta,datos,io,io,io,cliente,sync);await padre.Refrescar();
 var formulario=new EntregaViewModel(padre,hoja.Paradas.Single(),datos,new EvidenciasLocales(datos,archivos),io);await formulario.InicializarAsync();
 formulario.Seleccion.Single().Escaneado=true;formulario.Nombre="Receptor segunda visita";
 await formulario.TomarFoto.EjecutarAsync();await formulario.Entregar.EjecutarAsync();
 var actual=(await cliente.ObtenerHojasAsync(DateOnly.FromDateTime(DateTime.UtcNow.AddHours(-3)))).Single(h=>h.Id==id);
 if(actual.Paradas.Single().Estado!="Entregado")throw new InvalidOperationException(formulario.Mensaje);
 await datos.ModificarAsync(cuenta,hoja.JornadaId,j=>j.Finalizar(DateTimeOffset.UtcNow));await sync.SincronizarAsync(cuenta,hoja.JornadaId);
 formulario.Desconectar();Console.WriteLine("Segunda visita ejecutada desde EntregaViewModel: resultado remoto Entregado, solo el bulto pendiente y cierre confirmado.");
}
else throw new ArgumentException("Modes: offline, sync, revisit");
static JsonElement Elemento(DatosOperacionMovil d)=>JsonSerializer.SerializeToElement(d,DatosOperacionJson.Default.DatosOperacionMovil);

sealed class LoopbackTransport:DelegatingHandler
{
 public bool Offline{get;set;}
 public LoopbackTransport():base(new HttpClientHandler{UseProxy=false,AllowAutoRedirect=false}){}
 protected override Task<HttpResponseMessage> SendAsync(HttpRequestMessage request,CancellationToken ct)
 {
  if(Offline)throw new HttpRequestException("Synthetic demonstration: no connectivity.");
  request.RequestUri=new Uri("http://127.0.0.1:5000"+request.RequestUri!.PathAndQuery);request.Headers.Host=null;
  return base.SendAsync(request,ct);
 }
}
sealed class Sesion(string path):IAlmacenSesionMovil
{
 public async Task<EstadoSesionMovil?> LeerAsync(string api)=>File.Exists(path)?SerializadorSesionMovil.Deserializar(await File.ReadAllTextAsync(path)):null;
 public async Task GuardarAsync(EstadoSesionMovil s){await File.WriteAllTextAsync(path,SerializadorSesionMovil.Serializar(s));File.SetUnixFileMode(path,UnixFileMode.UserRead|UnixFileMode.UserWrite);}
 public Task EliminarAsync(string api){File.Delete(path);return Task.CompletedTask;}
}
sealed class Claves(string path):IAlmacenClavesProtegidas
{
 public async Task<string?> ObtenerAsync(string nombre)=>File.Exists(path)?JsonSerializer.Deserialize<Dictionary<string,string>>(await File.ReadAllTextAsync(path))!.GetValueOrDefault(nombre):null;
 public async Task GuardarAsync(string nombre,string valor){var d=File.Exists(path)?JsonSerializer.Deserialize<Dictionary<string,string>>(await File.ReadAllTextAsync(path))!:[];d[nombre]=valor;await File.WriteAllTextAsync(path,JsonSerializer.Serialize(d));File.SetUnixFileMode(path,UnixFileMode.UserRead|UnixFileMode.UserWrite);}
}

static class Foto { public static readonly byte[] Bytes=Convert.FromBase64String("iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR4nGP4z8DwHwAFAAH/iZk9HQAAAABJRU5ErkJggg=="); }

sealed class InteraccionDemo:IInteraccionReparto,ITrackingJornada,IVerificacionLocal
{
 public Task<bool> IniciarAsync()=>Task.FromResult(true);public void Detener(){}
 public Task<bool> VerificarAsync(string motivo,CancellationToken ct=default)=>Task.FromResult(true);
 public Task<string?> EscanearAsync()=>Task.FromResult<string?>(null);
 public Task<byte[]?> FotoAsync()=>Task.FromResult<byte[]?>(Foto.Bytes.ToArray());public Task<byte[]?> FirmaAsync()=>Task.FromResult<byte[]?>(Foto.Bytes.ToArray());
 public Task<Guid[]?> SeleccionarRendicionAsync(IReadOnlyList<BultoRuta> bultos)=>Task.FromResult<Guid[]?>(bultos.Select(b=>b.Id).ToArray());
 public Task<bool> ConfirmarSalidaConDiferenciasAsync(int bultosPendientes,int paradasAfectadas)=>Task.FromResult(true);
 public Task<bool> ConfirmarCierreAsync(bool pruebaPendiente,int bultosSinRendir)=>Task.FromResult(true);
}
