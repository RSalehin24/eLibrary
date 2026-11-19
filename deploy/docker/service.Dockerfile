# One Dockerfile for every Rust service: docker build --build-arg SERVICE=identity ...
# Targets: `runtime` (default) and `runtime-java` (ingestion: adds the JRE and epubcheck, D-47).
FROM rust:1.100-slim AS build
ARG SERVICE
WORKDIR /src
COPY Cargo.toml Cargo.lock clippy.toml ./
COPY crates ./crates
COPY xtask ./xtask
RUN cargo build --release --locked -p "svc-${SERVICE}" \
 && mkdir /out \
 && find target/release -maxdepth 1 -type f -executable -name "svc-${SERVICE}*" -exec cp {} /out/ \;

FROM debian:trixie-slim AS epubcheck
ARG EPUBCHECK_VERSION=5.4.0
ARG EPUBCHECK_SHA256=33350c61038e71dfb3d45a76aed04bf5481e6d5500cb780f6e98db8bbd15a28c
RUN apt-get update && apt-get install -y --no-install-recommends ca-certificates curl unzip \
 && curl -fsSL -o /tmp/epubcheck.zip "https://github.com/w3c/epubcheck/releases/download/v${EPUBCHECK_VERSION}/epubcheck-${EPUBCHECK_VERSION}.zip" \
 && echo "${EPUBCHECK_SHA256}  /tmp/epubcheck.zip" | sha256sum --check --quiet \
 && unzip -q /tmp/epubcheck.zip -d /opt \
 && mv "/opt/epubcheck-${EPUBCHECK_VERSION}" /opt/epubcheck

FROM debian:trixie-slim AS runtime-base
ARG SERVICE
RUN useradd --system --no-create-home --uid 10001 elibrary
COPY --from=build /out/ /usr/local/bin/
RUN ln -s "/usr/local/bin/svc-${SERVICE}" /usr/local/bin/service
# why: slim has no curl; bash can open a TCP socket for the internal health probe.
HEALTHCHECK --interval=10s --timeout=3s --start-period=10s --start-interval=1s --retries=3 \
  CMD bash -c 'exec 3<>/dev/tcp/127.0.0.1/9090 && printf "GET /internal/ready HTTP/1.0\r\n\r\n" >&3 && head -n1 <&3 | grep -q " 200 "'
ENTRYPOINT ["/usr/local/bin/service"]

FROM runtime-base AS runtime-java
RUN apt-get update && apt-get install -y --no-install-recommends openjdk-21-jre-headless \
 && rm -rf /var/lib/apt/lists/*
COPY --from=epubcheck /opt/epubcheck /opt/epubcheck
USER 10001

FROM runtime-base AS runtime
USER 10001
