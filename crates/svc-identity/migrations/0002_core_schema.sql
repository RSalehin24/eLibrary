-- Identity core schema (planning/05-services/identity/domain-model.md). Keys are UUIDv7 made by the
-- service; times are timestamptz UTC from the injected clock; closed sets are CHECK constraints.

create table users (
    id            uuid primary key,
    email         text        not null check (char_length(email) <= 254),
    display_name  text        not null,
    language      text        not null check (language in ('bn', 'en')),
    status        text        not null check (status in ('invited', 'active', 'suspended', 'disabled')),
    role          text        not null check (role in ('reader', 'operator', 'admin')),
    totp_required boolean     not null default false,
    grant_version bigint      not null default 0 check (grant_version >= 0),
    revision      bigint      not null default 0 check (revision >= 0),
    created_at    timestamptz not null,
    updated_at    timestamptz not null
);
create unique index users_email_unique on users (lower(email));

create table kindle_addresses (
    user_id  uuid not null references users (id) on delete cascade,
    position smallint not null check (position >= 0 and position < 5),
    address  text not null,
    primary key (user_id, position)
);

create table credentials (
    user_id       uuid primary key references users (id) on delete cascade,
    password_hash text        not null check (password_hash like '$argon2id$%'),
    changed_at    timestamptz not null
);

create table totp (
    user_id            uuid primary key references users (id) on delete cascade,
    secret_enc         bytea       not null,
    state              text        not null check (state in ('pending', 'enabled')),
    confirmed_at       timestamptz,
    last_accepted_step bigint      check (last_accepted_step >= 0),
    failed_count       integer     not null default 0 check (failed_count >= 0),
    check ((state = 'enabled') = (confirmed_at is not null))
);

create table sessions (
    id           uuid primary key,
    token_hash   bytea       not null unique,
    user_id      uuid        not null references users (id) on delete cascade,
    state        text        not null check (state in ('pending_totp', 'authenticated')),
    csrf_hash    bytea       not null,
    created_at   timestamptz not null,
    last_seen_at timestamptz not null,
    expires_at   timestamptz not null,
    revoked_at   timestamptz,
    ua_hash      bytea,
    ip_prefix    text,
    check (expires_at > created_at)
);
create index sessions_live_by_user on sessions (user_id) where revoked_at is null;

create table links (
    id         uuid primary key,
    user_id    uuid        not null references users (id) on delete cascade,
    purpose    text        not null check (purpose in ('invite', 'reset')),
    token_hash bytea       not null unique,
    nonce      bytea       not null,
    state      text        not null check (state in ('issued', 'consumed', 'superseded', 'expired')),
    expires_at timestamptz not null,
    request_id text        not null,
    created_at timestamptz not null,
    check (expires_at > created_at)
);
create unique index links_one_issued_per_purpose on links (user_id, purpose) where state = 'issued';

create table grants (
    id         uuid primary key,
    user_id    uuid        not null references users (id) on delete cascade,
    scope      text        not null check (scope in
        ('browse', 'preview', 'read', 'read_once', 'download', 'kindle', 'operate', 'manage_catalog', 'manage_users')),
    book_id    uuid,
    expires_at timestamptz,
    active     boolean     not null default true,
    granted_by uuid        not null,
    reason     text        not null,
    revision   bigint      not null default 0 check (revision >= 0),
    created_at timestamptz not null,
    check (granted_by <> user_id),
    check (book_id is null or scope in ('preview', 'read', 'read_once', 'download', 'kindle'))
);
create unique index grants_one_active_per_target
    on grants (user_id, scope, coalesce(book_id, '00000000-0000-0000-0000-000000000000'::uuid))
    where active;

create table read_once_uses (
    user_id     uuid        not null references users (id) on delete cascade,
    book_id     uuid        not null,
    ticket_id   uuid        not null,
    consumed_at timestamptz not null,
    primary key (user_id, book_id)
);

create table tickets (
    id            uuid primary key,
    secret_hash   bytea       not null unique,
    user_id       uuid        not null references users (id) on delete cascade,
    book_id       uuid        not null,
    version_id    uuid        not null,
    grant_version bigint      not null,
    issued_at     timestamptz not null,
    expires_at    timestamptz not null,
    redeemed_at   timestamptz,
    check (expires_at > issued_at and expires_at <= issued_at + interval '15 minutes')
);

create table profile_images (
    user_id      uuid primary key references users (id) on delete cascade,
    content_type text        not null check (content_type in ('image/png', 'image/jpeg', 'image/webp')),
    bytes        bytea       not null,
    size         integer     not null check (size = octet_length(bytes) and size > 0),
    sha256       bytea       not null check (octet_length(sha256) = 32),
    updated_at   timestamptz not null
);

create table login_attempts (
    key          text        not null,
    window_start timestamptz not null,
    count        integer     not null check (count >= 0),
    primary key (key, window_start)
);

create table audit_log (
    id         bigserial primary key,
    at         timestamptz not null,
    actor      text        not null,
    subject    text,
    action     text        not null,
    detail     jsonb       not null default '{}'::jsonb,
    request_id text,
    address    text,
    ua_hash    bytea
);
create index audit_log_by_time on audit_log (at);
create index audit_log_by_subject on audit_log (subject, at);

-- Insert-only (D-40): rows are never updated; only rows older than the one-year retention may be deleted.
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

create table email_requests (
    request_id text primary key,
    kind       text        not null check (kind in ('invite', 'password_reset')),
    user_id    uuid        not null references users (id) on delete cascade,
    language   text        not null check (language in ('bn', 'en')),
    link_ref   text        not null,
    created_at timestamptz not null
);

create table config_defaults (
    key   text primary key,
    value text not null
);
