const DIACRITICS = /[ً-ٰٟ]/g;

export function stripDiacritics(s: string): string {
  return s.replace(DIACRITICS, '');
}

function normalizeArabic(s: string): string {
  return stripDiacritics(s)
    .replace(/[إأآا]/g, 'ا')
    .replace(/ى/g, 'ي')
    .replace(/ة/g, 'ه')
    .replace(/\s+/g, ' ')
    .trim();
}

function levenshtein(a: string, b: string): number {
  const dp: number[][] = Array.from({ length: a.length + 1 }, () => new Array(b.length + 1).fill(0));
  for (let i = 0; i <= a.length; i++) dp[i][0] = i;
  for (let j = 0; j <= b.length; j++) dp[0][j] = j;
  for (let i = 1; i <= a.length; i++) {
    for (let j = 1; j <= b.length; j++) {
      dp[i][j] =
        a[i - 1] === b[j - 1] ? dp[i - 1][j - 1] : 1 + Math.min(dp[i - 1][j - 1], dp[i - 1][j], dp[i][j - 1]);
    }
  }
  return dp[a.length][b.length];
}

/**
 * Same category once diacritics/letter variants are normalized and up to one
 * typo'd character is tolerated — e.g. "حرج", "حريج" and "حَرْج" all match.
 * The length-3 floor keeps short, genuinely different words from colliding.
 */
export function isSameCategory(a: string, b: string): boolean {
  const na = normalizeArabic(a);
  const nb = normalizeArabic(b);
  if (na === nb) return true;
  return Math.min(na.length, nb.length) >= 3 && levenshtein(na, nb) <= 1;
}

/** True if `needle` fuzzily occurs as a whole word or substring inside `haystack`. */
export function fuzzyIncludes(haystack: string, needle: string): boolean {
  const h = normalizeArabic(haystack);
  const n = normalizeArabic(needle);
  if (h.includes(n)) return true;
  return h.split(' ').some((word) => isSameCategory(word, n));
}

/** Same result as `levenshtein(a, b) <= 1`, in one pass and without allocating a matrix. */
function withinOneEdit(a: string, b: string): boolean {
  if (a === b) return true;
  if (Math.abs(a.length - b.length) > 1) return false;
  if (a.length < b.length) return withinOneEdit(b, a);
  let i = 0;
  let j = 0;
  let edits = 0;
  while (i < a.length && j < b.length) {
    if (a[i] === b[j]) {
      i++;
      j++;
      continue;
    }
    if (++edits > 1) return false;
    if (a.length === b.length) j++; // substitution
    i++; // deletion from the longer string
  }
  return edits + (a.length - i) <= 1;
}

/**
 * Counts free-text values, merging near-duplicate spellings into one bucket
 * (same rule as isSameCategory). The most frequent exact spelling in a bucket
 * is used as its display label.
 *
 * Identical spellings are counted first and each distinct spelling is
 * normalized once: comparing every occurrence against every spelling with
 * isSameCategory took ~19 s on the ~14k keywords of the traffic dataset and
 * froze the dashboard on load and whenever the filters were cleared.
 */
export function countGrouped(values: string[]): [string, number][] {
  const exact = new Map<string, number>();
  for (const v of values) exact.set(v, (exact.get(v) ?? 0) + 1);

  const buckets: { spellings: Map<string, number>; normalized: string[] }[] = [];
  for (const [raw, count] of exact) {
    const n = normalizeArabic(raw);
    const bucket = buckets.find((b) =>
      b.normalized.some((m) => m === n || (Math.min(m.length, n.length) >= 3 && withinOneEdit(m, n))),
    );
    if (bucket) {
      bucket.spellings.set(raw, count);
      bucket.normalized.push(n);
    } else {
      buckets.push({ spellings: new Map([[raw, count]]), normalized: [n] });
    }
  }

  return buckets
    .map((b): [string, number] => {
      const total = [...b.spellings.values()].reduce((sum, c) => sum + c, 0);
      const [label] = [...b.spellings.entries()].sort((x, y) => y[1] - x[1])[0];
      return [label, total];
    })
    .sort((a, b) => b[1] - a[1]);
}
