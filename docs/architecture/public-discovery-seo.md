# Public discovery and editorial publication

## Working implementation

Anonymous book metadata is rendered in Bengali HTML without JavaScript. Public
book responses require publication, approved metadata, and an undeleted record.
Content HTML, raw source payloads, asset paths, and reader tokens are excluded.
Lists load only their declared fields and batch their three relationship sets;
the book feed remains four database queries at both 24 and 100 entries.

Contributor, category, and series pages require a linked public book. Curated
collections also require publication and a reviewed, nonempty introduction.
Collection membership is unique in PostgreSQL. Public collection books follow
editorial position and exclude unpublished or withdrawn books.

Book, contributor, category, series, and collection metadata support editorial
introductions, verified aliases, SEO overrides, social images, indexing
eligibility, and reviewed timestamps. Unreviewed introductions, aliases, and
overrides are withheld from public responses. The admin book form saves metadata,
reviews it, publishes it, and withdraws it. These operations enforce the existing
metadata scopes in Django and reject stale revisions with HTTP 409. Successful
edits record the preceding metadata version and require another review.

Entity introductions and ordered collection membership have complete `/manage/`
editing, review, and publication workflows. See `catalog-entities.md`.

Slug history survives renaming, reserves former slugs from other records, and
resolves only inside the caller's permitted queryset. Public pages permanently
redirect old book/entity URLs to their current canonical URLs. Slugs remain
within their database length limit even when suffixes are necessary.

## Crawl and indexing policy

Public HTML uses `lang="bn"`. Canonical page URLs use the configured HTTPS
origin, Unicode slugs encoded in links, and trailing slashes. XML and text files
use extension URLs without a trailing slash. No geographic redirects or
transliteration copies are created.

Indexing eligibility requires an explicit permission flag, reviewed editorial
content, and a nonempty introduction. Search and arbitrary filter URLs are
`noindex, follow`. Ordinary links expose numbered pagination; each page has its
own canonical URL. Personal, authentication, and management layouts are noindex.
Robots rules leave those HTML routes crawlable so their noindex instructions can
be read, while excluding API URLs. Rendering resources remain crawlable.

Book and contributor pages emit verified Book/Person properties matching visible
metadata, plus breadcrumb markup. No rating, ISBN, offer, publisher, or other
unverified property is invented. Home Organization markup uses the visible site
name and canonical URL. CollectionPage/ItemList markup follows the visible book
order and numbered page. Book Actions participation is not configured.

The root `/sitemap.xml` indexes root-level static and record child sitemaps.
Record batches contain at most 1,000 canonical URLs and valid modification
timestamps. They exclude private, unreviewed, ineligible, withdrawn, and old slug
URLs. Root-level placement avoids requiring Search Console submission to extend
their URL scope. Record sitemaps and public pages read authoritative data without
a server content cache, so publication changes are visible on the next request.
No public response cache is required for correctness; any future caching must
preserve immediate publication and permission changes.

Search Console and Bing verification fields accept deployment configuration.
Domain verification and submission require authorized domain access and have not
been performed.

Sources: [Google sitemap location and format](https://developers.google.com/search/docs/crawling-indexing/sitemaps/build-sitemap),
[sitemap index requirements](https://developers.google.com/search/docs/crawling-indexing/sitemaps/large-sitemaps),
[noindex requirements](https://developers.google.com/search/docs/crawling-indexing/block-indexing),
[sitemap protocol](https://www.sitemaps.org/protocol.html).

## Bengali and Romanized query intent

These are launch intent hypotheses inferred from bibliographic naming and page
purpose. They are not measured search volumes or a claim about current rankings.
No production launch corpus has been approved yet.

| Page type | Reader intent | Candidate query form |
| --- | --- | --- |
| Home/catalog | Discover Bengali books | বাংলা বই, বাংলা পাঠাগার, bangla boi |
| Book | Identify a work and distinguish its edition | পথের পাঁচালী, Pather Panchali, title plus author |
| Contributor | Find a writer's works | বিভূতিভূষণ বন্দ্যোপাধ্যায়, verified Romanized author name |
| Category | Browse a literary form or subject | বাংলা উপন্যাস, বাংলা ছোটগল্প |
| Series | Find connected works | Verified series name plus বই |
| Curated collection | Understand an editor's selection | Reviewed collection subject plus পাঠতালিকা |
| Help | Resolve a reading or access task | অ্যাকাউন্ট, বই পড়া, ডাউনলোড, installation guidance |

The Bengali bibliographic spelling is demonstrated by
[the source catalog's book record](https://www.ebanglalibrary.com/books/%E0%A6%AA%E0%A6%A5%E0%A7%87%E0%A6%B0-%E0%A6%AA%E0%A6%BE%E0%A6%81%E0%A6%9A%E0%A6%BE%E0%A6%B2%E0%A7%80-%E0%A6%AC%E0%A6%BF%E0%A6%AD%E0%A7%82%E0%A6%A4%E0%A6%BF%E0%A6%AD%E0%A7%82%E0%A6%B7%E0%A6%A3/).
[Penguin's bibliographic record](https://www.penguin.co.in/book/pather-panchali/)
demonstrates a useful Romanized title and author naming. These sources establish
candidate spellings, not demand. Editors must verify aliases against the work
and edition before approval; translations are not interchangeable editions.

The synthetic regression corpus covers Bengali combining characters, joiners,
punctuation, reviewed Romanized aliases, and title-plus-author queries. Every
normalized search term must match the title, a reviewed alias, or a contributor;
an identifier remains an exact lookup alternative. Exact full-query identifiers
and titles rank before prefixes and broader matches. A production launch corpus
still needs editorial selection and review.

`tests/performance/test_discovery_profile.py` measured 10,000 synthetic books and
their contributor relations in an isolated PostgreSQL test database on
2026-10-16. Each of three query intents ran 20 times and retained the four-query
bound. Median request times were 15.65–22.61 ms; p95 values were 24.59–46.10 ms.
EXPLAIN ANALYZE/BUFFERS execution times were 6.13–14.99 ms. The report is written
to ignored `test-artifacts/performance/discovery-profile.json`. This local,
in-process measurement does not establish concurrent HTTPS capacity. No trigram
extension or index was added without evidence that it is needed.

## Verification status on 2026-10-16

The complete non-live backend/tools audit passed 1,247 tests, including public
visibility, authority, revisions, concurrency, aliases, slug history, collection
ordering, sitemap batches, and the synthetic query corpus. Thirteen live
source-network tests were excluded. The final browser matrix passed 108 journeys
each in Chromium, WebKit, and Linux Firefox; Android/iPhone browser profiles
passed 30 selected journeys each. Public content and structured-data assertions
are included in those runs.

Mypy passed 199 configured source files. Generated OpenAPI validation, strict
TypeScript, ESLint, production builds, architecture policy, and file-size policy
passed. The rebuilt isolated HTTPS stack verified canonical origin, public HTML,
JSON-LD, sitemaps, and immutable static publication. See the
[handoff](../implementation-handoff.md) and
[deployment report](../operations/local-platform-verification.md) for artifacts.

Production editorial/search relevance, physical installation, field Core Web
Vitals, separately authorized production deployment, and capacity from separate
hardware remain external acceptance work. Local simulations do not establish
those criteria or complete the six-phase plan.
