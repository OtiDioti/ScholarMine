// Browser entry point: the secretary drops applicant PDFs, each is analysed
// on this computer, and the results appear in a table they can check, correct
// and export. Nothing is sent anywhere and nothing is kept after closing.

import * as pdfjs from "pdfjs-dist";

import { orcidChecksumOk, STATUS } from "./extract.js";
import { toCsv, toXlsx } from "./export.js";
import { analyseFile } from "./pipeline.js";

// build.mjs inlines the worker as a classic script string so the page works
// as one file opened from disk, where a separate worker file can't be loaded.
const workerUrl = URL.createObjectURL(new Blob([globalThis.PDFJS_WORKER_SOURCE], { type: "text/javascript" }));
pdfjs.GlobalWorkerOptions.workerPort = new Worker(workerUrl);

/**
 * @typedef {object} Row
 * @property {File} file
 * @property {import("./extract.js").Result} result
 * @property {boolean} checked - the secretary has looked at a flagged row
 */

/** @type {Row[]} */
const rows = [];
/** @type {File[]} */
const queue = [];
let running = false;

const $ = (/** @type {string} */ id) => /** @type {HTMLElement} */ (document.getElementById(id));
const picker = /** @type {HTMLInputElement} */ ($("picker"));
const tbody = $("rows");

picker.addEventListener("change", () => {
  enqueue([...(picker.files ?? [])]);
  picker.value = "";
});
$("drop").addEventListener("dragover", (event) => {
  event.preventDefault();
  $("drop").classList.add("over");
});
$("drop").addEventListener("dragleave", () => $("drop").classList.remove("over"));
$("drop").addEventListener("drop", (event) => {
  event.preventDefault();
  $("drop").classList.remove("over");
  enqueue([...(event.dataTransfer?.files ?? [])]);
});
$("only-review").addEventListener("change", (event) => {
  tbody.classList.toggle("only-review", /** @type {HTMLInputElement} */ (event.target).checked);
});
$("export-xlsx").addEventListener("click", () => download(toXlsx(...table(), new Set([1, 2])), "xlsx"));
$("export-csv").addEventListener("click", () => download(toCsv(...table()), "csv"));
$("clear").addEventListener("click", () => {
  rows.length = 0;
  tbody.replaceChildren();
  updateSummary();
});

/** @param {File[]} files */
function enqueue(files) {
  const known = new Set(rows.map((row) => `${row.file.name}:${row.file.size}`));
  const pdfs = files.filter((f) => /\.pdf$/i.test(f.name) && !known.has(`${f.name}:${f.size}`));
  queue.push(...pdfs.sort((a, b) => a.name.localeCompare(b.name)));
  if (!running) {
    void drain();
  }
}

async function drain() {
  running = true;
  let done = 0;
  $("progress").hidden = false;
  while (queue.length > 0) {
    // Files dropped while a batch runs join the same progress count.
    const total = done + queue.length;
    const file = /** @type {File} */ (queue.shift());
    $("progress-text").textContent = `Reading ${file.name} (${done + 1} of ${total})`;
    /** @type {HTMLProgressElement} */ ($("progress-bar")).value = done / total;
    const result = await analyseFile(pdfjs, new Uint8Array(await file.arrayBuffer()));
    const row = { file, result, checked: false };
    rows.push(row);
    tbody.append(renderRow(row));
    done += 1;
    updateSummary();
  }
  $("progress").hidden = true;
  running = false;
}

/** @param {Row} row */
function renderRow(row) {
  const tr = document.createElement("tr");
  const fileButton = el("button", { className: "file", textContent: row.file.name, title: "Open the PDF" });
  fileButton.addEventListener("click", () => {
    const url = URL.createObjectURL(row.file);
    window.open(url, "_blank", "noopener");
    setTimeout(() => URL.revokeObjectURL(url), 60_000);
  });

  const orcidCell = idCell(row.result.orcid, orcidUrl, parseOrcid, (id) => {
    row.result.orcid = id;
    refresh();
  });
  const scholarCell = idCell(row.result.scholar, scholarUrl, parseScholar, (id) => {
    row.result.scholar = id;
    refresh();
  });
  const status = el("span", { className: "badge" });
  const flag = el("label", { className: "flag" });
  const box = el("input", { type: "checkbox", title: "Mark as checked" });
  box.addEventListener("change", () => {
    row.checked = box.checked;
    refresh();
  });
  flag.append(box, " checked");

  const details = el("details");
  details.append(el("summary", { textContent: "why?" }));
  const list = el("ul");
  const others = [...row.result.otherOrcids.map(orcidUrl), ...row.result.otherScholars.map(scholarUrl)];
  for (const note of row.result.notes) {
    list.append(el("li", { textContent: note }));
  }
  if (others.length > 0) {
    list.append(el("li", { textContent: `Other identifiers in this file: ${others.join(", ")}` }));
  }
  details.append(list);

  tr.append(td(fileButton), td(orcidCell), td(scholarCell), td(status), td(flag), td(details));

  function refresh() {
    if (row.result.status !== STATUS.noText && row.result.status !== STATUS.unreadable) {
      row.result.status = statusFor(row.result.orcid, row.result.scholar);
    }
    status.textContent = row.result.status;
    status.dataset.status = row.result.status;
    const needsReview = row.result.review && !row.checked;
    tr.classList.toggle("needs-review", needsReview);
    flag.hidden = !row.result.review;
    updateSummary();
  }
  refresh();
  return tr;
}

/**
 * An editable identifier with a link to the profile, so the secretary can
 * fix a wrong pick by pasting the right URL or id.
 * @param {string} id
 * @param {(id: string) => string} toUrl
 * @param {(text: string) => string | null} parse
 * @param {(id: string) => void} onChange
 */
function idCell(id, toUrl, parse, onChange) {
  const wrap = el("div", { className: "id" });
  const input = el("input", { value: id, placeholder: "missing", spellcheck: false });
  const link = el("a", { textContent: "open ↗", target: "_blank", rel: "noopener noreferrer" });
  const show = (/** @type {string} */ value) => {
    link.hidden = value === "";
    link.href = value ? toUrl(value) : "";
  };
  input.addEventListener("change", () => {
    const parsed = input.value.trim() === "" ? "" : parse(input.value);
    input.classList.toggle("invalid", parsed === null);
    input.title = parsed === null ? "Not a valid identifier; it won't be exported." : "";
    if (parsed !== null) {
      input.value = parsed;
      show(parsed);
      onChange(parsed);
    }
  });
  show(id);
  wrap.append(input, link);
  return wrap;
}

/** @param {string} text */
function parseOrcid(text) {
  const match = /(\d{4}-?\d{4}-?\d{4}-?\d{3}[\dXx])/.exec(text.replace(/\s/g, ""));
  if (!match) {
    return null;
  }
  const digits = match[1].replaceAll("-", "").toUpperCase();
  const id = digits.match(/.{4}/g)?.join("-") ?? "";
  return orcidChecksumOk(id) ? id : null;
}

/** @param {string} text */
function parseScholar(text) {
  const trimmed = text.trim();
  const fromUrl = /[?&]user=([A-Za-z0-9_-]{12})(?![A-Za-z0-9_-])/.exec(trimmed);
  if (fromUrl) {
    return fromUrl[1];
  }
  return /^[A-Za-z0-9_-]{12}$/.test(trimmed) ? trimmed : null;
}

/** @param {string} id */
const orcidUrl = (id) => `https://orcid.org/${id}`;
/** @param {string} id */
const scholarUrl = (id) => `https://scholar.google.com/citations?user=${id}`;

/** @param {string} orcid @param {string} scholar */
function statusFor(orcid, scholar) {
  if (orcid && scholar) {
    return STATUS.ok;
  }
  return orcid || scholar ? STATUS.incomplete : STATUS.none;
}

function updateSummary() {
  const count = (/** @type {(row: Row) => boolean} */ test) => rows.filter(test).length;
  const review = count((row) => row.result.review && !row.checked);
  $("summary").textContent =
    rows.length === 0
      ? ""
      : `${rows.length} files · ${count((r) => r.result.status === STATUS.ok)} complete · ` +
        `${count((r) => r.result.status === STATUS.incomplete)} incomplete · ` +
        `${count((r) => !r.result.orcid && !r.result.scholar)} with nothing · ${review} to check`;
  $("results").hidden = rows.length === 0;
}

/** @returns {[string[], string[][]]} */
function table() {
  const header = ["File", "ORCID", "Google Scholar", "Status", "Needs check", "Other identifiers", "Notes"];
  const body = rows.map(({ file, result, checked }) => [
    file.name,
    result.orcid ? orcidUrl(result.orcid) : "",
    result.scholar ? scholarUrl(result.scholar) : "",
    result.status,
    result.review && !checked ? "yes" : "",
    [...result.otherOrcids.map(orcidUrl), ...result.otherScholars.map(scholarUrl)].join(" "),
    result.notes.join(" | "),
  ]);
  return [header, body];
}

/** @param {Blob} blob @param {string} extension */
function download(blob, extension) {
  const a = el("a", { href: URL.createObjectURL(blob), download: `applicants.${extension}` });
  a.click();
  setTimeout(() => URL.revokeObjectURL(a.href), 10_000);
}

/**
 * @template {keyof HTMLElementTagNameMap} K
 * @param {K} tag
 * @param {Partial<HTMLElementTagNameMap[K]>} [props]
 * @returns {HTMLElementTagNameMap[K]}
 */
function el(tag, props = {}) {
  return Object.assign(document.createElement(tag), props);
}

/** @param {Node} child */
function td(child) {
  const cell = document.createElement("td");
  cell.append(child);
  return cell;
}
