// In-memory stub. Real deployments talk to Postgres; the fixture keeps it simple
// so the evaluation needs no services running.

export interface User {
  id: string;
  email: string;
  name: string;
}

export interface UserPrefs {
  locale: string;
  theme: "light" | "dark";
  newsletter: boolean;
}

const users = new Map<string, User>([
  ["u_1", { id: "u_1", email: "ada@example.com", name: "Ada" }],
  ["u_2", { id: "u_2", email: "grace@example.com", name: "Grace" }],
]);

const prefs = new Map<string, UserPrefs>([
  ["u_1", { locale: "en-GB", theme: "dark", newsletter: true }],
  ["u_2", { locale: "en-US", theme: "light", newsletter: false }],
]);

export async function listUsers(): Promise<User[]> {
  return [...users.values()];
}

export async function readUser(id: string): Promise<User | null> {
  return users.get(id) ?? null;
}

export async function readUserPrefs(id: string): Promise<UserPrefs | null> {
  return prefs.get(id) ?? null;
}

export async function createUser(input: Omit<User, "id">): Promise<User> {
  const id = `u_${users.size + 1}`;
  const user: User = { id, ...input };
  users.set(id, user);
  return user;
}

export async function deleteUser(id: string): Promise<boolean> {
  prefs.delete(id);
  return users.delete(id);
}
