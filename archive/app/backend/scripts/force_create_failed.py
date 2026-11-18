"""One-off: force-generate all failed BookCreationRequests and report results.

Run inside a backend container:
    docker exec -e DJANGO_SETTINGS_MODULE=config.settings compose-backend-1 \
        python scripts/force_create_failed.py
"""
import os
import sys

sys.path.insert(0, "/app")
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")

import django

django.setup()

from apps.processing import services  # noqa: E402
from apps.processing.models import BookCreationRequest  # noqa: E402
from apps.catalog.models.books import GeneratedAsset  # noqa: E402
from django.db import connection  # noqa: E402


def title_for(req):
    sub = getattr(req, "submission", None)
    return (
        getattr(sub, "title", None)
        or getattr(getattr(req, "linked_book", None), "title", None)
        or getattr(getattr(req, "book_record", None), "name", None)
        or ""
    )


def main():
    failed = list(
        BookCreationRequest.objects.filter(state="failed").order_by("id")
    )
    print(f"Processing {len(failed)} failed requests with force_generate...\n")
    results = []
    for req in failed:
        rid = req.id
        title = title_for(req)
        connection.close()  # start each request with a fresh connection
        try:
            services.apply_request_action([rid], "force_generate")
            services.kickoff_request_processing(rid)
            req.refresh_from_db()
            book = req.linked_book
            assets = []
            if book is not None:
                assets = list(
                    GeneratedAsset.objects.filter(book=book).values_list(
                        "asset_type", "status"
                    )
                )
            slug = getattr(book, "slug", None)
            ok = req.state == "created"
            results.append((ok, rid, title, req.state, slug, assets, (req.error_message or "")[:120]))
            print(f"[{'OK ' if ok else 'XX '}] {req.state:9} | {title[:34]:34} | {slug} | {assets}")
            if not ok and req.error_message:
                print(f"        err: {req.error_message[:140]}")
        except Exception as exc:  # noqa: BLE001
            connection.close()  # reset any aborted transaction state
            try:
                req.refresh_from_db()
                state = req.state
            except Exception:  # noqa: BLE001
                connection.close()
                state = "unknown"
            results.append((False, rid, title, state, None, [], str(exc)[:140]))
            print(f"[EXC] {state:9} | {title[:34]:34} | EXCEPTION: {str(exc)[:120]}")

    ok_count = sum(1 for r in results if r[0])
    print("\n==================== SUMMARY ====================")
    print(f"created: {ok_count} / {len(results)}")
    print("\n--- CREATED (verifiable in frontend) ---")
    for r in results:
        if r[0]:
            print(f"  {r[2][:40]} | slug={r[4]}")
    print("\n--- NOT CREATED ---")
    for r in results:
        if not r[0]:
            print(f"  {r[2][:40]} | state={r[3]} | {r[6]}")


if __name__ == "__main__":
    main()
