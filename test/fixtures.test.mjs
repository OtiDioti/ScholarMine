// Runs the full read-and-analyse pipeline on every fixture PDF and compares
// the outcome with the hand-written expectations in fixtures/expected.json.

import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { test } from "node:test";
import * as pdfjs from "pdfjs-dist/legacy/build/pdf.mjs";

import { analyseFile } from "../src/pipeline.js";

const fixtures = new URL("./fixtures/", import.meta.url);
const expected = JSON.parse(readFileSync(new URL("expected.json", fixtures), "utf8"));

for (const [name, want] of Object.entries(expected)) {
  test(name, async () => {
    const data = new Uint8Array(readFileSync(new URL(name, fixtures)));
    const got = await analyseFile(pdfjs, data);
    const summary = { orcid: got.orcid, scholar: got.scholar, status: got.status, review: got.review };
    assert.deepEqual(summary, want, got.notes.join("\n"));
  });
}
