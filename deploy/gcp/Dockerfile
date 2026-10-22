FROM mcr.microsoft.com/dotnet/sdk:10.0.401 AS build
ARG PROJECT
WORKDIR /src
COPY . .
RUN dotnet publish "$PROJECT" -c Release -o /out /p:UseAppHost=false

FROM mcr.microsoft.com/dotnet/aspnet:10.0 AS runtime
RUN apt-get update && apt-get install -y --no-install-recommends curl libgssapi-krb5-2 \
    && rm -rf /var/lib/apt/lists/*
ARG ASSEMBLY
WORKDIR /app
COPY --from=build /out .
ENV APP_ASSEMBLY=$ASSEMBLY ASPNETCORE_URLS=http://+:8080 DOTNET_GCHeapHardLimitPercent=0x4B
EXPOSE 8080
ENTRYPOINT ["sh", "-c", "exec dotnet \"$APP_ASSEMBLY.dll\" \"$@\"", "--"]
