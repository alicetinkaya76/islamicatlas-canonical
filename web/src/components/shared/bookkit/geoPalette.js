/**
 * bookkit/geoPalette — coğrafi tip renk/ikon/etiket TEK KAYNAĞI (H17 Dalga-0).
 *
 * Yâkût görünümündeki 4 kopyanın (Map/Sidebar/Analytics/Globe) birleşimi;
 * paylaşılan anahtarlarda değerler bire bir aynıydı, birleşim yalnız
 * Analytics kopyasında eksik olan 'sea' girdisini tamamlar.
 * Kural (bookkit anayasası): bir parça İKİNCİ tüketici isteyince buraya
 * girer; kitaba-özel kalacaksa kendi dosyasında doğar.
 */

export const GEO_COLORS = {
  city:       '#d4a84b', // altın
  village:    '#66bb6a', // yeşil
  mountain:   '#a1887f', // kahverengi
  river:      '#4fc3f7', // mavi
  fortress:   '#ef5350', // kırmızı
  region:     '#ce93d8', // mor
  town:       '#ff8a65', // turuncu
  district:   '#ffb74d', // açık turuncu
  valley:     '#81c784', // açık yeşil
  water:      '#29b6f6', // koyu mavi
  well:       '#4dd0e1', // turkuaz
  monastery:  '#9575cd', // lacivert
  spring:     '#26c6da', // cyan
  pass:       '#8d6e63', // koyu kahve
  island:     '#4db6ac', // teal
  desert:     '#ffd54f', // sarı
  place:      '#90a4ae', // gri
  market:     '#f06292', // pembe
  quarter:    '#78909c', // gri-mavi
  wadi:       '#aed581', // lime
  sea:        '#1565c0', // koyu mavi
};

export const GEO_DEFAULT_COLOR = '#90a4ae';

export const GEO_ICONS = {
  city: '🏙', village: '🏘', mountain: '⛰', river: '🏞', fortress: '🏰',
  region: '📍', town: '🏛', district: '📌', valley: '🌿', water: '💧',
  well: '🕳', monastery: '⛪', spring: '💦', pass: '🛤', island: '🏝',
  desert: '🏜', place: '📍', market: '🏪', quarter: '🏠', wadi: '🌊', sea: '🌊',
};

export const GEO_EN = {
  city: 'City', village: 'Village', mountain: 'Mountain', river: 'River',
  fortress: 'Fortress', region: 'Region', town: 'Town', district: 'District',
  valley: 'Valley', water: 'Water', well: 'Well', monastery: 'Monastery',
  spring: 'Spring', pass: 'Pass', island: 'Island', desert: 'Desert',
  place: 'Place', market: 'Market', quarter: 'Quarter', wadi: 'Wadi', sea: 'Sea',
};

export const GEO_TR = {
  city: 'Şehir', village: 'Köy', mountain: 'Dağ', river: 'Nehir',
  fortress: 'Kale', region: 'Bölge', town: 'Kasaba', district: 'Nahiye',
  valley: 'Vadi', water: 'Su', well: 'Kuyu', monastery: 'Manastır',
  spring: 'Pınar', pass: 'Geçit', island: 'Ada', desert: 'Çöl',
  place: 'Mevki', market: 'Pazar', quarter: 'Mahalle', wadi: 'Kuru Dere', sea: 'Deniz',
};

export const PERIOD_LABEL = {
  active: { tr: 'Aktif', en: 'Active' },
  ruined: { tr: 'Harap', en: 'Ruined' },
  legendary: { tr: 'Efsanevî', en: 'Legendary' },
};

export function geoColor(gt) {
  return GEO_COLORS[gt] || GEO_DEFAULT_COLOR;
}

/* Three.js sayısal renk (Globe) — string paletten türetilir, ayrı kopya tutulmaz. */
export const GEO_COLORS_NUM = Object.fromEntries(
  Object.entries(GEO_COLORS).map(([k, v]) => [k, parseInt(v.slice(1), 16)])
);

export function geoColorNum(gt) {
  return GEO_COLORS_NUM[gt] ?? parseInt(GEO_DEFAULT_COLOR.slice(1), 16);
}
