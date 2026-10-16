# Protected file delivery

The versioned reader and EPUB download endpoints authorize every request in
Django. `PROTECTED_FILES_USE_NGINX=true` then returns an empty response with an
internal redirect. Only resolved, existing files inside `MEDIA_ROOT` are eligible;
symlink escapes and legacy files outside that shared root return 404. Development
keeps Django streaming when this setting is false. No public media route exists.

`deploy/nginx/application-routes.conf` maps the internal `/_protected/` location
to the shared media directory, with symlinks disabled. Direct requests to that
location and `/media/` return 404. API requests reach Django without proxy caching;
legacy API routes are excluded from this deployment surface. Maintenance admin
routes remain available. Hashed Next.js assets have long immutable caching;
missing files do not receive that long-lived policy.

Nginx internal redirects drop some upstream headers. The protected location
explicitly restores the Django reader's Content Security Policy and frame policy
from upstream variables. It also retains private no-store behavior, noindex,
nosniff, and no-referrer. This restoration is required for the reading sandbox.
See [Nginx internal locations](https://nginx.org/en/docs/http/ngx_http_core_module.html#internal)
and [upstream response variables](https://nginx.org/en/docs/http/ngx_http_upstream_module.html#variables).

The production template adds HTTPS, canonical-host handling, and HSTS. It
expects mounted certificates, shared media/static storage, and separately managed
API/frontend services. It has not yet been deployed on Ubuntu/Debian or tested
with production certificates. It is not a complete deployment by itself.

Verification on 2026-10-16 used the existing local Nginx 1.31.2 installation and a
separate Django process on loopback. Actual chapter bytes, MIME type, byte ranges,
sandbox headers, protected EPUB downloads, anonymous denial, and route isolation
passed. Nine focused backend cases cover internal redirects, permission
revocation, missing/outside paths, Unicode filenames, symlink escapes, and the
streaming fallback. The combined reader/protected-file run passed 25 cases.

To repeat against the isolated foundation database:

1. Generate fresh private fixtures with `tests/web/seed_preview.py`.
2. Run Django on port 8001 with `PROTECTED_FILES_USE_NGINX=true` and
   `FRONTEND_BASE_URL=http://127.0.0.1:8082`.
3. Run `tests/web/protected_proxy_configuration.py` with the normal backend
   environment. It prints an isolated temporary Nginx configuration path.
4. Start the installed Nginx with that path and its temporary directory as the
   prefix; keep both logs and PID files in that directory.
5. Run `tests/web/verify_protected_proxy.py` with
   `FOUNDATION_PROXY_URL=http://127.0.0.1:8082` and the private fixture path in
   `FOUNDATION_FIXTURE_PATH`.

The check only accepts loopback HTTP targets and does not contact source sites.
It logs a fixed success message rather than reader session identifiers.
