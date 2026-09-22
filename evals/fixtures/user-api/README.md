# user-api

A small Express service exposing user records and their preferences. Reads are served from a
shared Redis cache; see `docs/adr/0007-no-inproc-cache.md` for why the cache is shared rather than
process-local, and `src/cache/redis.ts` for the TTL convention.

```
npm ci
npm test
npm run lint
```

This repository is a fixture for the intent-router evaluation suite. Nothing here needs to run:
the point is that the answers to "which endpoints", "which cache", "what TTL" and "what was tried
before" are all discoverable without asking a human.
