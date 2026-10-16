import os
from pathlib import Path
from tempfile import mkdtemp

import django


def main():
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
    django.setup()
    from django.conf import settings

    root = Path(__file__).resolve().parents[2]
    output = Path(mkdtemp(prefix="elibrary-protected-proxy-"))
    configuration = root / "deploy" / "nginx"
    for name in (
        "application-routes.conf",
        "proxy-headers.conf",
        "response-security.conf",
    ):
        text = (
            (configuration / name)
            .read_text()
            .replace("/etc/nginx/", output.as_posix() + "/")
        )
        (output / name).write_text(text)
    (output / "nginx.conf").write_text(f'''
pid "{output}/nginx.pid";
error_log "{output}/error.log" warn;
events {{ worker_connections 128; }}
http {{
    access_log off;
    upstream library_api {{ server 127.0.0.1:8001; }}
    upstream library_frontend {{ server 127.0.0.1:3000; }}
    server {{
        listen 127.0.0.1:8082;
        set $security_hsts "";
        set $protected_storage "{Path(settings.MEDIA_ROOT).resolve()}";
        set $maintenance_static "{root}/app/backend/static";
        set $frontend_static "{root}/app/web/.next/static";
        include "{output}/application-routes.conf";
    }}
}}
''')
    print(output / "nginx.conf")


if __name__ == "__main__":
    main()
