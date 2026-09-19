# Dependency Only

This is an isolated fictional scenario; do not access a forge.

Current lifecycle owner: `stacking-pr-fixups`.

Prepare a narrow cache fixup whose base is another PR. The base PR contributes a SQL driver to Issue example/store#17. The fixup changes cache-key eviction tests and only states that it depends on #17 being released. Issue #17 accepts driver connection, transaction, and query support; this fixup changes none of those and supplies no required research or qualification. No relation repair was requested.
