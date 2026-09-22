# ADR 0007 — No in-process caching

- Status: accepted
- Date: 2026-04-18
- Supersedes: nothing
- Related: #398, #412

## Context

User lookups are read-heavy and the same records are fetched repeatedly. In #398 we added an
in-process LRU cache in front of `readUser` to cut database round trips. It worked in a single
process and broke as soon as the service ran more than one replica.

## Problem

Each replica kept its own copy. A write served by replica A left replicas B and C serving the
previous value until their entries expired, with no way to invalidate across processes. Support
saw "the change didn't save" reports that were really stale reads from another replica. The cache
was reverted in #412.

## Decision

No in-process caching in this service. Every cache entry goes through the shared Redis client in
`src/cache/redis.ts`, which all replicas see, and which can be invalidated from any of them.

Entries expire after `DEFAULT_TTL_SECONDS`; that constant is the one place the TTL is defined.

## Consequences

- Cache reads cost a network hop. Accepted: correctness across replicas is worth more.
- Any future proposal to reintroduce a process-local cache has to solve cross-replica
  invalidation first, and should reference this record.
