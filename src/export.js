// Builds the downloadable results: CSV for any tool, and a minimal .xlsx so
// Excel in German (or any semicolon) locale opens it in columns without an
// import wizard. Written by hand to keep the page dependency-free.

/**
 * @param {string[]} header
 * @param {string[][]} rows
 */
export function toCsv(header, rows) {
  const lines = [header, ...rows].map((cells) => cells.map(csvCell).join(","));
  // The BOM makes Excel read the file as UTF-8 instead of the local code page.
  return new Blob(["\uFEFF" + lines.join("\r\n") + "\r\n"], { type: "text/csv;charset=utf-8" });
}

/** @param {string} value */
function csvCell(value) {
  // File names and PDF snippets come from applicants; a leading = + - @
  // would run as a formula when the CSV is opened in a spreadsheet.
  const safe = /^[=+\-@\t\r]/.test(value) ? `'${value}` : value;
  return /[",\r\n]/.test(safe) ? `"${safe.replaceAll('"', '""')}"` : safe;
}

/**
 * @param {string[]} header
 * @param {string[][]} rows
 * @param {Set<number>} linkColumns - columns holding URLs to make clickable
 */
export function toXlsx(header, rows, linkColumns) {
  const sheetRows = [header, ...rows].map((cells, r) => {
    const xmlCells = cells.map((value, c) => xlsxCell(value, r, c, r > 0 && linkColumns.has(c)));
    return `<row r="${r + 1}">${xmlCells.join("")}</row>`;
  });
  const widths = header.map(
    (_, c) => `<col min="${c + 1}" max="${c + 1}" width="${c === 0 ? 40 : 30}" customWidth="1"/>`,
  );
  const sheet =
    `<?xml version="1.0" encoding="UTF-8" standalone="yes"?>` +
    `<worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">` +
    `<sheetViews><sheetView workbookViewId="0"><pane ySplit="1" topLeftCell="A2" state="frozen"/></sheetView></sheetViews>` +
    `<cols>${widths.join("")}</cols><sheetData>${sheetRows.join("")}</sheetData></worksheet>`;
  const files = {
    "[Content_Types].xml":
      `<?xml version="1.0" encoding="UTF-8" standalone="yes"?>` +
      `<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">` +
      `<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>` +
      `<Default Extension="xml" ContentType="application/xml"/>` +
      `<Override PartName="/xl/workbook.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet.main+xml"/>` +
      `<Override PartName="/xl/worksheets/sheet1.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml"/>` +
      `</Types>`,
    "_rels/.rels":
      `<?xml version="1.0" encoding="UTF-8" standalone="yes"?>` +
      `<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">` +
      `<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="xl/workbook.xml"/>` +
      `</Relationships>`,
    "xl/workbook.xml":
      `<?xml version="1.0" encoding="UTF-8" standalone="yes"?>` +
      `<workbook xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships">` +
      `<sheets><sheet name="Applicants" sheetId="1" r:id="rId1"/></sheets></workbook>`,
    "xl/_rels/workbook.xml.rels":
      `<?xml version="1.0" encoding="UTF-8" standalone="yes"?>` +
      `<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">` +
      `<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet" Target="worksheets/sheet1.xml"/>` +
      `</Relationships>`,
    "xl/worksheets/sheet1.xml": sheet,
  };
  return new Blob([zipStored(files)], { type: "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet" });
}

/** @param {string} value @param {number} r @param {number} c @param {boolean} link */
function xlsxCell(value, r, c, link) {
  const ref = columnName(c) + (r + 1);
  if (link && /^https:\/\/[^"]+$/.test(value)) {
    const url = xmlEscape(value);
    return `<c r="${ref}" t="str"><f>HYPERLINK("${url}")</f><v>${url}</v></c>`;
  }
  return `<c r="${ref}" t="inlineStr"><is><t xml:space="preserve">${xmlEscape(value)}</t></is></c>`;
}

/** @param {number} index */
function columnName(index) {
  let name = "";
  for (let n = index + 1; n > 0; n = Math.floor((n - 1) / 26)) {
    name = String.fromCharCode(65 + ((n - 1) % 26)) + name;
  }
  return name;
}

/** @param {string} text */
function xmlEscape(text) {
  return text
    .replace(/[\u0000-\u0008\u000B\u000C\u000E-\u001F]/g, "")
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;");
}

const CRC_TABLE = Array.from({ length: 256 }, (_, n) => {
  let c = n;
  for (let k = 0; k < 8; k++) {
    c = c & 1 ? 0xedb88320 ^ (c >>> 1) : c >>> 1;
  }
  return c >>> 0;
});

/** @param {Uint8Array} bytes */
function crc32(bytes) {
  let crc = 0xffffffff;
  for (const byte of bytes) {
    crc = CRC_TABLE[(crc ^ byte) & 0xff] ^ (crc >>> 8);
  }
  return (crc ^ 0xffffffff) >>> 0;
}

/**
 * A zip archive without compression, which is all .xlsx needs.
 * @param {Record<string, string>} files
 */
export function zipStored(files) {
  const encoder = new TextEncoder();
  const chunks = [];
  const central = [];
  let offset = 0;
  for (const [name, content] of Object.entries(files)) {
    const nameBytes = encoder.encode(name);
    const data = encoder.encode(content);
    const crc = crc32(data);
    const local = header(30, [
      [0, 0x04034b50, 4],
      [4, 20, 2],
      [8, 0, 2],
      [10, 0, 2],
      [12, 0x21, 2],
      [14, crc, 4],
      [18, data.length, 4],
      [22, data.length, 4],
      [26, nameBytes.length, 2],
    ]);
    chunks.push(local, nameBytes, data);
    central.push(
      header(46, [
        [0, 0x02014b50, 4],
        [4, 20, 2],
        [6, 20, 2],
        [10, 0, 2],
        [14, 0x21, 2],
        [16, crc, 4],
        [20, data.length, 4],
        [24, data.length, 4],
        [28, nameBytes.length, 2],
        [42, offset, 4],
      ]),
      nameBytes,
    );
    offset += local.length + nameBytes.length + data.length;
  }
  const centralSize = central.reduce((sum, part) => sum + part.length, 0);
  const count = Object.keys(files).length;
  const end = header(22, [
    [0, 0x06054b50, 4],
    [8, count, 2],
    [10, count, 2],
    [12, centralSize, 4],
    [16, offset, 4],
  ]);
  return concat([...chunks, ...central, end]);
}

/** @param {number} size @param {Array<[number, number, 2 | 4]>} fields */
function header(size, fields) {
  const view = new DataView(new ArrayBuffer(size));
  for (const [at, value, width] of fields) {
    if (width === 2) {
      view.setUint16(at, value, true);
    } else {
      view.setUint32(at, value, true);
    }
  }
  return new Uint8Array(view.buffer);
}

/** @param {Uint8Array[]} parts */
function concat(parts) {
  const out = new Uint8Array(parts.reduce((sum, part) => sum + part.length, 0));
  let at = 0;
  for (const part of parts) {
    out.set(part, at);
    at += part.length;
  }
  return out;
}
