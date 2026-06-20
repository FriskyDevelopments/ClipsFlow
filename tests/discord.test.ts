import { describe, it, expect, beforeEach } from "vitest";
import fs from "fs";
import path from "path";
import { runClipCommand, parseTags } from "../src/discord/commands.js";

const DATA_FILE = path.join(process.env.CLIPS_DATA_DIR as string, "clips.json");

beforeEach(() => {
  if (fs.existsSync(DATA_FILE)) fs.rmSync(DATA_FILE);
});

describe("parseTags", () => {
  it("returns undefined for null/undefined", () => {
    expect(parseTags(null)).toBeUndefined();
    expect(parseTags(undefined)).toBeUndefined();
  });

  it("splits, trims, and drops empties", () => {
    expect(parseTags(" intro , , promo ")).toEqual(["intro", "promo"]);
  });

  it("returns an empty array for a blank string", () => {
    expect(parseTags("   ")).toEqual([]);
  });
});

describe("runClipCommand", () => {
  it("add → creates a clip", () => {
    const res = runClipCommand({
      subcommand: "add",
      title: "Intro",
      filePath: "/clips/intro.mp4",
      durationSeconds: 120,
      tags: ["intro"],
    });
    expect(res.ok).toBe(true);
    expect(res.clip?.id).toBeTruthy();
    expect(res.clip?.tags).toEqual(["intro"]);
  });

  it("add → surfaces validation errors", () => {
    const res = runClipCommand({ subcommand: "add", title: "", filePath: "", durationSeconds: 0 });
    expect(res.ok).toBe(false);
    expect(res.message).toContain("Validation failed");
  });

  it("list → returns a paginated envelope", () => {
    runClipCommand({ subcommand: "add", title: "A", filePath: "/a.mp4", durationSeconds: 10, tags: ["x"] });
    runClipCommand({ subcommand: "add", title: "B", filePath: "/b.mp4", durationSeconds: 10, tags: ["y"] });
    const all = runClipCommand({ subcommand: "list" });
    expect(all.ok).toBe(true);
    expect(all.clips?.total).toBe(2);

    const filtered = runClipCommand({ subcommand: "list", tag: "x" });
    expect(filtered.clips?.total).toBe(1);
    expect(filtered.clips?.data[0].title).toBe("A");
  });

  it("get → found and not-found", () => {
    const created = runClipCommand({
      subcommand: "add",
      title: "Solo",
      filePath: "/s.mp4",
      durationSeconds: 5,
    });
    const id = created.clip!.id;

    const got = runClipCommand({ subcommand: "get", id });
    expect(got.ok).toBe(true);
    expect(got.clip?.id).toBe(id);

    const missing = runClipCommand({ subcommand: "get", id: "nope" });
    expect(missing.ok).toBe(false);
    expect(missing.message).toContain("not found");
  });

  it("update → changes title", () => {
    const created = runClipCommand({
      subcommand: "add",
      title: "Old",
      filePath: "/o.mp4",
      durationSeconds: 5,
    });
    const res = runClipCommand({ subcommand: "update", id: created.clip!.id, title: "New" });
    expect(res.ok).toBe(true);
    expect(res.clip?.title).toBe("New");
  });

  it("update → 404 for unknown id", () => {
    const res = runClipCommand({ subcommand: "update", id: "ghost", title: "x" });
    expect(res.ok).toBe(false);
    expect(res.message).toContain("not found");
  });

  it("delete → removes a clip, then 404 on repeat", () => {
    const created = runClipCommand({
      subcommand: "add",
      title: "Tmp",
      filePath: "/t.mp4",
      durationSeconds: 5,
    });
    const id = created.clip!.id;

    expect(runClipCommand({ subcommand: "delete", id }).ok).toBe(true);
    const again = runClipCommand({ subcommand: "delete", id });
    expect(again.ok).toBe(false);
    expect(again.message).toContain("not found");
  });
});
