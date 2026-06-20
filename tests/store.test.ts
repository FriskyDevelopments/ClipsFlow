import { describe, it, expect, beforeEach } from "vitest";
import fs from "fs";
import path from "path";
import * as store from "../src/store.js";
import { Clip } from "../src/types.js";

const DATA_FILE = path.join(process.env.CLIPS_DATA_DIR as string, "clips.json");

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

beforeEach(() => {
  if (fs.existsSync(DATA_FILE)) fs.rmSync(DATA_FILE);
});

describe("store.getAll — pagination", () => {
  it("defaults to page 1 with the default limit", () => {
    for (let i = 0; i < 25; i++) store.insert(makeClip(String(i)));
    const result = store.getAll();
    expect(result.total).toBe(25);
    expect(result.page).toBe(1);
    expect(result.limit).toBe(store.DEFAULT_PAGE_LIMIT);
    expect(result.data).toHaveLength(store.DEFAULT_PAGE_LIMIT);
  });

  it("returns the requested page slice", () => {
    for (let i = 0; i < 25; i++) store.insert(makeClip(String(i)));
    const result = store.getAll({ page: 2, limit: 10 });
    expect(result.page).toBe(2);
    expect(result.limit).toBe(10);
    expect(result.data).toHaveLength(10);
    expect(result.data[0].id).toBe("10");
  });

  it("returns a short final page", () => {
    for (let i = 0; i < 25; i++) store.insert(makeClip(String(i)));
    const result = store.getAll({ page: 3, limit: 10 });
    expect(result.data).toHaveLength(5);
  });

  it("caps limit at MAX_PAGE_LIMIT", () => {
    const result = store.getAll({ limit: 9999 });
    expect(result.limit).toBe(store.MAX_PAGE_LIMIT);
  });

  it("normalizes invalid page/limit to safe defaults", () => {
    store.insert(makeClip("a"));
    const result = store.getAll({ page: -3, limit: 0 });
    expect(result.page).toBe(1);
    expect(result.limit).toBe(store.DEFAULT_PAGE_LIMIT);
  });
});

describe("store.getAll — tag filtering", () => {
  beforeEach(() => {
    store.insert(makeClip("1", ["intro", "promo"]));
    store.insert(makeClip("2", ["intro"]));
    store.insert(makeClip("3", ["outro"]));
  });

  it("returns only clips containing the requested tag", () => {
    const result = store.getAll({ tag: "intro" });
    expect(result.total).toBe(2);
    expect(result.data.map((c) => c.id).sort()).toEqual(["1", "2"]);
  });

  it("returns an empty set for an unknown tag", () => {
    const result = store.getAll({ tag: "nope" });
    expect(result.total).toBe(0);
    expect(result.data).toHaveLength(0);
  });

  it("ignores an empty tag and returns everything", () => {
    const result = store.getAll({ tag: "" });
    expect(result.total).toBe(3);
  });

  it("paginates the filtered set, not the whole store", () => {
    const result = store.getAll({ tag: "intro", limit: 1 });
    expect(result.total).toBe(2);
    expect(result.data).toHaveLength(1);
  });
});
