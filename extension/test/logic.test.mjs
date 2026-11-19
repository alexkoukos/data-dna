import test from "node:test";
import assert from "node:assert/strict";
import { createRequire } from "node:module";

const L = createRequire(import.meta.url)("../logic.js");

test("a gate that cannot be reached lets the text through with a badge", () => {
  for (const s of [0, 429, 502, 503, 504]) assert.equal(L.failMode(s), "open");
  assert.equal(L.failMode(401), "badge");
});

test("a gate that refuses or fails in another way blocks, it never lets text through unchecked", () => {
  for (const s of [413, 422, 400, 403, 404, 500, 501])
    assert.equal(L.failMode(s), "block");
});

test("too long text says what to do", () => {
  assert.match(L.failReasons(413)[0], /shorten it or use Company AI/);
  assert.match(L.failReasons(422)[0], /shorten it or use Company AI/);
  assert.match(L.failReasons(500)[0], /Try again, or use Company AI/);
});

test("the limit matches the brain", () => {
  assert.equal(L.MAX_CHARS, 100000);
});

test("only http and https links are followed", () => {
  assert.equal(L.safeHref("https://example.com/a"), "https://example.com/a");
  assert.equal(
    L.safeHref("http://localhost:3000/chat"),
    "http://localhost:3000/chat",
  );
  for (const bad of [
    "javascript:alert(1)",
    "data:text/html,x",
    "chrome://settings",
    "nope",
    "",
    undefined,
  ])
    assert.equal(L.safeHref(bad), "#");
});
