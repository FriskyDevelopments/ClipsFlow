import express from "express";
import router from "./routes.js";

const app = express();
const PORT = process.env.PORT ?? 3000;

app.use(express.json());
app.use("/api/v1", router);

app.listen(PORT, () => {
  console.log(`ClipsFlow API running on http://localhost:${PORT}/api/v1`);
});

export default app;
