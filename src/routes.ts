import { Router, Request, Response } from "express";
import * as clips from "./clips.js";
import { ValidationError } from "./clips.js";

const router = Router();

router.post("/clips", (req: Request, res: Response) => {
  try {
    const clip = clips.createClip(req.body);
    res.status(201).json(clip);
  } catch (err) {
    if (err instanceof ValidationError) {
      res.status(400).json({ errors: err.errors });
    } else {
      res.status(500).json({ error: "Internal server error" });
    }
  }
});

router.get("/clips", (req: Request, res: Response) => {
  const query = {
    tag: req.query.tag as string | undefined,
    page: req.query.page ? Number(req.query.page) : undefined,
    limit: req.query.limit ? Number(req.query.limit) : undefined,
  };
  res.json(clips.listClips(query));
});

router.get("/clips/:id", (req: Request, res: Response) => {
  const clip = clips.getClip(req.params.id);
  if (!clip) {
    res.status(404).json({ error: "Clip not found" });
    return;
  }
  res.json(clip);
});

router.patch("/clips/:id", (req: Request, res: Response) => {
  try {
    const clip = clips.updateClip(req.params.id, req.body);
    res.json(clip);
  } catch (err) {
    if (err instanceof ValidationError) {
      res.status(400).json({ errors: err.errors });
    } else if (err instanceof Error && err.message.includes("not found")) {
      res.status(404).json({ error: err.message });
    } else {
      res.status(500).json({ error: "Internal server error" });
    }
  }
});

router.delete("/clips/:id", (req: Request, res: Response) => {
  try {
    clips.deleteClip(req.params.id);
    res.status(204).send();
  } catch (err) {
    if (err instanceof Error && err.message.includes("not found")) {
      res.status(404).json({ error: err.message });
    } else {
      res.status(500).json({ error: "Internal server error" });
    }
  }
});

export default router;
