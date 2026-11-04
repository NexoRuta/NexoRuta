FROM grafana/k6:1.4.2@sha256:3656673de3f30424e8ebcfa46acd9558d83b6a43612d0f668ffeac953950c6c7 AS k6
FROM python:3.13-slim-bookworm@sha256:281d39ff02e3b389401586134ff9e6572954687822a58055ec07a60ded4e0b7f

COPY --from=k6 /usr/bin/k6 /usr/local/bin/k6
WORKDIR /suite
COPY tests/load/ /suite/
COPY deploy/load/runner.py deploy/load/supervision.py deploy/load/sessions.py /suite/
RUN groupadd --gid 10001 nexoruta && useradd --uid 10001 --gid 10001 --no-create-home nexoruta \
    && mkdir -p /tmp/nexoruta-home && chown 10001:10001 /tmp/nexoruta-home
ENV HOME=/tmp/nexoruta-home
USER 10001:10001
ENTRYPOINT ["python3", "/suite/runner.py"]
