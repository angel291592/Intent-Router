import Redis from "ioredis";

// Single shared Redis client. Every cache entry in this service goes through
// here; in-process caching is deliberately not used, see
// docs/adr/0007-no-inproc-cache.md.
export const redis = new Redis({
  host: process.env.REDIS_HOST ?? "127.0.0.1",
  port: Number(process.env.REDIS_PORT ?? 6379),
  lazyConnect: true,
});

export const DEFAULT_TTL_SECONDS = 300; // repo convention: every cache entry expires in 5 minutes

export async function getCache<T>(key: string): Promise<T | null> {
  const raw = await redis.get(key);
  return raw === null ? null : (JSON.parse(raw) as T);
}

export async function setCache(
  key: string,
  value: unknown,
  ttlSeconds: number = DEFAULT_TTL_SECONDS,
): Promise<void> {
  await redis.set(key, JSON.stringify(value), "EX", ttlSeconds);
}

export async function dropCache(key: string): Promise<void> {
  await redis.del(key);
}
