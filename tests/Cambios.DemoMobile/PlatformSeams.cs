// Portable demo inputs. These do not test native GPS, camera, scanner or signature UI.
namespace NexoRuta.Mobile.Presentacion;
internal enum GeolocationAccuracy { Best }
internal sealed record GeolocationRequest(GeolocationAccuracy Accuracy,TimeSpan Timeout);
internal sealed class Location
{
 public double? Accuracy { get; init; }=10;public double Latitude { get; init; }=-34.9;
 public double Longitude { get; init; }=-56.2;public DateTimeOffset Timestamp { get; init; }=DateTimeOffset.UtcNow;
}
internal sealed class Geolocation
{
 public static Geolocation Default { get; }=new();
 public Task<Location?> GetLocationAsync(GeolocationRequest request,CancellationToken ct)=>Task.FromResult<Location?>(new());
}
internal enum NetworkAccess { Internet }
internal static class Connectivity
{
 internal sealed class Connection { public NetworkAccess NetworkAccess=>NetworkAccess.Internet; }
 public static Connection Current { get; }=new();
}
