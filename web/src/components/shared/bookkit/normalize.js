/**
 * bookkit/normalize — TR + akademik transliterasyon + Arapça varyant
 * normalizasyonu (H17 Dalga-0; YaqutView'dan çıkarıldı, davranış aynı).
 *
 * Kapsam: TR harfleri (ı/ğ/ü/ş/ö/ç), şapkalı/uzun ünlüler, DMG
 * diyakritikleri (ḥ/ṣ/ṭ/ḍ/ẓ), ayn/hemze işaretleri, Arapça hareke
 * aralığı (U+0610–065F, U+0670 — rakam bloğu 0660-066F BİLEREK dışarıda),
 * ة→ه, ى→ي, hemzeli elifler→ا.
 */
export const normalize = (s) =>
  (s || '').toLowerCase()
    .replace(/ı/g, 'i').replace(/ğ/g, 'g').replace(/ü/g, 'u')
    .replace(/ş/g, 's').replace(/ö/g, 'o').replace(/ç/g, 'c')
    .replace(/â/g, 'a').replace(/î/g, 'i').replace(/û/g, 'u')
    .replace(/[āáà]/g, 'a').replace(/[ūú]/g, 'u').replace(/[īíì]/g, 'i')
    .replace(/[ḥḫ]/g, 'h').replace(/ṣ/g, 's').replace(/ṭ/g, 't')
    .replace(/ḍ/g, 'd').replace(/ẓ/g, 'z').replace(/ʿ|ʾ|'/g, '')
    .normalize('NFKD').replace(/[\u0300-\u036F]/g, '')   // İ→i+U+0307 dahil birleşik diyakritikler
    .replace(/[\u0610-\u061A\u064B-\u065F\u0670]/g, '')   // YALNIZ harekeler (harf bloğu DIŞARIDA)
    .replace(/\u0640/g, '')                                   // tatvîl (ـ) aramada gürültü
    .replace(/ة/g, 'ه').replace(/ى/g, 'ي').replace(/[أإآ]/g, 'ا');

export default normalize;
