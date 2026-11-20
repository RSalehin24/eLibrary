-- Catalog core schema (planning/05-services/catalog/domain-model.md). Keys are UUIDs made by the
-- service; times are timestamptz UTC from the injected clock; closed sets are CHECK constraints.
-- Shelf, saved filters, Kindle requests, search documents and download log come with their slices.

create table books (
    id                 uuid primary key,
    slug               text        not null check (slug ~ '^[^/\s]+$' and char_length(slug) <= 200),
    current_version_id uuid,
    latest_version_id  uuid,
    source_key         text        check (source_key is null or char_length(source_key) = 64),
    deleted_at         timestamptz,
    deleted_by         uuid,
    revision           bigint      not null default 0 check (revision >= 0),
    created_at         timestamptz not null,
    updated_at         timestamptz not null,
    check ((deleted_at is null) = (deleted_by is null))
);
create unique index books_slug_unique on books (slug);
create unique index books_source_key_unique on books (source_key) where source_key is not null;

create function books_id_immutable() returns trigger language plpgsql as $$
begin
    if new.id <> old.id then
        raise exception 'books.id is immutable';
    end if;
    return new;
end;
$$;
create trigger books_id_guard before update on books
    for each row execute function books_id_immutable();

-- Every former and current slug; a slug is never reused by another book (INV-CAT-005).
create table book_slugs (
    slug       text primary key,
    book_id    uuid        not null references books (id),
    created_at timestamptz not null
);
create index book_slugs_by_book on book_slugs (book_id);

create table book_versions (
    id                   uuid primary key,
    book_id              uuid        not null references books (id),
    version_no           integer     not null check (version_no > 0),
    state                text        not null check (state in ('published', 'archived')),
    archived_reason      text        check (archived_reason in ('superseded', 'unpublished')),
    title                text        not null check (char_length(title) between 1 and 500),
    subtitle             text,
    language             text        not null check (language in ('bn', 'en')),
    edition_label        text,
    publisher_agent_id   uuid,
    first_published      date,
    summary              text,
    preview_chars        integer     not null default 0 check (preview_chars >= 0),
    build_hash           text        not null check (char_length(build_hash) = 64),
    source_hash          text        not null check (char_length(source_hash) = 64),
    builder_version      text        not null,
    ingestion_request_id text,
    created_by           text        not null,
    created_at           timestamptz not null,
    state_changed_at     timestamptz not null,
    unique (book_id, version_no),
    unique (book_id, build_hash),
    check ((state = 'archived') = (archived_reason is not null))
);
create unique index book_versions_one_published on book_versions (book_id) where state = 'published';

alter table books
    add constraint books_current_version_fk foreign key (current_version_id)
        references book_versions (id) deferrable initially deferred,
    add constraint books_latest_version_fk foreign key (latest_version_id)
        references book_versions (id) deferrable initially deferred;

-- The source link is read on manage routes and by the match call only (INV-CAT-002).
create table book_sources (
    book_id         uuid        not null references books (id),
    source_url      text        not null,
    source_key      text        not null check (char_length(source_key) = 64),
    first_linked_at timestamptz not null,
    primary key (book_id, source_key),
    unique (source_key)
);

create table agents (
    id           uuid primary key,
    kind         text        not null check (kind in ('person', 'organization')),
    display_name text        not null check (char_length(display_name) between 1 and 300),
    exact_key    text        not null,
    merged_into  uuid        references agents (id),
    revision     bigint      not null default 0 check (revision >= 0),
    check (merged_into is null or merged_into <> id)
);
create index agents_by_exact_key on agents (exact_key);

alter table book_versions
    add constraint book_versions_publisher_fk foreign key (publisher_agent_id) references agents (id);

create table agent_aliases (
    agent_id  uuid not null references agents (id),
    alias     text not null,
    script    text not null check (script in ('bengali', 'latin')),
    exact_key text not null,
    loose_key text not null,
    unique (exact_key, agent_id)
);
create index agent_aliases_by_loose_key on agent_aliases (loose_key);

create table credits (
    version_id uuid     not null references book_versions (id),
    agent_id   uuid     references agents (id),
    raw_name   text,
    role       text     not null check (role in
        ('writer', 'translator', 'editor', 'compiler', 'illustrator', 'cover_artist', 'publisher')),
    ordinal    smallint not null check (ordinal >= 0),
    primary key (version_id, role, ordinal),
    check (agent_id is not null or raw_name is not null)
);
create index credits_by_agent on credits (agent_id, role);

create table series (
    id        uuid primary key,
    name      text not null,
    exact_key text not null unique
);
create table version_series (
    version_id uuid not null references book_versions (id),
    series_id  uuid not null references series (id),
    ordinal    numeric,
    primary key (version_id, series_id)
);
create unique index version_series_ordinal_unique on version_series (series_id, ordinal) where ordinal is not null;

create table categories (
    id        uuid primary key,
    name      text not null,
    exact_key text not null,
    parent_id uuid references categories (id),
    check (parent_id is null or parent_id <> id)
);
create unique index categories_unique_per_parent
    on categories (exact_key, coalesce(parent_id, '00000000-0000-0000-0000-000000000000'::uuid));
create table version_categories (
    version_id  uuid not null references book_versions (id),
    category_id uuid not null references categories (id),
    primary key (version_id, category_id)
);

-- An operator override wins over the source value until the operator decides (INV-CAT-006).
create table field_overrides (
    book_id           uuid        not null references books (id),
    field             text        not null,
    value             jsonb       not null,
    set_by            uuid        not null,
    set_at            timestamptz not null,
    source_value_hash text        not null,
    stale             boolean     not null default false,
    primary key (book_id, field)
);

create table metadata_revisions (
    id          uuid primary key,
    book_id     uuid        not null references books (id),
    version_id  uuid        not null references book_versions (id),
    revision_no integer     not null check (revision_no > 0),
    source      text        not null check (source in ('ingestion', 'operator')),
    changed_by  text        not null,
    changed_at  timestamptz not null,
    changes     jsonb       not null,
    snapshot    jsonb       not null,
    unique (book_id, revision_no)
);

create table agent_merges (
    from_agent    uuid        not null references agents (id),
    into_agent    uuid        not null references agents (id),
    moved_credits jsonb       not null,
    at            timestamptz not null,
    by            uuid        not null,
    primary key (from_agent, at),
    check (from_agent <> into_agent)
);

-- Write-once files (INV-CAT-020, 021): the row is the only way a blob is reachable.
create table assets (
    id           uuid primary key,
    version_id   uuid        not null references book_versions (id),
    kind         text        not null check (kind in ('epub', 'cover', 'preview')),
    sha256       text        not null check (sha256 ~ '^[0-9a-f]{64}$'),
    size_bytes   bigint      not null check (size_bytes > 0),
    media_type   text        not null,
    storage_path text        not null,
    created_at   timestamptz not null,
    unique (version_id, kind),
    check (kind <> 'epub' or media_type = 'application/epub+zip')
);

-- why: the purge job runs as the service role too; it sets this flag in its own transaction.
create function assets_write_once() returns trigger language plpgsql as $$
begin
    if current_setting('catalog.purge', true) = 'on' and tg_op = 'DELETE' then
        return old;
    end if;
    raise exception 'assets are write-once';
end;
$$;
create trigger assets_immutable before update or delete on assets
    for each row execute function assets_write_once();

-- A published version needs a verified epub and one credit by a qualifying role (INV-CAT-004).
create function published_version_complete() returns trigger language plpgsql as $$
begin
    if new.state <> 'published' then
        return new;
    end if;
    if not exists (select 1 from assets where version_id = new.id and kind = 'epub') then
        raise exception 'a published version needs an epub asset';
    end if;
    if not exists (select 1 from credits where version_id = new.id
                   and role in ('writer', 'translator', 'editor', 'compiler')) then
        raise exception 'a published version needs a writer, translator, editor or compiler credit';
    end if;
    return new;
end;
$$;
create constraint trigger book_versions_published_check after insert or update of state on book_versions
    deferrable initially deferred for each row execute function published_version_complete();

create table audit_log (
    id      bigserial primary key,
    at      timestamptz not null,
    actor   text        not null,
    action  text        not null,
    target  text,
    details jsonb       not null default '{}'::jsonb
);
create index audit_log_by_time on audit_log (at);

-- Insert-only (D-40): only rows older than the one-year retention may be deleted.
create function audit_log_guard() returns trigger language plpgsql as $$
begin
    if tg_op = 'DELETE' and old.at < now() - interval '1 year' then
        return old;
    end if;
    raise exception 'audit_log is insert-only';
end;
$$;
create trigger audit_log_immutable before update or delete on audit_log
    for each row execute function audit_log_guard();

-- Append-only history.
create function metadata_revisions_guard() returns trigger language plpgsql as $$
begin
    raise exception 'metadata_revisions is append-only';
end;
$$;
create trigger metadata_revisions_immutable before update or delete on metadata_revisions
    for each row execute function metadata_revisions_guard();

create table events (
    cursor     bigserial primary key,
    id         uuid        not null unique,
    type       text        not null,
    v          integer     not null check (v > 0),
    subject_id uuid,
    request_id text,
    payload    jsonb       not null,
    at         timestamptz not null
);

create table event_cursors (
    source      text primary key,
    last_cursor bigint not null check (last_cursor >= 0)
);
