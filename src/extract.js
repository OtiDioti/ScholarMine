// Picks the applicant's ORCID iD and Google Scholar profile out of the pages
// of one application PDF. Every candidate is kept with the reason it was
// chosen or set aside, because users can't share applicant files with the
// developer: the notes are how a miss gets diagnosed.

/** @typedef {{text: string, links: string[]}} Page */

/**
 * @typedef {object} Candidate
 * @property {"orcid" | "scholar"} kind
 * @property {string} id
 * @property {number} page - zero-based
 * @property {"link" | "text"} source
 * @property {number} score
 * @property {string | null} excluded - why it can't be the applicant's, if so
 */

/**
 * @typedef {object} Result
 * @property {string} orcid - e.g. "0000-0002-1825-0097", or ""
 * @property {string} scholar - Scholar user id, e.g. "AbCdEfGhIjKl", or ""
 * @property {string} status
 * @property {boolean} review - true when a person should look at the file
 * @property {string[]} otherOrcids
 * @property {string[]} otherScholars
 * @property {string[]} notes
 */

export const STATUS = Object.freeze({
  ok: "ok",
  incomplete: "incomplete",
  none: "nothing found",
  noText: "no text (scanned?)",
  unreadable: "unreadable",
});

const ORCID_IN_TEXT = /(?<![\dA-Za-z])(\d{4})\s*-\s*(\d{4})\s*-\s*(\d{4})\s*-\s*(\d{3}[\dXx])(?![\dA-Za-z])/g;
const ORCID_IN_URL = /orcid\.org\/(\d{4}-\d{4}-\d{4}-\d{3}[\dX])/i;
const SCHOLAR_URL = /scholar\.google\.[a-z.]{2,8}\/citations\?([^\s<>"')\]]*)/gi;
// A separate non-global copy for single URLs: exec() on a /g regex leaves
// lastIndex behind, and matchAll() copies it into later scans.
const SCHOLAR_URL_ONE = new RegExp(SCHOLAR_URL.source, "i");
// Scholar profile ids are 12 characters; anything else is flagged, not dropped.
const SCHOLAR_ID = /^[A-Za-z0-9_-]{12}$/;
const ORCID_LABEL = /orcid/i;
const THIRD_PARTY =
  /\b(supervisor|supervised by|advisor|adviser|co-?authors?|referees?|references?|recommender|mentor|professor|prof\.)(?![A-Za-z])/i;
const PUBLICATION_HEADING = /^\s*(selected\s+)?(publications|bibliography|references|papers)\b.*$/im;
const RECOMMENDATION =
  /(i am (very |most )?(pleased|delighted|happy|glad|honou?red) to (strongly |highly )?(recommend|support))|(letter of (recommendation|reference|support))|(it is (my|a) (great |real )?pleasure to (recommend|write))|(i have known \w+ (for|since))|(i (strongly|highly|warmly|wholeheartedly|unreservedly) recommend)/i;
const MIN_TEXT_CHARS = 30;
const CLOSE_CALL = 3;

/**
 * @param {Page[]} pages
 * @returns {Result}
 */
export function analyse(pages) {
  /** @type {string[]} */
  const notes = [];
  /** @type {Candidate[]} */
  const candidates = [];
  let review = false;

  pages.forEach((page, index) => {
    const found = scanPage(page, index);
    candidates.push(...found.candidates);
    notes.push(...found.notes);
    review ||= found.review;
  });

  if (!hasText(pages)) {
    notes.unshift("No readable text in this PDF. It is probably scanned; check it by hand.");
    return emptyResult(STATUS.noText, notes);
  }

  const orcid = choose(candidates, "orcid", "ORCID", notes);
  const scholar = choose(candidates, "scholar", "Google Scholar", notes);
  review ||= orcid.review || scholar.review;

  if (!orcid.id) {
    const missed = orcidLabelsWithoutId(pages);
    notes.push(...missed);
    review ||= missed.length > 0;
  }

  return {
    orcid: orcid.id,
    scholar: scholar.id,
    status: orcid.id && scholar.id ? STATUS.ok : orcid.id || scholar.id ? STATUS.incomplete : STATUS.none,
    review,
    otherOrcids: orcid.others,
    otherScholars: scholar.others,
    notes,
  };
}

/** @param {string} status @param {string[]} notes @returns {Result} */
export function emptyResult(status, notes) {
  return { orcid: "", scholar: "", status, review: true, otherOrcids: [], otherScholars: [], notes };
}

/** ISO 7064 Mod 11-2, the check digit ORCID uses. @param {string} id */
export function orcidChecksumOk(id) {
  const digits = id.replaceAll("-", "");
  let total = 0;
  for (const char of digits.slice(0, -1)) {
    total = (total + Number(char)) * 2;
  }
  const remainder = (12 - (total % 11)) % 11;
  const expected = remainder === 10 ? "X" : String(remainder);
  return digits.at(-1)?.toUpperCase() === expected;
}

/**
 * Undoes the ways PDF text mangles identifiers: typographic dashes, soft
 * hyphens, HTML entities, and URLs wrapped onto the next line.
 * @param {string} text
 */
export function normalise(text) {
  return text
    .normalize("NFKC")
    .replace(/­/g, "")
    .replace(/[‐-―−﹘﹣－]/g, "-")
    .replace(/&amp;/g, "&")
    .replace(/([?&=/])[ \t]*\r?\n\s*/g, "$1")
    .replace(/\s*\r?\n[ \t]*([?&=])/g, "$1");
}

/** @param {Page} page @param {number} index */
function scanPage(page, index) {
  const text = normalise(page.text);
  const letter = RECOMMENDATION.test(text);
  const heading = PUBLICATION_HEADING.exec(text);
  const publicationsStart = heading ? heading.index + heading[0].length : Infinity;
  /** @type {string[]} */
  const notes = [];
  /** @type {Candidate[]} */
  const candidates = [];
  let review = false;
  const where = `page ${index + 1}`;

  const exclusionFor = (/** @type {number} */ at) => {
    if (letter) {
      return `inside what looks like a recommendation letter (${where})`;
    }
    const line = text.slice(text.lastIndexOf("\n", at - 1) + 1, at);
    const thirdParty = THIRD_PARTY.exec(line);
    if (thirdParty) {
      return `next to "${thirdParty[0]}" (${where})`;
    }
    if (at > publicationsStart) {
      return `inside the publication list (${where})`;
    }
    return null;
  };

  for (const match of text.matchAll(ORCID_IN_TEXT)) {
    const id = match.slice(1, 5).join("-").toUpperCase();
    const before = text.slice(Math.max(0, match.index - 40), match.index);
    const labelled = ORCID_LABEL.test(before);
    if (!orcidChecksumOk(id)) {
      notes.push(`Ignored ${id} (${where}): shaped like an ORCID iD but its check digit is wrong.`);
      review ||= labelled;
      continue;
    }
    const score = pageScore(index) + (labelled ? 2 : 0);
    candidates.push({ kind: "orcid", id, page: index, source: "text", score, excluded: exclusionFor(match.index) });
  }

  for (const match of text.matchAll(SCHOLAR_URL)) {
    const scholar = scholarId(match[1]);
    if (scholar.problem) {
      notes.push(`Ignored Scholar link (${where}) "${match[0]}": ${scholar.problem}.`);
      review = true;
      continue;
    }
    candidates.push({
      kind: "scholar",
      id: scholar.id,
      page: index,
      source: "text",
      score: pageScore(index),
      excluded: exclusionFor(match.index),
    });
  }

  for (const url of page.links) {
    candidates.push(...linkCandidates(url, index, letter ? exclusionFor(0) : null, notes));
  }
  return { candidates, notes, review };
}

/**
 * @param {string} url
 * @param {number} index
 * @param {string | null} excluded
 * @param {string[]} notes
 * @returns {Candidate[]}
 */
function linkCandidates(url, index, excluded, notes) {
  const where = `page ${index + 1}`;
  const orcid = ORCID_IN_URL.exec(url);
  if (orcid) {
    const id = orcid[1].toUpperCase();
    if (!orcidChecksumOk(id)) {
      notes.push(`Ignored ORCID link ${url} (${where}): its check digit is wrong.`);
      return [];
    }
    return [{ kind: "orcid", id, page: index, source: "link", score: pageScore(index) + 4, excluded }];
  }
  const scholarMatch = SCHOLAR_URL_ONE.exec(normalise(url));
  if (!scholarMatch) {
    return [];
  }
  const scholar = scholarId(scholarMatch[1]);
  if (scholar.problem) {
    notes.push(`Ignored Scholar link ${url} (${where}): ${scholar.problem}.`);
    return [];
  }
  return [{ kind: "scholar", id: scholar.id, page: index, source: "link", score: pageScore(index) + 2, excluded }];
}

/** @param {string} query */
function scholarId(query) {
  const user = new URLSearchParams(query).get("user");
  if (!user) {
    return { id: "", problem: "it has no profile id (user=...)" };
  }
  if (!SCHOLAR_ID.test(user)) {
    return { id: "", problem: `profile id "${user}" is not the usual 12 characters` };
  }
  return { id: user, problem: null };
}

/** Applicants put their identifiers near the top of the CV. @param {number} index */
function pageScore(index) {
  return 10 - Math.min(index * 2, 6);
}

/**
 * @param {Candidate[]} all
 * @param {"orcid" | "scholar"} kind
 * @param {string} label
 * @param {string[]} notes
 */
function choose(all, kind, label, notes) {
  /** @type {Map<string, {id: string, occurrences: Candidate[]}>} */
  const byId = new Map();
  for (const candidate of all.filter((c) => c.kind === kind)) {
    const seen = byId.get(candidate.id) ?? { id: candidate.id, occurrences: [] };
    seen.occurrences.push(candidate);
    byId.set(candidate.id, seen);
  }
  const ranked = [...byId.values()].map((entry) => {
    const usable = entry.occurrences.filter((c) => c.excluded === null);
    const pool = usable.length > 0 ? usable : entry.occurrences;
    const best = pool.reduce((a, b) => (b.score > a.score ? b : a));
    return {
      id: entry.id,
      best,
      score: best.score + (entry.occurrences.length > 1 ? 1 : 0),
      excluded: usable.length === 0 ? entry.occurrences[0].excluded : null,
    };
  });
  const usable = ranked
    .filter((r) => r.excluded === null)
    .sort((a, b) => b.score - a.score || a.best.page - b.best.page);
  const setAside = ranked.filter((r) => r.excluded !== null);

  for (const entry of setAside) {
    notes.push(`${label} ${entry.id} not used: ${entry.excluded}.`);
  }
  if (usable.length === 0) {
    return { id: "", others: setAside.map((r) => r.id), review: setAside.length > 0 };
  }
  const [chosen, ...rest] = usable;
  const how = chosen.best.source === "link" ? "clickable link" : "text";
  notes.push(`${label} ${chosen.id} chosen: ${how} on page ${chosen.best.page + 1}.`);
  const closeCall = rest.length > 0 && chosen.score - rest[0].score < CLOSE_CALL;
  if (closeCall) {
    notes.push(`${label} is a close call: ${rest[0].id} scored almost as high. Check which one is the applicant's.`);
  }
  return { id: chosen.id, others: [...rest, ...setAside].map((r) => r.id), review: closeCall };
}

/** "ORCID" written somewhere with no valid iD right after it. @param {Page[]} pages */
function orcidLabelsWithoutId(pages) {
  /** @type {string[]} */
  const notes = [];
  pages.forEach((page, index) => {
    const text = normalise(page.text);
    for (const match of text.matchAll(/orcid/gi)) {
      const after = text.slice(match.index, match.index + 80);
      if (!/\d{4}-\d{4}-\d{4}-\d{3}[\dX]/i.test(after)) {
        const snippet = after.replace(/\s+/g, " ").trim();
        notes.push(`"ORCID" appears on page ${index + 1} without a usable iD after it: "${snippet}"`);
      }
    }
  });
  return notes;
}

/** @param {Page[]} pages */
function hasText(pages) {
  const chars = pages.reduce((sum, page) => sum + page.text.replace(/\s/g, "").length, 0);
  const links = pages.reduce((sum, page) => sum + page.links.length, 0);
  return chars >= MIN_TEXT_CHARS || links > 0;
}
