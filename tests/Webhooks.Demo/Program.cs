using System.Text.Json;
using Microsoft.EntityFrameworkCore;
using NexoRuta.Infrastructure.Persistence;
using NexoRuta.IntegrationTests.Fixtures;
using Npgsql;

// Only the generated, owned synthetic Cloud runtime; accepts no arbitrary connection string.
var root=Path.GetFullPath(Path.Combine(AppContext.BaseDirectory,"../../../../../"));
while(!File.Exists(Path.Combine(root,"scripts/cloud/dev.py")))
{var parent=Directory.GetParent(root);if(parent is null)throw new InvalidOperationException("Run inside the NexoRuta checkout.");root=parent.FullName;}
using var state=JsonDocument.Parse(await File.ReadAllTextAsync(Path.Combine(root,".local/codex-cloud/private.json")));
var s=state.RootElement;
if(s.GetProperty("purpose").GetString()!="nexoruta-disposable-cloud" || !s.GetProperty("database").GetString()!.StartsWith("nexoruta_cloud_",StringComparison.Ordinal))throw new InvalidOperationException("Not an owned synthetic Cloud database.");
var conn=new NpgsqlConnectionStringBuilder{Host="127.0.0.1",Port=s.GetProperty("pgPort").GetInt32(),Database=s.GetProperty("database").GetString(),Username=s.GetProperty("ownerUser").GetString(),Password=s.GetProperty("ownerPassword").GetString()}.ConnectionString;
await using var db=new NexoRutaDbContext(new DbContextOptionsBuilder<NexoRutaDbContext>().UseNexoRutaPostgres(conn).Options);
if(await db.Database.SqlQuery<string>($"SELECT current_database() AS \"Value\"").SingleAsync()!=s.GetProperty("database").GetString())throw new InvalidOperationException("Database mismatch.");
await ReglasEnvioTestData.SembrarInicialesAsync(db);await ServiciosEnvioTestData.SembrarAsync(db);
Console.WriteLine("Synthetic rules and coverage/tariff ready. Commerce: http://localhost:5102/webhooks; receiver: http://localhost:5103/comercio. Credentials remain in private.json.");
