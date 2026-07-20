/**
 * personBridge — kişi kartlarında kaynak-izi köprüsü (H19 S2, Dalga-2).
 *
 * web/public/books/person_bridge.json (build_person_bridge.py; mağaza
 * pid-merge'lerinden alam↔dia↔ei1 iki yönlü haritalar) tembel yüklenir.
 * Veri yokken tüm sorgular null döner (blok sessizce görünmez).
 * dia-chunks ailesi BİLEREK dışarıda (ayrı kimlik evreni).
 */
let BR = null;
let started = false;

export function ensurePersonBridge() {
  if (started) return;
  started = true;
  const base = import.meta.env.BASE_URL || '/';
  fetch(`${base}books/person_bridge.json`, { cache: 'no-cache' })
    .then((r) => (r.ok ? r.json() : null))
    .then((d) => { BR = d; })
    .catch(() => {});
}

export function bridgeFromAlam(alamId) {
  return (BR && BR.alam && BR.alam[String(alamId)]) || null;
}

export function bridgeFromDia(slug) {
  return (BR && BR.dia && BR.dia[slug]) || null;
}
