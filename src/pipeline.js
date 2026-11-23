// Turns one PDF file's bytes into a Result, mapping unreadable files to a
// result row instead of an exception so no applicant silently disappears.

import { analyse, emptyResult, STATUS } from "./extract.js";
import { readPdf } from "./readpdf.js";

/**
 * @param {typeof import("pdfjs-dist")} pdfjs
 * @param {Uint8Array} data
 * @returns {Promise<import("./extract.js").Result>}
 */
export async function analyseFile(pdfjs, data) {
  let pages;
  try {
    pages = await readPdf(pdfjs, data);
  } catch (error) {
    const reason = error instanceof Error ? error.message : String(error);
    return emptyResult(STATUS.unreadable, [`The PDF could not be opened: ${reason}`]);
  }
  return analyse(pages);
}
