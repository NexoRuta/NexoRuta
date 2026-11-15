FROM --platform=linux/amd64 mcr.microsoft.com/dotnet/sdk:10.0.401@sha256:e70cdb7f80b0348f5cb85f19a8f670fca061f033d57eed12fa003d58b0e06317 AS build
ARG PROJECT
WORKDIR /src
COPY .restore/ ./
RUN dotnet restore "$PROJECT" --locked-mode \
    && find . -type f -name '__nexoruta_restore_shape.razor' -delete
COPY . .
RUN dotnet publish "$PROJECT" -c Release -o /out --no-restore /p:UseAppHost=false

FROM --platform=linux/amd64 mcr.microsoft.com/dotnet/aspnet:10.0@sha256:bfd912c83295ce66d4b706ebb8541b9f14259b0e76fbb88b2751f58ce2399d2e AS runtime
RUN apt-get update && apt-get install -y --no-install-recommends curl libgssapi-krb5-2 \
    && rm -rf /var/lib/apt/lists/*
ARG ASSEMBLY
WORKDIR /app
COPY --from=build /out .
ENV APP_ASSEMBLY=$ASSEMBLY ASPNETCORE_URLS=http://+:8080 DOTNET_GCHeapHardLimitPercent=0x4B
EXPOSE 8080
ENTRYPOINT ["sh", "-c", "exec dotnet \"$APP_ASSEMBLY.dll\" \"$@\"", "--"]
