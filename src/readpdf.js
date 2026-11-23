// Reads the text and link targets of every page of a PDF with pdf.js.
// The pdf.js module is passed in so the same code runs in the browser
// (bundled build) and in Node tests (legacy build).

/**
 * @typedef {{text: string, links: string[]}} Page
 */

/**
 * @param {typeof import("pdfjs-dist")} pdfjs
 * @param {Uint8Array} data - PDF bytes; pdf.js takes ownership of the buffer.
 * @returns {Promise<Page[]>}
 */
export async function readPdf(pdfjs, data) {
  // Fonts are only needed for rendering; skipping them keeps extraction
  // fast and avoids fetching font data that a single offline file can't serve.
  const task = pdfjs.getDocument({ data, disableFontFace: true, useSystemFonts: false, verbosity: 0 });
  const doc = await task.promise;
  try {
    const pages = [];
    for (let n = 1; n <= doc.numPages; n++) {
      const page = await doc.getPage(n);
      const content = await page.getTextContent();
      const annotations = await page.getAnnotations();
      pages.push({ text: joinItems(content.items), links: linkTargets(annotations) });
      page.cleanup();
    }
    return pages;
  } finally {
    await task.destroy();
  }
}

/** @param {Array<{str?: string, hasEOL?: boolean}>} items */
function joinItems(items) {
  const parts = [];
  for (const item of items) {
    if (typeof item.str !== "string") {
      continue;
    }
    parts.push(item.str);
    if (item.hasEOL) {
      parts.push("\n");
    }
  }
  return parts.join("");
}

/** @param {Array<any>} annotations */
function linkTargets(annotations) {
  const urls = [];
  for (const annotation of annotations) {
    // `unsafeUrl` keeps the raw target when pdf.js refuses to build a URL
    // object from it, e.g. "orcid.org/..." without a scheme.
    const url = annotation.url || annotation.unsafeUrl;
    if (annotation.subtype === "Link" && typeof url === "string") {
      urls.push(url);
    }
  }
  return urls;
}
