# ScholarMine

Finds each applicant's ORCID iD and Google Scholar profile in their application PDF,
for screening PhD and postdoc applications.

ScholarMine is a single HTML page. The PDFs are read in the browser with
[pdf.js](https://mozilla.github.io/pdf.js/). The page's Content-Security-Policy blocks
all network access, so applicant files never leave the computer, and nothing is
stored once the tab is closed.

The earlier Python command-line version is kept on the
[`legacy`](../../tree/legacy) branch.

## Use

1. Open `dist/scholarmine.html` in Chrome or Edge (Firefox is untested). It runs
   straight from disk and needs no installation, so the file can be copied to
   any computer.
2. Drop the applicants' PDFs (one per applicant) on the page, or click to pick them.
3. Review the table:
   - Highlighted rows need a person to look at them; tick **checked** once done.
   - **why?** shows where each identifier was found and why others were set aside.
     Examples: a check digit that doesn't match, an iD inside a reference letter or
     the publication list, a scanned page without text.
   - Click a file name to open the PDF. To correct an identifier, paste the right
     URL or iD into its field.
4. Download the results as Excel or CSV.

## Build

Needs Node 22.13 or later.

```
npm install
npm run build        # writes dist/scholarmine.html (about 1.6 MB, self-contained)
```

## Test

```
npm test                                                                   # logic and export tests in Node
node test/e2e.mjs test/fixtures --expected test/fixtures/expected.json   # the built page in headless Chrome
```

`node test/e2e.mjs <folder> --screenshot out.png --expand-all` runs any folder of
PDFs through the built page and saves a screenshot with every explanation open.

`test/fixtures/make_fixtures.py` (needs PyMuPDF and the DejaVu Sans font)
regenerates the synthetic test PDFs. `test/fixtures/expected.json` holds the
hand-written answers.

## Layout

- `src/extract.js`: finds, validates and ranks identifiers, and writes the "why?" notes
- `src/readpdf.js`: page text and link targets via pdf.js
- `src/pipeline.js`: one file in, one result out; unreadable files become rows too
- `src/export.js`: CSV and a dependency-free .xlsx writer
- `src/app.js`, `src/index.html`: the page
- `build.mjs`: inlines everything, including the pdf.js worker, into one HTML file

## License

MIT. The built page includes pdf.js, which is Apache-2.0 licensed.
