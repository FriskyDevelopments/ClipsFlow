import fs from "fs";
import os from "os";
import path from "path";

// Point the file store at an isolated temp directory so tests never touch
// the real ./data directory. Must be set before any module that reads
// CLIPS_DATA_DIR at import time (store.ts), hence a setupFile.
const dir = fs.mkdtempSync(path.join(os.tmpdir(), "clipsflow-test-"));
process.env.CLIPS_DATA_DIR = dir;
process.env.NODE_ENV = "test";
