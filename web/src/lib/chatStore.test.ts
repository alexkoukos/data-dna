import { beforeEach, describe, expect, it } from "vitest";
import { groupByPeriod, loadChats, saveChats, titleFrom, type Chat } from "./chatStore";

const chat = (id: string, updated: number): Chat => ({ id, title: id, updated, turns: [] });

describe("chatStore", () => {
  beforeEach(() => localStorage.clear());

  it("trims a long first question into a title", () => {
    expect(
      titleFrom("  How   long do we keep customer records before deleting them for good?  "),
    ).toHaveLength(42);
    expect(titleFrom("   ")).toBe("New chat");
  });

  it("groups chats by age, newest first, without empty groups", () => {
    const now = new Date(2026, 10, 18, 15).getTime();
    const day = 86_400_000;
    const groups = groupByPeriod(
      [
        chat("old", now - 20 * day),
        chat("a", now - 1000),
        chat("y", now - day),
        chat("w", now - 4 * day),
        chat("b", now - 5000),
      ],
      now,
    );
    expect(groups.map((g) => g.period)).toEqual(["Today", "Yesterday", "Previous 7 days", "Older"]);
    expect(groups[0]?.chats.map((c) => c.id)).toEqual(["a", "b"]);
  });

  it("saves and loads, and survives broken storage", () => {
    saveChats([chat("x", 1)]);
    expect(loadChats().map((c) => c.id)).toEqual(["x"]);
    localStorage.setItem("sentry.chats", "{nope");
    expect(loadChats()).toEqual([]);
  });
});

import { suggestFor } from "./chatPrompts";

describe("suggestFor", () => {
  it("matches what was typed anywhere in a prompt and ignores one-letter input", () => {
    expect(suggestFor("retention")).toEqual([
      "Summarise our data retention policy in two sentences",
    ]);
    expect(suggestFor("r")).toEqual([]);
    expect(suggestFor("draft a polite reply declining a vendor's offer")).toEqual([]);
  });
});
