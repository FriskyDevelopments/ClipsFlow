import express from "express";
import rateLimit from "express-rate-limit";
import router from "./routes.js";

const app = express();
const PORT = process.env.PORT ?? 3000;

app.use(express.json());

// Liveness/readiness probe for load balancers and orchestrators.
app.get("/healthz", (_req, res) => {
  res.json({ status: "ok" });
});

// Request-level rate limiting protects the unauthenticated write path
// (POST /clips) from flooding the store. Window/cap are env-tunable and
// the limiter is bypassed under test to keep the suite deterministic.
const limiter = rateLimit({
  windowMs: Number(process.env.RATE_LIMIT_WINDOW_MS ?? 60_000),
  max: Number(process.env.RATE_LIMIT_MAX ?? 100),
  standardHeaders: true,
  legacyHeaders: false,
  skip: () => process.env.NODE_ENV === "test",
});

app.use("/api/v1", limiter, router);

// Don't bind a port when imported by the test runner.
if (process.env.NODE_ENV !== "test") {
  app.listen(PORT, () => {
    console.log(`ClipsFlow API running on http://localhost:${PORT}/api/v1`);
  });
}

export default app;
