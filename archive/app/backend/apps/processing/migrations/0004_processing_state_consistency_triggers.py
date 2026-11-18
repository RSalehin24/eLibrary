from django.db import migrations


SYNC_FUNCTION_SQL = """
CREATE OR REPLACE FUNCTION processing_sync_book_record_state(target_record_id text)
RETURNS void AS $$
DECLARE
    next_state text;
BEGIN
    IF target_record_id IS NULL THEN
        RETURN;
    END IF;

    SELECT state
    INTO next_state
    FROM processing_bookcreationrequest
    WHERE book_record_id = target_record_id
    ORDER BY updated_at DESC, created_at DESC, id ASC
    LIMIT 1;

    IF next_state IS NULL THEN
        SELECT
            CASE
                WHEN linked_book_id IS NOT NULL THEN 'created'
                WHEN book_creation_state NOT IN (
                    'not_created',
                    'initial',
                    'queued',
                    'processing',
                    'created',
                    'paused',
                    'failed',
                    'duplicate',
                    'deleted'
                ) THEN 'not_created'
                ELSE book_creation_state
            END
        INTO next_state
        FROM processing_bookrecord
        WHERE id = target_record_id;
    END IF;

    UPDATE processing_bookrecord
    SET book_creation_state = next_state,
        updated_at = NOW()
    WHERE id = target_record_id
      AND book_creation_state IS DISTINCT FROM next_state;
END;
$$ LANGUAGE plpgsql;
"""


REQUEST_TRIGGER_SQL = """
CREATE OR REPLACE FUNCTION processing_bookcreationrequest_sync_record_state()
RETURNS trigger AS $$
BEGIN
    IF TG_OP = 'DELETE' THEN
        PERFORM processing_sync_book_record_state(OLD.book_record_id);
        RETURN OLD;
    END IF;

    PERFORM processing_sync_book_record_state(NEW.book_record_id);

    IF TG_OP = 'UPDATE' AND OLD.book_record_id IS DISTINCT FROM NEW.book_record_id THEN
        PERFORM processing_sync_book_record_state(OLD.book_record_id);
    END IF;

    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS processing_bookcreationrequest_sync_record_state_trigger
ON processing_bookcreationrequest;

CREATE TRIGGER processing_bookcreationrequest_sync_record_state_trigger
AFTER INSERT OR UPDATE OF state, book_record_id, updated_at, created_at OR DELETE
ON processing_bookcreationrequest
FOR EACH ROW
EXECUTE FUNCTION processing_bookcreationrequest_sync_record_state();
"""


RECORD_TRIGGER_SQL = """
CREATE OR REPLACE FUNCTION processing_bookrecord_enforce_creation_state()
RETURNS trigger AS $$
DECLARE
    latest_state text;
BEGIN
    SELECT state
    INTO latest_state
    FROM processing_bookcreationrequest
    WHERE book_record_id = NEW.id
    ORDER BY updated_at DESC, created_at DESC, id ASC
    LIMIT 1;

    IF latest_state IS NOT NULL THEN
        NEW.book_creation_state := latest_state;
    ELSIF NEW.linked_book_id IS NOT NULL THEN
        NEW.book_creation_state := 'created';
    ELSIF NEW.book_creation_state NOT IN (
        'not_created',
        'initial',
        'queued',
        'processing',
        'created',
        'paused',
        'failed',
        'duplicate',
        'deleted'
    ) THEN
        NEW.book_creation_state := 'not_created';
    END IF;

    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS processing_bookrecord_enforce_creation_state_trigger
ON processing_bookrecord;

CREATE TRIGGER processing_bookrecord_enforce_creation_state_trigger
BEFORE INSERT OR UPDATE OF book_creation_state, linked_book_id
ON processing_bookrecord
FOR EACH ROW
EXECUTE FUNCTION processing_bookrecord_enforce_creation_state();
"""


DROP_SQL = """
DROP TRIGGER IF EXISTS processing_bookrecord_enforce_creation_state_trigger
ON processing_bookrecord;
DROP FUNCTION IF EXISTS processing_bookrecord_enforce_creation_state();
DROP TRIGGER IF EXISTS processing_bookcreationrequest_sync_record_state_trigger
ON processing_bookcreationrequest;
DROP FUNCTION IF EXISTS processing_bookcreationrequest_sync_record_state();
DROP FUNCTION IF EXISTS processing_sync_book_record_state(text);
"""


class Migration(migrations.Migration):
    dependencies = [
        ("processing", "0003_processing_ui_state"),
    ]

    operations = [
        migrations.RunSQL(
            sql=SYNC_FUNCTION_SQL + REQUEST_TRIGGER_SQL + RECORD_TRIGGER_SQL,
            reverse_sql=DROP_SQL,
        ),
    ]
