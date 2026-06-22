import { Hono } from "hono";
import * as clips from "./clips.js";
import { ValidationError } from "./clips.js";
import { ClipStore } from "./store.js";

/**
 * Builds the clip HTTP API over an injected {@link ClipStore}. Returning a
 * plain Hono app (rather than wiring globals) keeps it testable with an
 * in-memory store and lets the Worker compose it behind rate limiting.
 */
export function createApi(store: ClipStore): Hono {
  const app = new Hono();

  // Liveness/readiness probe.
  app.get("/healthz", (c) => c.json({ status: "ok" }));

  const v1 = new Hono();

  v1.post("/clips", async (c) => {
    try {
      const body = await c.req.json().catch(() => ({}));
      const clip = await clips.createClip(store, body);
      return c.json(clip, 201);
    } catch (err) {
      if (err instanceof ValidationError) return c.json({ errors: err.errors }, 400);
      return c.json({ error: "Internal server error" }, 500);
    }
  });

  v1.get("/clips", async (c) => {
    const tag = c.req.query("tag");
    const pageRaw = c.req.query("page");
    const limitRaw = c.req.query("limit");
    const result = await clips.listClips(store, {
      tag: tag ?? undefined,
      page: pageRaw ? Number(pageRaw) : undefined,
      limit: limitRaw ? Number(limitRaw) : undefined,
    });
    return c.json(result);
  });

  v1.get("/clips/:id", async (c) => {
    const clip = await clips.getClip(store, c.req.param("id"));
    if (!clip) return c.json({ error: "Clip not found" }, 404);
    return c.json(clip);
  });

  v1.patch("/clips/:id", async (c) => {
    try {
      const body = await c.req.json().catch(() => ({}));
      const clip = await clips.updateClip(store, c.req.param("id"), body);
      return c.json(clip);
    } catch (err) {
      if (err instanceof ValidationError) return c.json({ errors: err.errors }, 400);
      if (err instanceof Error && err.message.includes("not found")) {
        return c.json({ error: err.message }, 404);
      }
      return c.json({ error: "Internal server error" }, 500);
    }
  });

  v1.delete("/clips/:id", async (c) => {
    try {
      await clips.deleteClip(store, c.req.param("id"));
      return c.body(null, 204);
    } catch (err) {
      if (err instanceof Error && err.message.includes("not found")) {
        return c.json({ error: err.message }, 404);
      }
      return c.json({ error: "Internal server error" }, 500);
    }
  });

  app.route("/api/v1", v1);
  return app;
}
