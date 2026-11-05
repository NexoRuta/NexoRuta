using System.Net;
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
 var evidencias=new EvidenciasLocales(datos,archivos);
 var foto=await evidencias.GuardarAsync(cuenta,jornadaId,entregaId,"Foto",Foto.Bytes);
 var resultados=entrega.Bultos.Select((b,i)=>new ResultadoBultoMovil(b.Id,b.Version,i<2,i<2?null:"AUSENTE")).ToArray();
 var d=new DatosOperacionMovil{FotoId=foto.Id,Nombre="Receptor sintético",Latitud=-34.9,Longitud=-56.2,PrecisionMetros=10,PosicionEnUtc=DateTimeOffset.UtcNow,ResultadosBultos=resultados};
 await datos.RegistrarConCapturasAsync(cuenta,jornadaId,[foto.Id],j=>j.RegistrarBultos(entregaId,Elemento(d),DateTimeOffset.UtcNow));
 var retiro=hoja.Paradas.Single(p=>p.EnvioId==retiroId);
 var fotoRetiro=await evidencias.GuardarAsync(cuenta,jornadaId,retiroId,"Foto",Foto.Bytes);
 var firma=await evidencias.GuardarAsync(cuenta,jornadaId,retiroId,"Firma",Foto.Bytes);
 var rd=new DatosOperacionMovil{FotoId=fotoRetiro.Id,FirmaId=firma.Id,ResultadosBultos=retiro.Bultos.Select(b=>new ResultadoBultoMovil(b.Id,b.Version,true,null)).ToArray()};
 await datos.RegistrarConCapturasAsync(cuenta,jornadaId,[fotoRetiro.Id,firma.Id],j=>j.RegistrarBultos(retiroId,Elemento(rd),DateTimeOffset.UtcNow,true));
 try { await sync.SincronizarAsync(cuenta,jornadaId);throw new InvalidOperationException("Network was not blocked."); }
 catch(HttpRequestException) { }
 if((await datos.LeerAsync(cuenta,jornadaId))!.CantidadPendientes!=2)throw new InvalidOperationException("Missing durable operations.");
 Console.WriteLine("Red bloqueada: 2 operaciones y 3 evidencias persistidas. El proceso termina; ejecutar sync en un proceso nuevo.");
}
else if(modo=="sync")
{
 cuenta=await cliente.ObtenerCuentaLocalAsync()??throw new InvalidOperationException("Missing persisted session.");
 var pendientes=(await datos.LeerAsync(cuenta,jornadaId))!.CantidadPendientes;
 if(pendientes!=2)throw new InvalidOperationException("Expected the offline queue from the previous process.");
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
else throw new ArgumentException("Modes: offline, sync");
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
