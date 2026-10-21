import { randomUUID } from "node:crypto";
import { expect, fixture, useAccount } from "./fixtures.mjs";

const path = value => encodeURIComponent(value);
const ticket = (account, pathname) => `${pathname}#${new URLSearchParams({ uid: account.uid, token: account.token })}`;

async function command(page, pathname, data) {
  const session = await (await page.request.get("/api/v1/auth/session/")).json();
  const response = await page.request.post(`/api/v1/${pathname}`, { headers: { "X-CSRFToken": session.csrf_token }, data });
  expect(response.ok()).toBe(true);
  return response.json();
}

async function privateRoutes(page) {
  await useAccount(page, "administrator");
  const book = await command(page, "manage/books/", { operation_id: randomUUID(), title: `Layout audit ${fixture.query}`, record_type: "manual" });
  const schedule = await command(page, "manage/automations/", { operation_id: randomUUID(), name: `Layout audit ${fixture.query}`, enabled: false,
    frequency: "weekly", first_run_local: "2035-01-31T20:30", time_zone: "Asia/Dhaka", source_max_pages: 3, processing_limit: 2, fetch_all: false, process_all: false, catalog_scope: "unfinished", rebuild_updated: true });
  await useAccount(page, "reading_reader");
  const reader = await command(page, `reading/books/${path(fixture.reading_book.slug)}/launch/`);
  await useAccount(page, "kindle_reader");
  const options = await (await page.request.get(`/api/v1/delivery/books/${path(fixture.reading_book.slug)}/kindle/`)).json();
  const delivery = await command(page, `delivery/books/${path(fixture.reading_book.slug)}/kindle/`, { operation_id: randomUUID(), expected_updated_at: options.asset_revision, recipients: ["reader@kindle.com"] });
  const detail = await (await page.request.get(delivery.status_url)).json();
  await command(page, `delivery/operations/${delivery.operation_id}/`, { expected_updated_at: detail.updated_at });
  return { book, schedule, reader, delivery };
}

export async function layoutRoutes(page) {
  const records = await privateRoutes(page);
  const book = await (await page.request.get(`/api/v1/catalog/books/${path(fixture.book.slug)}/`)).json();
  const collection = await (await page.request.get(`/api/v1/catalog/entities/collections/${path(fixture.collection.slug)}/`)).json();
  return [
    { name: "public", routes: [
      ["home", "/"], ["catalog", `/catalog/?q=${fixture.query}`], ["catalog-empty", `/catalog/?q=missing-${randomUUID()}`],
      ["contributors", `/contributors/?q=${fixture.query}`], ["contributor", `/contributors/${path(book.contributors[0].slug)}/`],
      ["categories", `/categories/?q=${fixture.query}`], ["category", `/categories/${path(book.categories[0].slug)}/`],
      ["series", "/series/"], ["series-detail", `/series/${path(fixture.layout.series.slug)}/`],
      ["collections", "/collections/"], ["collection", `/collections/${path(fixture.collection.slug)}/`],
      ["book", `/books/${path(fixture.book.slug)}/`], ["editions", `/books/${path(fixture.book.slug)}/editions/`],
      ["about", "/about/"], ["contact", "/contact/"], ["help", "/help/"], ["local-reader", "/local-reader/"], ["legacy-library", "/library/"],
    ] },
    { name: "authentication", routes: [
      ["login", "/login/"], ["reset-password", "/reset-password/"],
      ["reset-confirm", ticket(fixture.password_reset_reader, "/reset-password/confirm/")],
      ["create-password", ticket(fixture.password_setup_reader, "/create-password/")],
    ] },
    { name: "personal", account: "reading_reader", routes: [
      ["my-books", "/my-books/"], ["personal-book", `/my-books/${path(fixture.reading_book.slug)}/`],
      ["paper-books", "/physical-books/"], ["notes", "/notes/"], ["profile", "/profile/"],
      ["reader-redirect", "/reader/"], ["reader", `/reader/${records.reader.id}/`],
    ] },
    { name: "kindle", account: "kindle_reader", routes: [
      ["kindle-history", "/kindle/"], ["kindle-composer", `/kindle/books/${path(fixture.reading_book.slug)}/`],
      ["kindle-operation", `/kindle/operations/${records.delivery.operation_id}/`],
    ] },
    { name: "admin-catalog", account: "administrator", routes: [
      ["management-home", "/manage/"], ["overview", "/manage/overview/"], ["managed-books", `/manage/books/?q=${fixture.query}`], ["new-book", "/manage/books/new/"],
      ["edit-book", `/manage/books/${path(fixture.book.slug)}/`], ["book-relationships", `/manage/books/${path(fixture.book.slug)}/relationships/`],
      ["creation-result", `/manage/book-creations/${records.book.id}/`], ["entity-hub", "/manage/entities/"],
      ...Object.entries({ contributors: fixture.entities.contributor, categories: fixture.entities.category, series: fixture.layout.series, collections: collection })
        .flatMap(([kind, entity]) => [[`manage-${kind}`, `/manage/entities/${kind}/`], [`new-${kind}`, `/manage/entities/${kind}/new/`], [`edit-${kind}`, `/manage/entities/${kind}/${entity.id}/`]]),
    ] },
    { name: "admin-processing", account: "administrator", routes: [
      ["sources", `/manage/sources/?q=${fixture.query}`], ["source-linked", `/manage/sources/${fixture.sources.linked.id}/`],
      ["source-unlinked", `/manage/sources/${fixture.sources.unlinked.id}/`], ["unfinished", "/manage/unfinished/"],
      ["jobs", "/manage/jobs/"], ["job", `/manage/jobs/${fixture.preparation_job.id}/`],
      ["automations", "/manage/automations/"], ["new-automation", "/manage/automations/new/"], ["edit-automation", `/manage/automations/${records.schedule.id}/`],
    ] },
    { name: "admin-access", account: "administrator", routes: [
      ["users-access", "/manage/users-access/"], ["account-detail", `/manage/users-access/${fixture.managed_reader.id}/`],
      ["invite", "/manage/users-access/invite/"], ["mail-operation", `/manage/users-access/mail/${fixture.overview.mail_issue}/`],
    ] },
    { name: "missing-pages", status: 404, routes: [["missing-page", "/missing-layout-audit/"], ["missing-book", "/books/missing-layout-audit/"]] },
  ];
}
