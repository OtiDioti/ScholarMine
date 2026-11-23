// Checks the export formats keep applicant-controlled text inert and that the
// .xlsx container is a well-formed zip with the parts Excel requires.

import assert from "node:assert/strict";
import { test } from "node:test";

import { toCsv, toXlsx } from "../src/export.js";

test("CSV neutralises formulas and quotes awkward cells", async () => {
  const blob = toCsv(["File", "Notes"], [["=HYPERLINK(\"http://evil\")", 'say "hi", twice\nok']]);
  // Blob.text() would strip the BOM, which is part of what is being tested.
  const text = new TextDecoder("utf-8", { ignoreBOM: true }).decode(await blob.arrayBuffer());
  assert.equal(text, '\uFEFFFile,Notes\r\n"\'=HYPERLINK(""http://evil"")","say ""hi"", twice\nok"\r\n');
});

test("XLSX is a zip holding the workbook parts, with text kept as strings", async () => {
  const blob = toXlsx(["File", "ORCID"], [["=1+1.pdf", "https://orcid.org/0000-0002-1825-0097"]], new Set([1]));
  const bytes = new Uint8Array(await blob.arrayBuffer());
  const raw = new TextDecoder().decode(bytes);
  assert.deepEqual([...bytes.slice(0, 4)], [0x50, 0x4b, 0x03, 0x04]);
  for (const part of ["[Content_Types].xml", "xl/workbook.xml", "xl/worksheets/sheet1.xml"]) {
    assert.ok(raw.includes(part), part);
  }
  assert.ok(raw.includes('<t xml:space="preserve">=1+1.pdf</t>'));
  assert.ok(raw.includes('<f>HYPERLINK("https://orcid.org/0000-0002-1825-0097")</f>'));
});
