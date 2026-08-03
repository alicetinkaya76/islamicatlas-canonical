/**
 * bookkit — kitap/kaynak görünümlerinin ortak parça kutusu (H17 Dalga-0).
 *
 * Anayasa: bir parça ancak İKİNCİ tüketici de isteyince buraya terfi eder;
 * ilk kullanımda kitaba-özel dosyasında doğar. Buradaki her parça
 * piksel-parite kapısından geçerek geldi (kaynağı: Yâkût görünümü).
 */
export { GEO_COLORS, GEO_ICONS, GEO_EN, GEO_TR, PERIOD_LABEL, GEO_DEFAULT_COLOR, GEO_COLORS_NUM, geoColor, geoColorNum } from './geoPalette';
export { default as VirtualList } from './VirtualList';
export { normalize } from './normalize';
export { default as ErrorBoundary } from './ErrorBoundary';
export { openitiRepoUrl } from './openiti';
