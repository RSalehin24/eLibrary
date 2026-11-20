-- The one visibility filter (INV-CAT-002, 003): a book is public iff it has a published current
-- version and no tombstone. Reader-facing queries read this view and never the base tables for
-- visibility; the view has no source-link column.
create view visible_books as
select b.id as book_id, b.slug, v.id as version_id, v.title, v.subtitle, v.language,
       v.edition_label, v.publisher_agent_id, v.first_published, v.summary,
       v.state_changed_at as published_at
from books b
join book_versions v on v.id = b.current_version_id
where b.deleted_at is null and v.state = 'published';
