/**
 * dynastyHonesty — hanedan verisinin İDDİA ETTİĞİ ile ÖLÇTÜĞÜ arasındaki farkı
 * ekranda görünür kılar (H56).
 *
 * Denetim üç ayrı uydurma-sınıfı kusur ölçtü ve üçü de aynı kalıptaydı:
 * *veri bir şey bilmiyor, ekran biliyormuş gibi çiziyor.*
 *
 *   1) YIL ARALIĞI. 186 hanedanın 9'unda aralık imkânsız (Eyyûbîler
 *      "1169 – 15", Hârizmşahlar "7 – 1231"; İslam takvimi 622'de başlar).
 *      Popup ve arama bunu ÇIPLAK basıyordu. Dördü ayrıca haritada hiçbir
 *      yılda çizilmiyor — sebebi bir filtre kararı değil, bozuk veri.
 *      Ayrıca 7 hanedanda `end = 2025` bir NÖBETÇİ değerdir; canonical
 *      karşılıklarının `end_ce` alanı null (yani "devam ediyor").
 *
 *   2) YAYILIM DİKDÖRTGENİ. 186 hanedanın 185'inde gerçek sınır kutusu
 *      (bn/bs/bw/be) YOK; dikdörtgen `başkent ± sabit derece` ile
 *      üretiliyor ve yarıçap editöryel bir "önem" etiketinden geliyor
 *      (Kritik 8°, Yüksek 5°, Normal 3°, aksi 1,5°). Ekranda ölçülmüş bir
 *      sınır gibi duruyordu.
 *
 *   3) HÜKÜMDAR KONUMU. 830 hükümdarın 830'u kendi hanedanının başkent
 *      koordinatına kopyalanmış; 830 nokta haritada 133 noktaya çakışıyor.
 *      Popup "bu hükümdar buradaydı" izlenimi veriyordu.
 *
 * DOKTRİN: hiçbirinde doğru değer TAHMİN EDİLMEZ. Tutarsız yıllar
 * `data/review_queue/dynasty_temporal.jsonl` üzerinden insan kuyruğuna
 * gider (build_dynasty_temporal_flags.py).
 *
 * Bayrak dosyası yoksa (temiz kopya, üretici koşmamış) her şey eskisi gibi
 * davranır — yalnız dürüstlük katmanı sessizce yok olur.
 */

let FLAGS = null;
let started = false;

let FACETS = null;
/* Popup HTML'i STATİK bir dize olarak kuruluyor; veri sonradan gelirse blok
   hiç basılmaz. Ölçüldü: temiz yüklemede `.p-canon` yoktu, ancak katman
   yeniden çizilince çıkıyordu. Abonelik, veri indiğinde bir kez yeniden
   çizim tetikler. (Aynı gecikme `ensurePlaceIndex` için de geçerli — orası
   ayrı bir tur.) */
const aboneler = new Set();
function haberVer() { aboneler.forEach((f) => { try { f(); } catch { /* yut */ } }); }

/** Veri indiğinde bir kez çağrılır; aboneliği bırakan fonksiyon döner. */
export function onDynastyDataReady(cb) {
  aboneler.add(cb);
  if (FLAGS && FACETS) cb();          // zaten indiyse hemen
  return () => aboneler.delete(cb);
}

export function ensureDynastyFlags() {
  if (started) return;
  started = true;
  const base = import.meta.env.BASE_URL || '/';
  fetch(`${base}view-data/dynasty_temporal_flags.json`, { cache: 'no-cache' })
    .then((r) => (r.ok ? r.json() : null))
    .then((d) => { FLAGS = (d && d.flags) || {}; })
    .catch(() => { FLAGS = {}; })
    .finally(haberVer);
  /* H57: canonical'ın v1'e EKLEDİĞİ bağlar (ardıllık, başkent yeri, himaye).
     Denetim ölçtü: canonical dynasty namespace'inin hiçbir alanı arayüze
     çıkmıyordu — `grep web/src` bosworth_id/had_capital/had_ruler/
     patron_dynasty için SIFIR isabet. 18 KB, popup'la aynı anda gelir. */
  fetch(`${base}view-data/dynasty_facets.json`, { cache: 'no-cache' })
    .then((r) => (r.ok ? r.json() : null))
    .then((d) => { FACETS = (d && d.facets) || {}; })
    .catch(() => { FACETS = {}; })
    .finally(haberVer);
}

/** v1 hanedan id'si → canonical'ın eklediği bağlar (yoksa null). */
export function dynastyFacets(id) {
  if (!FACETS) return null;
  return FACETS[String(id)] || null;
}

export const FACET_LABEL = {
  onc: { tr: 'Öncülü', en: 'Preceded by', ar: 'سبقتها' },
  ard: { tr: 'Ardılı', en: 'Succeeded by', ar: 'تلتها' },
  bkt: { tr: 'Başkent kaydı', en: 'Capital record', ar: 'سجل العاصمة' },
  kurum: { tr: 'Himayesindeki yapı', en: 'Patronised structures', ar: 'المنشآت تحت رعايتها' },
  /* Çözüm birden çok aday arasından İNSAN ONAYI OLMADAN yapıldıysa söylenir:
     129 başkent girdisinin 64'ü böyle. Düz bir bağ gibi göstermek, bu
     depoda tekrar tekrar onarılan "sessiz kesinlik" kalıbı olurdu. */
  belirsiz: { tr: 'aday arasından seçildi, onaylanmadı',
              en: 'picked among candidates, unconfirmed',
              ar: 'اختير من بين مرشحين، غير مؤكد' },
};

/** Bayrağı olmayan id 'saglam' demektir (üretici yalnız sapmaları yazar). */
export function dynastyTemporalFlag(id) {
  if (!FLAGS) return null;
  return FLAGS[String(id)] || null;
}

const METIN = {
  devam: { tr: 'devam ediyor', en: 'ongoing', ar: 'مستمرة' },
  tutarsiz: { tr: 'kaynakta tutarsız', en: 'inconsistent in source', ar: 'غير متسق في المصدر' },
};

/**
 * Popup/arama için yıl aralığı metni.
 *
 * - saglam   → "1169 – 1250"
 * - devam    → "1735 – devam ediyor"   (nöbetçi 2025 basılmaz)
 * - tutarsiz → "kaynakta tutarsız (1169 – 15)"
 *
 * Tutarsız olanda ham değer PARANTEZ İÇİNDE kalır: veriyi saklamak da bir
 * tür sahtelik olurdu — kullanıcı kaynağın ne dediğini görebilmeli, ama
 * bunun bir tarih iddiası olmadığını da bilmeli.
 */
export function dynastyYearRange(d, lang = 'tr') {
  const dil = METIN.devam[lang] ? lang : 'tr';
  const f = dynastyTemporalFlag(d && d.id);
  const s = d ? d.start : null;
  const e = d ? d.end : null;
  if (!f) return `${s} – ${e}`;
  if (f.d === 'devam') return `${s} – ${METIN.devam[dil]}`;
  return `${METIN.tutarsiz[dil]} (${s} – ${e})`;
}

/** Bu hanedan bozuk yıl yüzünden haritada hiç çizilmiyor mu? */
export function dynastyNeverDrawn(id) {
  const f = dynastyTemporalFlag(id);
  return !!(f && f.h);
}

/* ── Yayılım dikdörtgeni ────────────────────────────────────────────────── */

/** Gerçek sınır kutusu var mı? 186 hanedanın YALNIZ 1'inde var (Endülüs). */
export function hasMeasuredExtent(d) {
  return !!(d && d.bn && d.bs && d.bw && d.be);
}

export const EXTENT_NOTE = {
  tr: 'Şematik yayılım — ölçülmüş sınır değil; başkent çevresinde temsilî alan.',
  en: 'Schematic extent — not a measured boundary; indicative area around the capital.',
  ar: 'امتداد تخطيطي — ليس حدًا مقيسًا؛ منطقة إرشادية حول العاصمة.',
};

/* ── Hükümdar konumu ────────────────────────────────────────────────────── */

/** Hükümdarın noktası hanedanın başkentinden mi devralındı? */
export function rulerCoordInherited(r, dynasty) {
  if (!r || !dynasty) return false;
  return r.lat === dynasty.lat && r.lon === dynasty.lon;
}

export const RULER_COORD_NOTE = {
  tr: 'Konum hanedanın başkentinden devralındı — hükümdara özgü bir yer kaydı yok.',
  en: 'Location inherited from the dynasty capital — no ruler-specific place record.',
  ar: 'الموقع موروث من عاصمة الأسرة — لا يوجد سجل مكان خاص بالحاكم.',
};
