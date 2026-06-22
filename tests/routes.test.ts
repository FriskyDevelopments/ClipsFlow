import { describe, it, expect, beforeEach } from "vitest";
import { Hono } from "hono";
import { createApi } from "../src/api.js";
import { MemoryStore } from "../src/store.js";

const base = "/api/v1";
const valid = { title: "Intro", filePath: "/clips/intro.mp4", durationSeconds: 120, tags: ["intro"] };

let app: Hono;

beforeEach(() => {
  app = createApi(new MemoryStore());
});

function post(path: string, body: unknown) {
  return app.request(path, {
    method: "POST",
    body: JSON.stringify(body),
    headers: { "content-type": "application/json" },
  });
}

describe("health", () => {
  it("GET /healthz returns ok", async () => {
    const res = await app.request("/healthz");
    expect(res.status).toBe(200);
    expect(await res.json()).toEqual({ status: "ok" });
  });
});

describe("POST /clips", () => {
  it("creates a clip", async () => {
    const res = await post(`${base}/clips`, valid);
    expect(res.status).toBe(201);
    const body = (await res.json()) as any;
    expect(body.id).toBeTruthy();
    expect(body.title).toBe("Intro");
  });

  it("rejects invalid input with 400 and errors", async () => {
    const res = await post(`${base}/clips`, { title: "" });
    expect(res.status).toBe(400);
    const body = (await res.json()) as any;
    expect(Array.isArray(body.errors)).toBe(true);
  });
});

describe("GET /clips", () => {
  it("returns a paginated envelope", async () => {
    for (let i = 0; i < 3; i++) await post(`${base}/clips`, { ...valid, title: `c${i}` });
    const res = await app.request(`${base}/clips`);
    expect(res.status).toBe(200);
    const body = (await res.json()) as any;
    expect(body.total).toBe(3);
    expect(body.page).toBe(1);
    expect(body.data).toHaveLength(3);
  });

  it("filters by tag", async () => {
    await post(`${base}/clips`, { ...valid, tags: ["a"] });
    await post(`${base}/clips`, { ...valid, tags: ["b"] });
    const res = await app.request(`${base}/clips?tag=a`);
    const body = (await res.json()) as any;
    expect(body.total).toBe(1);
    expect(body.data[0].tags).toContain("a");
  });

  it("honors page and limit", async () => {
    for (let i = 0; i < 5; i++) await post(`${base}/clips`, { ...valid, title: `c${i}` });
    const res = await app.request(`${base}/clips?page=2&limit=2`);
    const body = (await res.json()) as any;
    expect(body.page).toBe(2);
    expect(body.limit).toBe(2);
    expect(body.data).toHaveLength(2);
  });
});

describe("GET/PATCH/DELETE /clips/:id", () => {
  it("round-trips a single clip", async () => {
    const created = (await (await post(`${base}/clips`, valid)).json()) as any;
    const id = created.id;

    const got = await app.request(`${base}/clips/${id}`);
    expect(got.status).toBe(200);
    expect(((await got.json()) as any).id).toBe(id);

    const patched = await app.request(`${base}/clips/${id}`, {
      method: "PATCH",
      body: JSON.stringify({ title: "Updated" }),
      headers: { "content-type": "application/json" },
    });
    expect(patched.status).toBe(200);
    expect(((await patched.json()) as any).title).toBe("Updated");

    const deleted = await app.request(`${base}/clips/${id}`, { method: "DELETE" });
    expect(deleted.status).toBe(204);

    const missing = await app.request(`${base}/clips/${id}`);
    expect(missing.status).toBe(404);
  });

  it("returns 404 for unknown id on update", async () => {
    const res = await app.request(`${base}/clips/does-not-exist`, {
      method: "PATCH",
      body: JSON.stringify({ title: "x" }),
      headers: { "content-type": "application/json" },
    });
    expect(res.status).toBe(404);
  });

  it("returns 404 for unknown id on delete", async () => {
    const res = await app.request(`${base}/clips/does-not-exist`, { method: "DELETE" });
    expect(res.status).toBe(404);
  });
});
