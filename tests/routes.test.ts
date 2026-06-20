import { describe, it, expect, beforeEach } from "vitest";
import fs from "fs";
import path from "path";
import request from "supertest";
import app from "../src/index.js";

const DATA_FILE = path.join(process.env.CLIPS_DATA_DIR as string, "clips.json");
const base = "/api/v1";

const valid = { title: "Intro", filePath: "/clips/intro.mp4", durationSeconds: 120, tags: ["intro"] };

beforeEach(() => {
  if (fs.existsSync(DATA_FILE)) fs.rmSync(DATA_FILE);
});

describe("health", () => {
  it("GET /healthz returns ok", async () => {
    const res = await request(app).get("/healthz");
    expect(res.status).toBe(200);
    expect(res.body).toEqual({ status: "ok" });
  });
});

describe("POST /clips", () => {
  it("creates a clip", async () => {
    const res = await request(app).post(`${base}/clips`).send(valid);
    expect(res.status).toBe(201);
    expect(res.body.id).toBeTruthy();
    expect(res.body.title).toBe("Intro");
  });

  it("rejects invalid input with 400 and errors", async () => {
    const res = await request(app).post(`${base}/clips`).send({ title: "" });
    expect(res.status).toBe(400);
    expect(Array.isArray(res.body.errors)).toBe(true);
  });
});

describe("GET /clips", () => {
  it("returns a paginated envelope", async () => {
    for (let i = 0; i < 3; i++) {
      await request(app).post(`${base}/clips`).send({ ...valid, title: `c${i}` });
    }
    const res = await request(app).get(`${base}/clips`);
    expect(res.status).toBe(200);
    expect(res.body.total).toBe(3);
    expect(res.body.page).toBe(1);
    expect(res.body.data).toHaveLength(3);
  });

  it("filters by tag", async () => {
    await request(app).post(`${base}/clips`).send({ ...valid, tags: ["a"] });
    await request(app).post(`${base}/clips`).send({ ...valid, tags: ["b"] });
    const res = await request(app).get(`${base}/clips`).query({ tag: "a" });
    expect(res.body.total).toBe(1);
    expect(res.body.data[0].tags).toContain("a");
  });

  it("honors page and limit", async () => {
    for (let i = 0; i < 5; i++) {
      await request(app).post(`${base}/clips`).send({ ...valid, title: `c${i}` });
    }
    const res = await request(app).get(`${base}/clips`).query({ page: 2, limit: 2 });
    expect(res.body.page).toBe(2);
    expect(res.body.limit).toBe(2);
    expect(res.body.data).toHaveLength(2);
  });
});

describe("GET/PATCH/DELETE /clips/:id", () => {
  it("round-trips a single clip", async () => {
    const created = await request(app).post(`${base}/clips`).send(valid);
    const id = created.body.id;

    const got = await request(app).get(`${base}/clips/${id}`);
    expect(got.status).toBe(200);
    expect(got.body.id).toBe(id);

    const patched = await request(app).patch(`${base}/clips/${id}`).send({ title: "Updated" });
    expect(patched.status).toBe(200);
    expect(patched.body.title).toBe("Updated");

    const deleted = await request(app).delete(`${base}/clips/${id}`);
    expect(deleted.status).toBe(204);

    const missing = await request(app).get(`${base}/clips/${id}`);
    expect(missing.status).toBe(404);
  });

  it("returns 404 for unknown id on update", async () => {
    const res = await request(app).patch(`${base}/clips/does-not-exist`).send({ title: "x" });
    expect(res.status).toBe(404);
  });

  it("returns 404 for unknown id on delete", async () => {
    const res = await request(app).delete(`${base}/clips/does-not-exist`);
    expect(res.status).toBe(404);
  });
});
