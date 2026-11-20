-- Notify's own data: event cursors, the mail outbox and the delivery log. No address, link or
-- token is ever stored (mail content is fetched from identity by reference right before sending).

create table cursors (
    source     text primary key check (source in ('identity', 'catalog')),
    cursor     bigint      not null check (cursor >= 0),
    updated_at timestamptz not null
);

create table outbox (
    id              uuid primary key,
    source          text        not null check (source in ('identity', 'catalog')),
    event_id        uuid        not null,
    kind            text        not null check (kind in ('invite', 'password_reset', 'password_changed')),
    request_id      text        not null,
    user_id         uuid        not null,
    language        text        not null check (language in ('bn', 'en')),
    state           text        not null check (state in ('queued', 'sending', 'sent', 'failed')),
    attempts        integer     not null default 0 check (attempts >= 0),
    next_attempt_at timestamptz not null,
    lease_until     timestamptz,
    error_class     text        check (error_class in ('retryable', 'permanent')),
    created_at      timestamptz not null,
    updated_at      timestamptz not null,
    unique (source, event_id, kind)
);
create index outbox_due on outbox (next_attempt_at) where state in ('queued', 'sending');

create table delivery_log (
    id             bigserial primary key,
    outbox_id      uuid        not null references outbox (id) on delete cascade,
    attempt        integer     not null check (attempt > 0),
    status         text        not null check (status in ('sent', 'retry', 'failed')),
    error_class    text        check (error_class in ('retryable', 'permanent')),
    masked_address text,
    at             timestamptz not null
);
create index delivery_log_by_outbox on delivery_log (outbox_id, attempt);
