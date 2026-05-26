import { describe, it, expect } from "vitest";
import { validateCreateClip } from "../src/validators.js";

describe("validateCreateClip — required fields", () => {
  const base = { title: "Intro", filePath: "/clips/intro.mp4", durationSeconds: 120 };

  it("accepts a fully valid input", () => {
    expect(validateCreateClip(base).valid).toBe(true);
  });

  it("rejects null input", () => {
    expect(validateCreateClip(null).valid).toBe(false);
  });

  it("rejects empty title", () => {
    const r = validateCreateClip({ ...base, title: "  " });
    expect(r.valid).toBe(false);
    expect(r.errors).toContain("title must be a non-empty string");
  });

  it("rejects empty filePath", () => {
    const r = validateCreateClip({ ...base, filePath: "" });
    expect(r.valid).toBe(false);
    expect(r.errors).toContain("filePath must be a non-empty string");
  });

  it("rejects invalid tags", () => {
    const r = validateCreateClip({ ...base, tags: [1, 2] });
    expect(r.valid).toBe(false);
    expect(r.errors).toContain("tags must be an array of strings");
  });

  it("accepts valid tags", () => {
    expect(validateCreateClip({ ...base, tags: ["intro", "v1"] }).valid).toBe(true);
  });
});

describe("validateCreateClip — durationSeconds", () => {
  const base = { title: "Intro", filePath: "/clips/intro.mp4" };

  it("accepts a valid duration", () => {
    const r = validateCreateClip({ ...base, durationSeconds: 120 });
    expect(r.valid).toBe(true);
    expect(r.errors).toHaveLength(0);
  });

  it("accepts exactly 3600 seconds (boundary)", () => {
    expect(validateCreateClip({ ...base, durationSeconds: 3600 }).valid).toBe(true);
  });

  it("rejects missing durationSeconds", () => {
    const r = validateCreateClip(base);
    expect(r.valid).toBe(false);
    expect(r.errors.some((e) => e.includes("durationSeconds"))).toBe(true);
  });

  it("rejects duration = 0", () => {
    const r = validateCreateClip({ ...base, durationSeconds: 0 });
    expect(r.valid).toBe(false);
    expect(r.errors).toContain("durationSeconds must be a positive finite number");
  });

  it("rejects negative duration", () => {
    const r = validateCreateClip({ ...base, durationSeconds: -30 });
    expect(r.valid).toBe(false);
    expect(r.errors.some((e) => e.includes("positive finite number"))).toBe(true);
  });

  it("rejects NaN", () => {
    expect(validateCreateClip({ ...base, durationSeconds: NaN }).valid).toBe(false);
  });

  it("rejects Infinity", () => {
    expect(validateCreateClip({ ...base, durationSeconds: Infinity }).valid).toBe(false);
  });

  it("rejects duration exceeding 3600 seconds", () => {
    const r = validateCreateClip({ ...base, durationSeconds: 3601 });
    expect(r.valid).toBe(false);
    expect(r.errors[0]).toContain("must not exceed 3600");
  });
});
