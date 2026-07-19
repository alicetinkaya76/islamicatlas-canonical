/**
 * placeBooks — "bu yeri kitaplarda oku" köprüsü (H18 S2, Dalga-1).
 *
 * web/public/books/place_index.json (build_place_index.py; 17 kitap,
 * pid→kitap listesi + tekil norm-ad→pid 'names' haritası) tembel yüklenir.
 * Şehir popup'ı içerik-fonksiyonu olduğundan veri geldikten sonraki her
 * açılışta blok görünür; veri yokken blok sessizce boş kalır (uydurma yok).
 *
 * Ad eşleme: BİREBİR (fuzzy yok) — üreticideki norm_ar ile aynı
 * normalizasyon (hareke+tatvil temizliği, أإآ→ا, ى→ي; ة→ه YAPILMAZ).
 */
let IDX = null;
let started = false;

export function ensurePlaceIndex() {
  if (started) return;
  started = true;
  const base = import.meta.env.BASE_URL || '/';
  /* no-cache: indeks her yeniden üretimde değişir; tarayıcı 304 ile
     doğrulasın (bayat 1.6MB kopya canlıda yakalandı — H18). */
  fetch(`${base}books/place_index.json`, { cache: 'no-cache' })
    .then((r) => (r.ok ? r.json() : null))
    .then((d) => { IDX = d; })
    .catch(() => {});
}

const normAr = (s) => (s || '')
  .replace(/[ؐ-ٰٟـ]/g, '')
  .replace(/أ|إ|آ/g, 'ا')
  .replace(/ى/g, 'ي')
  .trim();

/* Şehir kaydının Arapça adından kitap listesi (en çok anılan ilk 3). */
export function booksForPlaceName(arName) {
  if (!IDX || !arName) return [];
  const pid = IDX.names[normAr(arName)];
  if (!pid) return [];
  return IDX.places[pid] || [];
}

export function booksBlockHtml(arName, lang) {
  const entries = booksForPlaceName(arName).slice(0, 3);
  if (!entries.length) return '';
  const title = { tr: 'Bu yeri kitaplarda oku', en: 'Read this place in the books', ar: 'اقرأ هذا المكان في الكتب' }[lang] || 'Bu yeri kitaplarda oku';
  const rows = entries.map((e) =>
    `<a href="#library?book=${e.pidnum}&sec=${(e.secs && e.secs[0]) ?? 0}"
        style="display:block;padding:2px 0;color:#c9a84c;text-decoration:none;font-size:12px">
       📖 ${e.book} <span style="opacity:.7">· ${e.total.toLocaleString('tr-TR')} ${{ tr: 'anılma', en: 'mentions', ar: 'ذكر' }[lang] || 'anılma'}</span>
     </a>`).join('');
  return `<div class="p-row" style="flex-direction:column;align-items:flex-start;border-top:1px solid rgba(201,168,76,.25);margin-top:6px;padding-top:6px">
    <span class="p-k">📚 ${title}</span><div>${rows}</div></div>`;
}
