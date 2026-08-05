/**
 * battleOutcome — savaş sonucunun TEK OTORİTESİ (H56).
 *
 * DENETİM BULGUSU: aynı `getOutcomeType` fonksiyonu ÜÇ dosyada kopyalanmıştı
 * (BattleView, BattleSidebar, BattleCard) ve üçünün de son satırı
 * `return 'win'` idi — yani sonuç metni YOKKEN varsayılan "zafer".
 *
 * ÖLÇÜLDÜ: 100 savaşın 39'unda `out_en` boş (battle_meta 65 savaşı kapsıyor).
 * Ekrandaki 82 "✓ zafer" rozetinin 39'u (%48) veriden değil, varsayılandan
 * geliyordu. İkisi doğrudan tarihsel olarak yanlıştı:
 *
 *   • Tarain Savaşı (Birinci, 1191) — Gurluların YENİLGİSİ, ekranda ✓
 *   • Belgrad Muhasarası (1456)     — Osmanlı YENİLGİSİ, ekranda ✓
 *
 * Yani varsayılan yalnız "bilgisizliği gizlemiyordu", aktif olarak yanlış
 * tarih anlatıyordu.
 *
 * DÜZELTME: veri yoksa `'unknown'`. Rozet basılmaz, filtre sayısı şişmez.
 * Doğru sonucu TAHMİN ETMİYORUZ — 39 savaşın sonucu `battle_meta.js`
 * genişletilerek kaynakla doldurulmalı.
 */

/* Müslüman taraf için bilinen yenilgi kalıpları (v1'den olduğu gibi alındı;
   davranış değişmedi — değişen YALNIZ varsayılan). */
const YENILGI = [
  'frankish victory', 'crusader victory', 'holy league victory',
  'mongol victory', 'spanish victory', 'british victory',
  'qara khitai victory', 'timurid victory', 'partial defeat',
  'umayyad victory', 'tactical withdrawal',
];

/**
 * @returns {'win'|'loss'|'draw'|'unknown'} — 'unknown' = kaynakta sonuç yok
 */
export function getOutcomeType(b) {
  const out = ((b && b.out_en) || '').toLowerCase().trim();
  if (!out) return 'unknown';        // ← H56: eskiden 'win' idi
  if (out.includes('inconclusive') || out.includes('arbitration')) return 'draw';
  if (YENILGI.some((x) => out.includes(x))) return 'loss';
  return 'win';
}

/** Rozet simgesi; sonucu bilinmeyen savaşta rozet HİÇ basılmaz (null). */
export function outcomeMark(ot) {
  return ot === 'win' ? '✓' : ot === 'loss' ? '✗' : ot === 'draw' ? '~' : null;
}

export const OUTCOME_UNKNOWN_LABEL = {
  tr: 'sonuç kaynakta yok',
  en: 'outcome not in source',
  ar: 'النتيجة غير مذكورة في المصدر',
};

export default getOutcomeType;
