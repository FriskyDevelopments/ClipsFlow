import type { Request, Response, Router } from "express";
import { validateTelegram } from "./telegramAuth";

export function registerTelegramAuthRoute(app: Router): void {
  app.post("/auth", (req: Request, res: Response) => {
    const { initData } = req.body ?? {};

    if (typeof initData !== "string") {
      return res.status(400).json({ ok: false, error: "initData is required" });
    }

    const token = process.env.BOT_TOKEN;
    if (!token) {
      return res.status(500).json({ ok: false, error: "BOT_TOKEN is not configured" });
    }

    const valid = validateTelegram(initData, token);

    if (!valid) {
      return res.status(403).json({ ok: false });
    }

    return res.json({ ok: true });
  });
}
