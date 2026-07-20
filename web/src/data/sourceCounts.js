/**
 * sourceCounts — kaynak rozetlerinin TEK sayı kaynağı (H17 S3, Dalga-0).
 *
 * Sayılar elle YAZILMAZ: pipelines/frontend/build_source_counts.py gerçek
 * veri dosyalarını sayar → source_counts.json; UI yalnız buradan okur.
 * (Elle rozet dönemi: Şehir Atlası '1,020' yazıyordu, gerçek 1.384;
 * Bilim '186' yazıyordu, gerçek 182.)
 */
import RAW from './source_counts.json';

export const SOURCE_COUNTS = Object.fromEntries(
  Object.entries(RAW.sources).map(([k, v]) => [k, v.count])
);

export const SOURCE_DETAILS = Object.fromEntries(
  Object.entries(RAW.sources).map(([k, v]) => [k, v.detail || {}])
);

/* Rozet biçimi: tam sayı, TR ayracıyla (12.954) — kısaltma yok, kesinlik
   evin ilkesi. Sayı yoksa (missing) tire. */
export function fmtCount(key) {
  const n = SOURCE_COUNTS[key];
  return typeof n === 'number' ? n.toLocaleString('tr-TR') : '—';
}
