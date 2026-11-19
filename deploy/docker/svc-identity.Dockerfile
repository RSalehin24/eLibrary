FROM rust:1.100-slim AS build
WORKDIR /src
COPY Cargo.toml Cargo.lock clippy.toml ./
COPY crates ./crates
RUN cargo build --release --locked -p svc-identity

FROM debian:trixie-slim
RUN useradd --system --no-create-home --uid 10001 elibrary
COPY --from=build /src/target/release/svc-identity /usr/local/bin/svc-identity
USER 10001
# why: slim has no curl; bash can open a TCP socket for the internal health probe.
HEALTHCHECK --interval=10s --timeout=3s --start-period=5s --retries=3 \
  CMD bash -c 'exec 3<>/dev/tcp/127.0.0.1/9090 && printf "GET /internal/ready HTTP/1.0\r\n\r\n" >&3 && head -n1 <&3 | grep -q " 200 "'
ENTRYPOINT ["/usr/local/bin/svc-identity"]
