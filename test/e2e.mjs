// Drives the built single-file page in headless Chrome the way the secretary
// would: open it from disk, pick PDFs in the file input, read the table.
// Usage: node test/e2e.mjs <pdf-dir> [--expected file.json] [--screenshot out.png [--expand-all]] [--timeout s]

import { spawn } from "node:child_process";
import { mkdtempSync, readdirSync, readFileSync, rmSync, writeFileSync } from "node:fs";
import { tmpdir } from "node:os";
import { join, resolve } from "node:path";
import { pathToFileURL } from "node:url";

const CHROME = process.env.CHROME ?? "google-chrome";
const args = process.argv.slice(2);
const dir = resolve(args[0] ?? "test/fixtures");
const option = (/** @type {string} */ name) => (args.includes(name) ? args[args.indexOf(name) + 1] : undefined);
const files = readdirSync(dir)
  .filter((name) => /\.pdf$/i.test(name))
  .map((name) => join(dir, name));
const page = pathToFileURL(resolve("dist/scholarmine.html")).href;

const profile = mkdtempSync(join(tmpdir(), "scholarmine-e2e-"));
const chrome = spawn(CHROME, [
  "--headless=new",
  "--remote-debugging-port=0",
  `--user-data-dir=${profile}`,
  "--no-first-run",
  "--no-default-browser-check",
  "about:blank",
]);

try {
  const endpoint = await new Promise((done, fail) => {
    chrome.stderr.on("data", (chunk) => {
      const match = /DevTools listening on (ws:\/\/\S+)/.exec(String(chunk));
      if (match) {
        done(match[1]);
      }
    });
    chrome.on("exit", () => fail(new Error("Chrome exited before DevTools was ready")));
  });
  const cdp = await connect(endpoint);
  const { targetId } = await cdp.send("Target.createTarget", { url: "about:blank" });
  const { sessionId } = await cdp.send("Target.attachToTarget", { targetId, flatten: true });
  const send = (/** @type {string} */ method, params = {}) => cdp.send(method, params, sessionId);

  const requests = [];
  const errors = [];
  cdp.on("Network.requestWillBeSent", (event) => requests.push(event.request.url));
  cdp.on("Runtime.exceptionThrown", (event) => errors.push(event.exceptionDetails.exception?.description ?? event.exceptionDetails.text));
  cdp.on("Log.entryAdded", (event) => event.entry.level === "error" && errors.push(event.entry.text));
  await send("Network.enable");
  await send("Runtime.enable");
  await send("Log.enable");
  await send("Page.enable");
  await send("Emulation.setDeviceMetricsOverride", { width: 1280, height: 900, deviceScaleFactor: 1, mobile: false });
  await send("Page.navigate", { url: page });
  await waitFor(send, "document.readyState === 'complete'", 10_000);

  const { root } = await send("DOM.getDocument");
  const { nodeId } = await send("DOM.querySelector", { nodeId: root.nodeId, selector: "#picker" });
  const started = Date.now();
  await send("DOM.setFileInputFiles", { nodeId, files });
  try {
    await waitFor(
      send,
      `document.querySelectorAll('#rows tr').length === ${files.length} && document.getElementById('progress').hidden`,
      Number(option("--timeout") ?? 600) * 1000,
    );
  } catch (error) {
    const state = await evaluate(send, "document.getElementById('progress-text').textContent + ' | rows: ' + document.querySelectorAll('#rows tr').length");
    console.log(`stalled at: ${state}\npage errors: ${errors.join("\n  ") || "none"}`);
    throw error;
  }
  const seconds = (Date.now() - started) / 1000;

  const rows = await evaluate(
    send,
    `[...document.querySelectorAll('#rows tr')].map((tr) => ({
      file: tr.querySelector('button.file').textContent,
      orcid: tr.querySelectorAll('.id input')[0].value,
      scholar: tr.querySelectorAll('.id input')[1].value,
      status: tr.querySelector('.badge').textContent,
      review: tr.classList.contains('needs-review'),
    }))`,
  );
  console.log(`${files.length} files processed in the browser in ${seconds.toFixed(2)} s`);
  console.log(`summary line: ${await evaluate(send, "document.getElementById('summary').textContent")}`);

  const outside = requests.filter((url) => !/^(file|blob|data):/.test(url));
  console.log(`network requests leaving the machine: ${outside.length}${outside.length ? ` -> ${outside.join(", ")}` : ""}`);
  console.log(`page errors: ${errors.length}${errors.length ? `\n  ${errors.join("\n  ")}` : ""}`);

  let failures = 0;
  const expectedPath = option("--expected");
  if (expectedPath) {
    const expected = JSON.parse(readFileSync(expectedPath, "utf8"));
    for (const row of rows) {
      const want = expected[row.file];
      const got = { orcid: row.orcid, scholar: row.scholar, status: row.status, review: row.review };
      if (JSON.stringify(got) !== JSON.stringify(want)) {
        failures += 1;
        console.log(`MISMATCH ${row.file}: got ${JSON.stringify(got)} want ${JSON.stringify(want)}`);
      }
    }
    console.log(`${rows.length - failures}/${rows.length} rows match expected.json`);
  }

  const screenshot = option("--screenshot");
  if (screenshot) {
    if (args.includes("--expand-all")) {
      await evaluate(send, "document.querySelectorAll('details').forEach((d) => (d.open = true))");
    }
    const height = await evaluate(send, "document.documentElement.scrollHeight");
    await send("Emulation.setDeviceMetricsOverride", { width: 1280, height, deviceScaleFactor: 1, mobile: false });
    const { data } = await send("Page.captureScreenshot", { format: "png" });
    writeFileSync(screenshot, Buffer.from(data, "base64"));
    console.log(`screenshot: ${screenshot}`);
  }
  cdp.close();
  process.exitCode = failures > 0 || errors.length > 0 || outside.length > 0 ? 1 : 0;
} finally {
  chrome.kill();
  await new Promise((done) => chrome.once("exit", done));
  // Chrome can still be flushing its profile right after exiting.
  rmSync(profile, { recursive: true, force: true, maxRetries: 10, retryDelay: 200 });
}

/** @param {string} url */
async function connect(url) {
  const socket = new WebSocket(url);
  await new Promise((done, fail) => {
    socket.onopen = done;
    socket.onerror = fail;
  });
  let next = 0;
  const pending = new Map();
  const listeners = new Map();
  socket.onmessage = (message) => {
    const data = JSON.parse(String(message.data));
    if (data.id !== undefined) {
      const { done, fail } = pending.get(data.id);
      pending.delete(data.id);
      if (data.error) {
        fail(new Error(`${data.error.message} ${data.error.data ?? ""}`));
      } else {
        done(data.result);
      }
    } else {
      listeners.get(data.method)?.(data.params);
    }
  };
  return {
    /** @param {string} method @param {object} params @param {string} [sessionId] */
    send(method, params = {}, sessionId) {
      const id = ++next;
      socket.send(JSON.stringify({ id, method, params, sessionId }));
      return new Promise((done, fail) => pending.set(id, { done, fail }));
    },
    /** @param {string} method @param {(params: any) => void} listener */
    on(method, listener) {
      listeners.set(method, listener);
    },
    close() {
      socket.close();
    },
  };
}

/** @param {Function} send @param {string} expression */
async function evaluate(send, expression) {
  const { result, exceptionDetails } = await send("Runtime.evaluate", { expression, returnByValue: true });
  if (exceptionDetails) {
    throw new Error(exceptionDetails.exception?.description ?? exceptionDetails.text);
  }
  return result.value;
}

/** @param {Function} send @param {string} condition @param {number} timeout */
async function waitFor(send, condition, timeout) {
  const deadline = Date.now() + timeout;
  while (Date.now() < deadline) {
    if (await evaluate(send, condition)) {
      return;
    }
    await new Promise((done) => setTimeout(done, 100));
  }
  throw new Error(`Timed out waiting for: ${condition}`);
}
