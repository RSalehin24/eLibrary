# Catalog numbers for books without metadata

Catalog numbers remain ten characters long. Previously, every newly created book
was assigned to the unknown author/category pair, whose original encoding held
only 4,095 book sequences. A large library could therefore stop accepting books
before their metadata was attached.

Allocation now uses a reserved book-payload tag after that unassigned pair is
full. The extension keeps the existing alphabet, scrambling and checksum checks;
it has a 44-bit sequence for books with no encoded author/category identity.
Existing numbers, URLs and records are unchanged, and no data migration is needed.
The decoder continues to report author/category sequence zero for these numbers.
Normal metadata relationship lookup remains authoritative.

Existing nonzero author/category encodings retain their bounds and behavior.
Allocation still holds the existing database advisory transaction lock, and the
database uniqueness constraint remains enabled. Full encodings fail explicitly;
the application does not silently omit a catalog number or delete earlier records.
