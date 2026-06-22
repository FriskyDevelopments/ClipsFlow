import { describe, it, expect, beforeEach } from "vitest";
import { MemoryStore, DEFAULT_PAGE_LIMIT, MAX_PAGE_LIMIT } from "../src/store.js";
import { Clip } from "../src/types.js";

function makeClip(id: string, tags: string[] = []): Clip {
  const now = new Date().toISOString();
  return {
    id,
    title: `clip-${id}`,
    filePath: `/clips/${id}.mp4`,
    durationSeconds: 60,
    tags,
    createdAt: now,
    updatedAt: now,
  };
}

let store: MemoryStore;

beforeEach(() => {
  store = new MemoryStore();
});

describe("MemoryStore.getAll — pagination", () => {
  it("defaults to page 1 with the default limit", async () => {
    for (let i = 0; i < 25; i++) await store.insert(makeClip(String(i)));
    const result = await store.getAll();
    expect(result.total).toBe(25);
    expect(result.page).toBe(1);
    expect(result.limit).toBe(DEFAULT_PAGE_LIMIT);
    expect(result.data).toHaveLength(DEFAULT_PAGE_LIMIT);
  });

  it("returns the requested page slice", async () => {
    for (let i = 0; i < 25; i++) await store.insert(makeClip(String(i)));
    const result = await store.getAll({ page: 2, limit: 10 });
    expect(result.page).toBe(2);
    expect(result.limit).toBe(10);
    expect(result.data).toHaveLength(10);
    expect(result.data[0].id).toBe("10");
  });

  it("returns a short final page", async () => {
    for (let i = 0; i < 25; i++) await store.insert(makeClip(String(i)));
    const result = await store.getAll({ page: 3, limit: 10 });
    expect(result.data).toHaveLength(5);
  });

  it("caps limit at MAX_PAGE_LIMIT", async () => {
    const result = await store.getAll({ limit: 9999 });
    expect(result.limit).toBe(MAX_PAGE_LIMIT);
  });

  it("normalizes invalid page/limit to safe defaults", async () => {
    await store.insert(makeClip("a"));
    const result = await store.getAll({ page: -3, limit: 0 });
    expect(result.page).toBe(1);
    expect(result.limit).toBe(DEFAULT_PAGE_LIMIT);
  });
});

describe("MemoryStore.getAll — tag filtering", () => {
  beforeEach(async () => {
    await store.insert(makeClip("1", ["intro", "promo"]));
    await store.insert(makeClip("2", ["intro"]));
    await store.insert(makeClip("3", ["outro"]));
  });

  it("returns only clips containing the requested tag", async () => {
    const result = await store.getAll({ tag: "intro" });
    expect(result.total).toBe(2);
    expect(result.data.map((c) => c.id).sort()).toEqual(["1", "2"]);
  });

  it("returns an empty set for an unknown tag", async () => {
    const result = await store.getAll({ tag: "nope" });
    expect(result.total).toBe(0);
    expect(result.data).toHaveLength(0);
  });

  it("ignores an empty tag and returns everything", async () => {
    const result = await store.getAll({ tag: "" });
    expect(result.total).toBe(3);
  });

  it("paginates the filtered set, not the whole store", async () => {
    const result = await store.getAll({ tag: "intro", limit: 1 });
    expect(result.total).toBe(2);
    expect(result.data).toHaveLength(1);
  });
});
