# Local broker verification dependency proposal

The next worker increment needs a real RabbitMQ broker to verify publisher
confirmations, duplicate delivery, connection interruptions, and dispatch
recovery. Existing PostgreSQL/Redis verification services remain isolated from
legacy application volumes.

Proposed image: **`rabbitmq:4.3.6-management`**, Docker's official RabbitMQ image.
The publisher's release page lists 4.3.6, released 16 September 2026, with
community support through 31 January 2027. The official-images manifest lists
this exact management tag for Linux AMD64 and ARM64 among other architectures.
Recheck support and image security before production deployment.

Sources checked 14 October 2026:
[RabbitMQ releases](https://www.rabbitmq.com/release-information),
[Docker official image manifest](https://raw.githubusercontent.com/docker-library/official-images/master/library/rabbitmq).

`local/compose/broker-test.yml` is a reviewable, configuration-validated local
broker definition. It binds AMQP and management ports to loopback only, limits
resources, requires a unique externally supplied password, and keeps broker
data in its own named volume. Run it under a separate `elibrary-broker-test`
project after image installation is approved. Never reset the volume as a
verification shortcut. Credentials belong in a mode-0600 file outside the
repository and must not appear in logs or tool output.

No new Python packages are proposed: the installed, previously approved Celery
requirements already provide the AMQP transport. This proposal does not include
k6, production deployment, external email delivery, or destructive cleanup.
The user approved this image and isolated application image builds/tests on
16 October 2026. The broker has been downloaded and exercised in the new
`deploy/compose/platform.yml` test project. Confirmed publication, duplicate
delivery, broker interruption/retry, and persisted-attempt recovery passed.
The separate legacy broker-only Compose definition remains available; see the
[platform deployment guide](../operations/platform-deployment.md) for the tested stack.
