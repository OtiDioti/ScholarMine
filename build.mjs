// Bundles the app and the pdf.js worker into dist/scholarmine.html, a single
// file the secretary can open from disk with no install and no network.

import { build } from "esbuild";
import { mkdirSync, readFileSync, writeFileSync } from "node:fs";

const bundle = await build({
  entryPoints: ["src/app.js"],
  bundle: true,
  format: "esm",
  minify: true,
  target: "es2022",
  write: false,
  legalComments: "eof",
});
const app = bundle.outputFiles[0].text;
// Chrome refuses module workers created from blob: URLs on a file:// page,
// so the worker is rebuilt as a classic script.
const workerBundle = await build({
  entryPoints: ["node_modules/pdfjs-dist/build/pdf.worker.min.mjs"],
  bundle: true,
  format: "iife",
  minify: true,
  target: "es2022",
  write: false,
  legalComments: "eof",
});
const worker = workerBundle.outputFiles[0].text;

// Escaping every "<" keeps the HTML parser from ever seeing "</script" or
// "<!--" inside the inlined code.
const workerScript = `<script>globalThis.PDFJS_WORKER_SOURCE = ${JSON.stringify(worker).replaceAll("<", "\\u003c")};</script>`;
const appScript = `<script type="module">${app.replace(/<\/(script)/gi, "<\\/$1")}</script>`;
if (/<!--/.test(app)) {
  throw new Error("The app bundle contains '<!--', which is unsafe to inline in a script tag.");
}

const template = readFileSync("src/index.html", "utf8");
const html = template.replace("<!-- PDFJS_WORKER -->", () => workerScript).replace("<!-- APP -->", () => appScript);
mkdirSync("dist", { recursive: true });
writeFileSync("dist/scholarmine.html", html);
console.log(`dist/scholarmine.html: ${(html.length / 1024 / 1024).toFixed(2)} MB`);
