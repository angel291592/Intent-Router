import { Router } from "express";
import {
  createUser,
  deleteUser,
  listUsers,
  readUser,
  readUserPrefs,
} from "../db/users";

export const usersRouter = Router();

// GET /api/users
usersRouter.get("/", async (_req, res) => {
  const users = await listUsers();
  res.json({ users });
});

// GET /api/users/:id
usersRouter.get("/:id", async (req, res) => {
  const user = await readUser(req.params.id);
  if (user === null) {
    res.status(404).json({ error: "not_found" });
    return;
  }
  res.json({ user });
});

// GET /api/users/:id/prefs
usersRouter.get("/:id/prefs", async (req, res) => {
  const prefs = await readUserPrefs(req.params.id);
  if (prefs === null) {
    res.status(404).json({ error: "not_found" });
    return;
  }
  res.json({ prefs });
});

// POST /api/users
usersRouter.post("/", async (req, res) => {
  const user = await createUser(req.body);
  res.status(201).json({ user });
});

// DELETE /api/users/:id
usersRouter.delete("/:id", async (req, res) => {
  const removed = await deleteUser(req.params.id);
  res.status(removed ? 204 : 404).end();
});
