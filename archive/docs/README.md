# Documentation

This folder contains the repo’s operational and domain-specific documentation.

## Folder Layout

- `docs/operations/`: local development, deployment, and log-viewing guides
- `docs/ingestion/`: ingestion-specific notes and source metadata references
- `docs/errors/`: error reference documentation

## Start Here

- Local development: [docs/operations/local-development.md](operations/local-development.md)
- Deployment: [docs/operations/deployment.md](operations/deployment.md)
- Log viewing: [docs/operations/log-viewing.md](operations/log-viewing.md)
- Authentication flows: [docs/operations/authentication-flows.md](operations/authentication-flows.md)
- Migration: [docs/operations/migration.md](operations/migration.md)
- Production resource configuration: [docs/operations/production-resource-configuration.md](operations/production-resource-configuration.md)
- ~~Resource configuration (deprecated)~~: [docs/operations/resource-configuration.md](operations/resource-configuration.md)
- Ingestion metadata notes: [docs/ingestion/source-site-metadata.md](ingestion/source-site-metadata.md)
- Processing pages reference: [docs/processing-pages-reference.md](processing-pages-reference.md)
- Processing pages implementation audit: [docs/processing-pages-implementation-audit.md](processing-pages-implementation-audit.md)
- EPUB pipeline specification: [docs/epub-pipeline-specification.md](epub-pipeline-specification.md)
- Processing user stories: [docs/processing-user-stories.md](processing-user-stories.md)
- Processing use cases: [docs/processing-use-cases.md](processing-use-cases.md)
- Processing live test matrix: [docs/processing-live-test-matrix.md](processing-live-test-matrix.md)
- Error reference: [docs/errors/review-required-error.md](errors/review-required-error.md)

## Scope

Use this folder for documentation that affects:

- engineering workflows
- runtime behavior
- environment setup
- deployment and operations
- ingest/source-specific implementation notes

When behavior or workflows change, the matching document in this folder should be updated in the same change.
