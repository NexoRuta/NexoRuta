FROM mcr.microsoft.com/dotnet/sdk:10.0.401 AS build
ARG PROJECT
WORKDIR /src
COPY . .
RUN dotnet publish "$PROJECT" -c Release -o /out /p:UseAppHost=false

FROM mcr.microsoft.com/dotnet/aspnet:10.0 AS runtime
ARG ASSEMBLY
RUN apt-get update && apt-get install -y --no-install-recommends curl libgssapi-krb5-2 \
    && rm -rf /var/lib/apt/lists/*
WORKDIR /app
COPY --from=build /out .
ENV APP_ASSEMBLY=$ASSEMBLY ASPNETCORE_URLS=http://+:8080 DOTNET_GCHeapHardLimitPercent=75
EXPOSE 8080
ENTRYPOINT ["sh", "-c", "exec dotnet \"$APP_ASSEMBLY.dll\" \"$@\"", "--"]
