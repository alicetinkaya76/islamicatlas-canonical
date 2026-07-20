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

/* H20 S3: pid → kaynak id'leri (Ulema Havuzu'nun ihtiyacı; havuz kayıtları
   yalnız kaynak KODU taşır, id taşımaz). Ters indeks ilk istekte kurulur. */
let BY_PID = null;
export function bridgeByPid(pidNum) {
  if (!BR) return null;
  if (!BY_PID) {
    BY_PID = {};
    for (const [alamId, v] of Object.entries(BR.alam || {})) {
      const n = v.pid && v.pid.replace('iac:person-', '').replace(/^0+/, '');
      if (n) BY_PID[n] = { ...(BY_PID[n] || {}), alam: alamId, dia: v.dia ?? BY_PID[n]?.dia, ei1: v.ei1 ?? BY_PID[n]?.ei1 };
    }
    for (const [slug, v] of Object.entries(BR.dia || {})) {
      const n = v.pid && v.pid.replace('iac:person-', '').replace(/^0+/, '');
      if (n) BY_PID[n] = { ...(BY_PID[n] || {}), dia: slug, alam: v.alam ?? BY_PID[n]?.alam, ei1: v.ei1 ?? BY_PID[n]?.ei1 };
    }
  }
  return BY_PID[String(pidNum)] || null;
}
