export interface Governorate {
  fr: string;
  ar: string;
  lat: number;
  lon: number;
}

// Source: hassen/coordonnees_gouvernorats_tunisie-1.xlsx
export const GOVERNORATES: Governorate[] = [
  { fr: 'Ariana', ar: 'أريانة', lat: 36.8625, lon: 10.1956 },
  { fr: 'Béja', ar: 'باجة', lat: 36.7333, lon: 9.1833 },
  { fr: 'Ben Arous', ar: 'بن عروس', lat: 36.6436, lon: 10.2152 },
  { fr: 'Bizerte', ar: 'بنزرت', lat: 37.29, lon: 9.87 },
  { fr: 'Gabès', ar: 'قابس', lat: 33.9, lon: 10.1 },
  { fr: 'Gafsa', ar: 'قفصة', lat: 34.3789, lon: 8.6601 },
  { fr: 'Jendouba', ar: 'جندوبة', lat: 36.5005, lon: 8.7807 },
  { fr: 'Kairouan', ar: 'القيروان', lat: 35.6712, lon: 10.1005 },
  { fr: 'Kasserine', ar: 'القصرين', lat: 35.0809, lon: 8.6601 },
  { fr: 'Kébili', ar: 'قبلي', lat: 33.7072, lon: 8.9715 },
  { fr: 'Le Kef', ar: 'الكاف', lat: 36.1231, lon: 8.6601 },
  { fr: 'Mahdia', ar: 'المهدية', lat: 35.3353, lon: 10.8903 },
  { fr: 'La Manouba', ar: 'منوبة', lat: 36.8447, lon: 9.8571 },
  { fr: 'Médenine', ar: 'مدنين', lat: 33.2281, lon: 10.8903 },
  { fr: 'Monastir', ar: 'المنستير', lat: 35.7643, lon: 10.8113 },
  { fr: 'Nabeul', ar: 'نابل', lat: 36.46, lon: 10.73 },
  { fr: 'Sfax', ar: 'صفاقس', lat: 34.8607, lon: 10.3498 },
  { fr: 'Sidi Bouzid', ar: 'سيدي بوزيد', lat: 35.04, lon: 9.5 },
  { fr: 'Siliana', ar: 'سليانة', lat: 36.0887, lon: 9.3645 },
  { fr: 'Sousse', ar: 'سوسة', lat: 35.8371, lon: 10.6347 },
  { fr: 'Tataouine', ar: 'تطاوين', lat: 32.93, lon: 10.45 },
  { fr: 'Tozeur', ar: 'توزر', lat: 33.93, lon: 8.13 },
  { fr: 'Tunis', ar: 'تونس', lat: 36.8375, lon: 10.1927 },
  { fr: 'Zaghouan', ar: 'زغوان', lat: 36.4091, lon: 10.1423 },
];

export const UNMATCHED_LABEL = 'غير محدد';

// Informal Arabic text often swaps the ة/ه ending (e.g. "منوبه" for "منوبة") —
// normalize both sides to ه before comparing so those variants still match.
const normalize = (s: string) => s.replace(/ة/g, 'ه');

/** Best-effort match of a free-text location string against a governorate name. */
export function matchGovernorate(...texts: Array<string | null | undefined>): Governorate | null {
  for (const text of texts) {
    if (!text) continue;
    const haystack = normalize(text);
    const found = GOVERNORATES.find((g) => haystack.includes(normalize(g.ar)));
    if (found) return found;
  }
  return null;
}
