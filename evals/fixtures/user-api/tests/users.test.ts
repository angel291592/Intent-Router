import { describe, expect, it } from "vitest";
import { listUsers, readUser, readUserPrefs } from "../src/db/users";

// These assertions are the response contract for the three read endpoints.
// Anything that changes the shape of what they return breaks clients.

describe("GET /api/users", () => {
  it("returns a users array of id, email and name", async () => {
    const users = await listUsers();
    expect(Array.isArray(users)).toBe(true);
    expect(Object.keys(users[0]).sort()).toEqual(["email", "id", "name"]);
  });
});

describe("GET /api/users/:id", () => {
  it("returns a single user with exactly id, email and name", async () => {
    const user = await readUser("u_1");
    expect(user).not.toBeNull();
    expect(Object.keys(user!).sort()).toEqual(["email", "id", "name"]);
  });

  it("returns null for an unknown id", async () => {
    expect(await readUser("nope")).toBeNull();
  });
});

describe("GET /api/users/:id/prefs", () => {
  it("returns locale, theme and newsletter", async () => {
    const prefs = await readUserPrefs("u_1");
    expect(Object.keys(prefs!).sort()).toEqual([
      "locale",
      "newsletter",
      "theme",
    ]);
  });
});
