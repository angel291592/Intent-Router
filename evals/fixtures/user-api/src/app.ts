import express from "express";
import { usersRouter } from "./routes/users";

export const app = express();

app.use(express.json());
app.use("/api/users", usersRouter);

app.get("/healthz", (_req, res) => {
  res.json({ ok: true });
});

const port = Number(process.env.PORT ?? 3000);

if (require.main === module) {
  app.listen(port, () => {
    console.log(`user-api listening on ${port}`);
  });
}
