import sys
import time
import django
django.setup()

from django.utils import timezone
from apps.catalog.models import Book, BookSource
from apps.ingestion.services.submissions import queue_reprocess_book
from apps.ingestion.models import ProcessingJob

def main():
    # 1. Fetch 15 existing books with real ebanglalibrary.com source URLs in a single query
    print("Fetching books to reprocess...")
    sources = BookSource.objects.filter(
        normalized_source_url__contains="ebanglalibrary.com",
        book__deleted_at__isnull=True
    ).select_related('book')[:15]
    
    books = [s.book for s in sources if s.book]

    if len(books) < 15:
        # Fallback to any books if not enough real ones found
        print(f"Only found {len(books)} books with real ebanglalibrary.com URLs, fetching any books...")
        remaining = 15 - len(books)
        any_books = list(Book.objects.filter(deleted_at__isnull=True)[:remaining])
        books.extend(any_books)

    print(f"Found {len(books)} books to reprocess:")
    for book in books:
        print(f" - {book.id}: {book.title}")

    # 2. Trigger reprocessing for each book
    reprocess_jobs = []
    print("\n[Step 1] Triggering reprocessing for books...")
    for book in books:
        try:
            job, created = queue_reprocess_book(book)
            reprocess_jobs.append(job)
            print(f"Queued reprocess job {job.id} for book '{book.title}'")
        except Exception as e:
            print(f"Failed to queue reprocess for book '{book.title}': {e}")

    if not reprocess_jobs:
        print("Error: No reprocess jobs were queued.")
        sys.exit(1)

    # 3. Monitor reprocessing jobs
    job_ids = [str(job.id) for job in reprocess_jobs]
    start_time = time.time()
    timeout = 300  # seconds
    all_finished = False

    print("\n[Step 2] Monitoring reprocessing job states...")
    while time.time() - start_time < timeout:
        states = {}
        finished_count = 0
        for j_id in job_ids:
            try:
                job = ProcessingJob.objects.get(pk=j_id)
                state = job.status
                states[j_id] = state
                if state in ["succeeded", "failed"]:
                    finished_count += 1
            except ProcessingJob.DoesNotExist:
                states[j_id] = "deleted"
                finished_count += 1
                
        current_time = timezone.now().strftime("%H:%M:%S")
        states_summary = ", ".join([f"{j_id[:8]}: {state}" for j_id, state in list(states.items())[:5]])
        print(f"[{current_time}] ({finished_count}/{len(job_ids)} finished). Sample states: {states_summary}...")
        
        if finished_count == len(job_ids):
            all_finished = True
            break
            
        time.sleep(5)

    if all_finished:
        print(f"\nAll {len(job_ids)} books were successfully reprocessed and completed!")
        sys.exit(0)
    else:
        print("\nTimeout waiting for reprocessing to finish.")
        sys.exit(1)

if __name__ == "__main__":
    main()
