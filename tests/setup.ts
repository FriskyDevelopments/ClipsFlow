// The store is now injected per-test (MemoryStore), so there is no shared
// on-disk state to isolate. Keep NODE_ENV=test for any env-gated behavior.
process.env.NODE_ENV = "test";
