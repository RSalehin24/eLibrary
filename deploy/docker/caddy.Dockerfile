# Same base as the official image (tag pinned in dev, digest at release; D-64), run as non-root:
# the volume mount points are owned by the unprivileged user so the named volumes are writable.
FROM caddy:2
RUN mkdir -p /data/caddy /config/caddy && chown -R 10001:10001 /data /config
USER 10001
