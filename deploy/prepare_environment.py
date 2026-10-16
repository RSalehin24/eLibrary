import argparse
import os
import re
import secrets
from pathlib import Path


def canonical_hostname(value):
    hostname = value.strip().encode("idna").decode("ascii").lower()
    labels = hostname.split(".")
    if (
        len(hostname) > 253
        or len(labels) < 2
        or any(
            not re.fullmatch(r"[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?", label)
            for label in labels
        )
    ):
        raise ValueError("Use a DNS hostname without a scheme, port, or path.")
    return hostname


def environment_values(hostname, directory):
    database, cache, broker = (secrets.token_hex(32) for _ in range(3))
    hostname = canonical_hostname(hostname)
    return {
        "PUBLIC_HOST": hostname,
        "PUBLIC_SITE_URL": f"https://{hostname}",
        "TLS_DIRECTORY": str(directory.resolve() / "tls"),
        "DJANGO_SECRET_KEY": secrets.token_hex(48),
        "POSTGRES_ADMIN_PASSWORD": secrets.token_hex(32),
        "APP_DATABASE_PASSWORD": database,
        "REDIS_PASSWORD": cache,
        "RABBITMQ_PASSWORD": broker,
        "DATABASE_URL": f"postgresql://library:{database}@postgres:5432/library",
        "CELERY_BROKER_URL": f"amqp://library:{broker}@rabbitmq:5672/library",
        "REDIS_RESULT_URL": f"redis://:{cache}@redis:6379/0",
        "REDIS_CACHE_URL": f"redis://:{cache}@redis:6379/1",
    }


def render_environment(values):
    lines = []
    for name, value in values.items():
        if not re.fullmatch(r"[A-Z][A-Z0-9_]*", name) or any(
            character in value for character in "\r\n\0"
        ):
            raise ValueError(
                "Environment fields must use valid names and single-line values."
            )
        escaped = value.replace("'", "\\'")
        lines.append(f"{name}='{escaped}'\n")
    return "".join(lines)


def write_environment(path, values):
    contents = render_environment(values)
    descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(descriptor, "w") as stream:
        stream.write(contents)


def main():
    parser = argparse.ArgumentParser(
        description="Prepare a private environment; no deployment or account creation."
    )
    parser.add_argument("--hostname", required=True)
    parser.add_argument(
        "--output", type=Path, default=Path(__file__).with_name("platform.env")
    )
    arguments = parser.parse_args()
    values = environment_values(arguments.hostname, arguments.output.parent)
    write_environment(arguments.output, values)
    print(
        f"Created private configuration: {arguments.output}. Configure SMTP and certificate files before deployment."
    )


if __name__ == "__main__":
    main()
