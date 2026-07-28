/**
 * navRegistry.js — H33: navigasyonun TEK DEKLARATİF KAYNAĞI.
 *
 * SORUN (H27 denetimi, 1 numaralı öneri): aynı sekme listesi BEŞ ayrı yerde
 * tekrarlanıyordu — VALID_TABS, SWIPE_TAB_ORDER, masaüstü "Kaynaklar/Analiz"
 * açılırları, mobil çekmece, BottomTabBar. Yeni bir görünüm eklemek ~8 dokunuş
 * istiyordu ve biri unutulunca SESSİZ kırılıyordu (ölçüldü: #visits mobilde
 * hiç erişilemiyordu; drawer ile BottomTabBar khitat/cityatlas'ta anlaşmıyordu).
 *
 * ÇÖZÜM: her sekme BURADA bir kez tanımlanır; tüm navlar bundan TÜRETİLİR.
 *
 * ALAN SÖZLEŞMESİ
 *   id       : hash rotası ve render anahtarı (#<id>)
 *   icon     : yapısal ikon (BottomTabBar bunu ayrı alan olarak ister)
 *   label    : {tr,en,ar} — i18n `t.tabs[id]` varsa O ÖNCELİKLİDİR, bu yedektir
 *   group    : 'primary' (üst düz buton) | 'source' (v1 kaynak görünümleri)
 *              | 'unified' (v2 birleşik görünümler) | 'analysis' | 'utility'
 *   navs     : hangi navlarda görünür — 'top' | 'dropdown' | 'drawer'
 *              | 'bottom' | 'bottomPrimary' | 'swipe'
 *   preload  : üzerine gelince ön-yüklenecek veri (varsa)
 *   countKey : rozet sayısı için sourceCounts anahtarı (varsa)
 *
 * NOT: render dispatch (App.jsx ternary zinciri) bu turda BİLEREK dokunulmadı —
 * 45 dallı, ayrı ve riskli bir iş. Guard test (test_nav_registry_contract)
 * registry ↔ dispatch tutarlılığını kilitler.
 */

const NAV_ITEMS = [
  /* ── Üst düz butonlar ───────────────────────────────────────────── */
  { id: 'map', icon: '🗺️', group: 'primary', navs: ['top', 'drawer', 'bottomPrimary', 'swipe'],
    label: { tr: '🗺 Harita', en: '🗺 Map', ar: '🗺 خريطة' } },
  { id: 'dashboard', icon: '📊', group: 'primary', navs: ['top', 'drawer', 'bottomPrimary', 'swipe'],
    label: { tr: '📊 Pano', en: '📊 Dashboard', ar: '📊 لوحة' } },
  { id: 'library', icon: '📖', group: 'primary', navs: ['top', 'drawer', 'bottom'], countKey: 'library',
    label: { tr: '📖 Kütüphane', en: '📖 Library', ar: '📖 المكتبة' } },

  /* ── Kaynaklar ▾ : v1 kaynak görünümleri ────────────────────────── */
  { id: 'alam', icon: '📖', group: 'source', navs: ['dropdown', 'drawer', 'bottomPrimary', 'swipe'],
    countKey: 'alam', preload: '/data/alam_lite.json',
    label: { tr: "📖 el-A'lâm", en: '📖 al-Aʿlām', ar: '📖 الأعلام' } },
  { id: 'dia', icon: '📚', group: 'source', navs: ['dropdown', 'drawer', 'bottomPrimary', 'swipe'],
    countKey: 'dia', preload: '/data/dia_lite.json',
    label: { tr: '📚 DİA', en: '📚 TDV İA', ar: '📚 موسوعة' } },
  { id: 'ei1', icon: '📕', group: 'source', navs: ['dropdown', 'drawer', 'bottom', 'swipe'],
    countKey: 'ei1', preload: '/data/ei1_lite.json',
    label: { tr: '📕 EI-1', en: '📕 EI-1', ar: '📕 دائرة المعارف' } },
  { id: 'yaqut', icon: '🌍', group: 'source', navs: ['dropdown', 'drawer', 'bottom', 'swipe'],
    countKey: 'yaqut', preload: '/data/yaqut_lite.json',
    label: { tr: "🌍 Mu'cemü'l-Büldân", en: '🌍 Muʿjam al-Buldān', ar: '🌍 معجم البلدان' },
    curated: { ar: 'معجم البلدان', by: 'Yâkût el-Hamevî', caps: '🗺 🌍 📊 🕸', name: { tr: "Mu'cemü'l-Büldân", en: "Muʿjam al-Buldān" } } },
  { id: 'rihla', icon: '🧭', group: 'source', navs: ['dropdown', 'drawer', 'bottom', 'swipe'],
    countKey: 'rihla', preload: '/data/ibn_battuta_atlas_layer.json',
    label: { tr: '🧭 İbn Battûta', en: '🧭 Ibn Battuta', ar: '🧭 ابن بطوطة' },
    curated: { ar: 'الرحلة', by: 'İbn Battûta', caps: '🛤 🗺', name: { tr: "Rihle", en: "Riḥla" } } },
  { id: 'khitat', icon: '🏛️', group: 'source', navs: ['dropdown', 'drawer', 'bottom', 'swipe'],
    countKey: 'khitat', preload: '/data/maqrizi_khitat_atlas_layer.json',
    label: { tr: '🏛️ el-Hıṭaṭ', en: '🏛️ al-Khiṭaṭ', ar: '🏛️ الخطط' },
    curated: { ar: 'الخطط', by: 'Makrîzî', caps: '🏛 🗺', name: { tr: "el-Hıtat", en: "al-Khiṭaṭ" } } },
  { id: 'lestrange', icon: '🗺️', group: 'source', navs: ['dropdown', 'drawer', 'bottom', 'swipe'],
    countKey: 'lestrange', preload: '/data/le_strange_eastern_caliphate.json',
    label: { tr: '🗺️ Le Strange', en: '🗺️ Le Strange', ar: '🗺️ لي سترينج' },
    curated: { ar: '', by: 'G. Le Strange', caps: '🗺 🔗', name: { tr: "Lands of the Eastern Caliphate", en: "Lands of the Eastern Caliphate" } } },
  { id: 'darpislam', icon: '🪙', group: 'source', navs: ['dropdown', 'drawer', 'bottom'],
    countKey: 'darpislam', preload: '/data/darpislam_lite.json',
    label: { tr: '🪙 Darphaneler', en: '🪙 Mints', ar: '🪙 دور السك' } },
  { id: 'science', icon: '🔬', group: 'source', navs: ['dropdown', 'drawer', 'bottom'],
    countKey: 'science', preload: '/data/science_layer.json',
    label: { tr: '🔬 Bilim Atlası', en: '🔬 Science Atlas', ar: '🔬 أطلس العلوم' } },
  { id: 'salibiyyat', icon: '⚔️', group: 'source', navs: ['dropdown', 'drawer', 'bottom', 'swipe'],
    countKey: 'salibiyyat', preload: '/data/salibiyyat_atlas_layer.json',
    label: { tr: '⚔️ Salibiyyât', en: '⚔️ Crusades', ar: '⚔️ صليبيات' },
    curated: { ar: '', by: 'Müslüman kronikçiler', caps: '⚔️ 🕰 🕸', name: { tr: "Salibiyyât (6 kronik)", en: "Crusades (6 chronicles)" } } },
  { id: 'evliya', icon: '🐫', group: 'source', navs: ['dropdown', 'drawer', 'bottom'],
    countKey: 'evliya', preload: '/data/evliya_atlas_layer.json',
    label: { tr: '🐫 Evliyâ Çelebi', en: '🐫 Evliya Çelebi', ar: '🐫 أوليا جلبي' },
    curated: { ar: 'سياحتنامه', by: 'Evliyâ Çelebi', caps: '🛤 🗺 🕰', name: { tr: "Seyahatnâme", en: "Seyahatnâme" } } },
  { id: 'muqaddasi', icon: '📐', group: 'source', navs: ['dropdown', 'drawer', 'bottom'],
    countKey: 'muqaddasi', preload: '/data/muqaddasi_atlas_layer.json',
    label: { tr: '📐 Makdisî', en: '📐 al-Muqaddasī', ar: '📐 المقدسي' },
    curated: { ar: 'أحسن التقاسيم', by: 'Makdisî', caps: '🗺 🛤 📐', name: { tr: "Ahsenü't-Tekāsîm", en: "Aḥsan al-Taqāsīm" } } },

  /* ── Kaynaklar ▾ : v2 birleşik görünümler ───────────────────────── */
  { id: 'cityatlas', icon: '🏙️', group: 'unified', navs: ['dropdown', 'drawer', 'bottom'],
    countKey: 'cityatlas', preload: '/data/city-atlas/konya.json',
    label: { tr: '🏙️ Şehir Atlası', en: '🏙️ City Atlas', ar: '🏙️ أطلس المدن' } },
  { id: 'visits', icon: '🧭', group: 'unified', navs: ['dropdown', 'drawer', 'bottom'],
    label: { tr: '🧭 Seyahatnâmeler', en: '🧭 Travel Accounts', ar: '🧭 الرحلات' } },

  /* ── Analiz ▾ ───────────────────────────────────────────────────── */
  { id: 'timeline', icon: '📅', group: 'analysis', navs: ['dropdown', 'drawer', 'bottom'],
    label: { tr: '📅 Zaman Çizelgesi', en: '📅 Timeline', ar: '📅 الجدول الزمني' } },
  { id: 'links', icon: '🔗', group: 'analysis', navs: ['dropdown', 'drawer', 'bottom'],
    label: { tr: '🔗 Nedensellik', en: '🔗 Causality', ar: '🔗 السببية' } },
  { id: 'scholars', icon: '🎓', group: 'analysis', navs: ['dropdown', 'drawer', 'bottom', 'swipe'],
    label: { tr: '🎓 Âlimler', en: '🎓 Scholars', ar: '🎓 العلماء' } },
  { id: 'battles', icon: '⚔️', group: 'analysis', navs: ['dropdown', 'drawer', 'bottom'],
    countKey: 'battles',
    label: { tr: '⚔️ Savaşlar', en: '⚔️ Battles', ar: '⚔️ المعارك' } },

  /* ── Yardımcı (navlarda ayrı düğmesi var) ───────────────────────── */
  { id: 'admin', icon: '⚙', group: 'utility', navs: [],
    label: { tr: '⚙ Yönetim', en: '⚙ Admin', ar: '⚙ الإدارة' } },
];

/** Bir navda görünen öğeler, kayıt sırasında. */
export function itemsFor(nav) {
  return NAV_ITEMS.filter((it) => it.navs.includes(nav));
}

/** Belirli grup(lar)daki öğeler — açılır menüleri kurmak için. */
export function itemsInGroup(...groups) {
  return NAV_ITEMS.filter((it) => groups.includes(it.group));
}

/** Etiket: i18n sözlüğü (t.tabs) öncelikli, yoksa kayıttaki yedek. */
export function navLabel(item, t, lang) {
  const fromI18n = t?.tabs?.[item.id];
  if (typeof fromI18n === 'string' && fromI18n.trim()) return fromI18n;
  return item.label?.[lang] || item.label?.tr || item.id;
}

/** Kütüphane rafındaki 'Kürasyonlu Atlas Görünümleri' — eser-türevi v1 görünümleri. */
export function curatedItems() {
  return NAV_ITEMS.filter((it) => it.curated);
}

export const VALID_TAB_IDS = NAV_ITEMS.map((i) => i.id);

/* Kaydırma sırası KASITLIDIR (kayıt sırasından türetilmez) — v1'deki mevcut
   dizilim korunur. Registry'de olmayan id sessizce süzülür, böylece iki kaynak
   birbirinden ayrışamaz. */
const SWIPE_SEQUENCE = [
  'map', 'dashboard', 'alam', 'dia', 'ei1', 'scholars',
  'rihla', 'yaqut', 'lestrange', 'khitat', 'salibiyyat',
];
export const SWIPE_ORDER = SWIPE_SEQUENCE.filter((id) => VALID_TAB_IDS.includes(id));

export default NAV_ITEMS;
