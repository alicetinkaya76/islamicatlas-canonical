/**
 * CanonicalLayer.jsx — H26: ana haritaya OPSİYONEL canonical olay katmanı.
 *
 * Ana #map v1'in db.json'ından beslenir (100 savaş + 200 olay). Bu katman,
 * canonical mağazadaki kitap-türevi olayları (yer başına toplanmış) EK overlay
 * olarak getirir — v1 render'ına DOKUNMADAN. Varsayılan kapalı; toggle ile
 * açılır. Ayırt edici renk (camgöbeği) = "canonical katman".
 *
 * Veri: /view-data/canonical_events.json (build_canonical_map_layer.py üretir).
 * DÜRÜSTLÜK: koordinat olayın değil, işaret ettiği canonical PLACE'in
 * (gazetteer) — popup bunu "yer" olarak sunar, olayı o yere yığar.
 *
 * ── H56 DENETİMİ: burada iki kusur ölçüldü ve onarıldı ───────────────────
 *
 *  1) SAYI İLE İÇERİK ÇELİŞİYORDU. Üreticide `CAP = 25`, burada
 *     `slice(0, 12)` vardı. Bağdat marker'ı başlıkta "388 canonical olay"
 *     yazıp listede 12 satır gösteriyor, sonra "+376 daha" diyordu — ve o
 *     satırın açılacak HİÇBİR hedefi yoktu. Ölçüldü: 5.618 olayın yalnız
 *     2.616'sı (%46) ekrana ulaşıyordu.
 *     Onarım: her iki kesme de kaldırıldı; payload artık %100 taşıyor ve
 *     liste KAYDIRILABİLİR. Sayı ile içerik artık aynı şeyi söylüyor.
 *
 *  2) YANLIŞ KESİNLİK. Marker yarıçapı yalnız olay SAYISININ fonksiyonuydu;
 *     koordinatın ne kadar güvenilir olduğu hiçbir yere yansımıyordu. Oysa
 *     kaynak kayıt bunu biliyor: 5.618 olayın 1.563'ü (%27,8) centroid ya da
 *     yaklaşık koordinat üzerinde ve 613'ü 250 KM hassasiyetli bir noktada
 *     duruyor — 100 m hassasiyetli Haleb ile aynı görsel dilde çiziliyordu.
 *     Onarım: belirsiz koordinatlı marker KESİKLİ kenarla çiziliyor ve popup
 *     hassasiyeti açıkça yazıyor.
 *
 * Props: map (Leaflet instance) · lang · visible
 */
import { useEffect, useRef } from 'react';
import L from 'leaflet';

const CANON = '#38bdf8';   // camgöbeği — v1 altınından ayrışır

/* Alt tür etiketleri. Üretici artık alt türü OLMAYAN olaya "Event" YAZMIYOR
   ("tür yok" bir tür değildir; 1.838 kayıt böyleydi) — etiketlemeyi burası
   yapar ve sınıflanmamış olanı öyle adlandırır. */
const SUBTYPE_TR = {
  Battle: 'Muharebe', Conquest: 'Fetih', Revolt: 'İsyan', Treaty: 'Antlaşma',
  Founding: 'Kuruluş', Composition: 'Telif', Death: 'Vefat', Disaster: 'Âfet',
  _yok: 'sınıflanmamış',
};
const SUBTYPE_AR = {
  Battle: 'معركة', Conquest: 'فتح', Revolt: 'ثورة', Treaty: 'معاهدة',
  Founding: 'تأسيس', Composition: 'تأليف', Death: 'وفاة', Disaster: 'كارثة',
  _yok: 'غير مصنف',
};
const subLabel = (k, lang) => (
  lang === 'ar' ? (SUBTYPE_AR[k] || k)
    : lang === 'en' ? (k === '_yok' ? 'unclassified' : k)
      : (SUBTYPE_TR[k] || k)
);

/* Koordinat belirsizliği metni. `u`: e=exact, a=approximate, c=centroid.
   `pm`: kaynak kaydın ilan ettiği hassasiyet (metre). */
function belirsizlikMetni(p, lang) {
  if (!p.u || p.u === 'e') return null;
  const km = p.pm != null ? Math.round(p.pm / 1000) : null;
  const tip = {
    tr: { a: 'yaklaşık konum', c: 'üst yerin merkezinden' },
    en: { a: 'approximate location', c: 'centroid of parent place' },
    ar: { a: 'موقع تقريبي', c: 'مركز المكان الأعلى' },
  }[lang === 'ar' ? 'ar' : lang === 'en' ? 'en' : 'tr'][p.u];
  if (!tip) return null;
  if (km && km >= 1) {
    const ek = lang === 'en' ? `±${km} km` : lang === 'ar' ? `±${km} كم` : `±${km} km`;
    return `${tip} · ${ek}`;
  }
  return tip;
}

const esc = (s) => String(s == null ? '' : s)
  .replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');

export default function CanonicalLayer({ map, lang = 'tr', visible }) {
  const layerRef = useRef(null);

  useEffect(() => {
    if (!map || !visible) return undefined;
    let cancelled = false;
    const group = L.layerGroup();
    layerRef.current = group;
    const tr = lang !== 'en' && lang !== 'ar';

    fetch('/view-data/canonical_events.json')
      .then((r) => (r.ok ? r.json() : Promise.reject(new Error(`canon ${r.status}`))))
      .then((places) => {
        if (cancelled) return;
        places.forEach((p) => {
          const radius = Math.min(4 + Math.log2(p.count + 1) * 2.2, 22);
          const belirsiz = p.u === 'c' || p.u === 'a';
          const mk = L.circleMarker([p.lat, p.lon], {
            radius,
            weight: belirsiz ? 1.4 : 1,
            color: '#0b3a4a',
            /* H56: belirsiz koordinat KESİKLİ kenarla çizilir — 250 km
               hassasiyetli bir bölge noktası, 100 m'lik bir şehirle aynı
               görsel kesinlikte görünmemeli. */
            dashArray: belirsiz ? '3,3' : undefined,
            fillColor: CANON,
            fillOpacity: belirsiz ? 0.32 : 0.5,
          });

          /* H56: slice(0, 12) KALDIRILDI. Payload artık kesilmemiş listeyi
             taşıyor; uzun listeler kaydırılır. Başlıktaki sayı ile gösterilen
             satır sayısı ARTIK AYNI. */
          const rows = p.events.map((e) => {
            const yr = e.year_ah != null
              ? `<span style="opacity:.55">H.${esc(e.year_ah)}</span> ` : '';
            const title = esc(lang === 'ar'
              ? (e.title_ar || e.title_tr)
              : (e.title_tr || e.title_ar));
            const read = (e.book_pid && e.sec != null)
              ? ` <a href="#library?book=${esc(e.book_pid)}&sec=${esc(e.sec)}" style="color:${CANON};text-decoration:none">§${esc(e.sec)}↗</a>`
              : '';
            return `<div style="font-size:11px;margin:1px 0;line-height:1.35">${yr}${title}${read}</div>`;
          }).join('');

          const subs = Object.entries(p.subtypes)
            .sort((a, b) => b[1] - a[1])
            .map(([k, n]) => `${esc(subLabel(k, lang))}·${n}`).join('  ');
          const name = esc(lang === 'ar'
            ? (p.name_ar || p.name_tr)
            : (p.name_tr || p.name_ar));
          const olayKelime = lang === 'ar' ? 'حدث في السجل'
            : lang === 'en' ? 'canonical events' : 'canonical olay';
          const bel = belirsizlikMetni(p, lang);
          const belSatiri = bel
            ? `<div style="font-size:10px;opacity:.75;margin:2px 0 5px;padding-left:6px;border-left:2px solid rgba(56,189,248,.5)">📍 ${esc(bel)}</div>`
            : '';
          /* Aklıselim tavanı aşılırsa üretici işaretler; o zaman SUSMAK yerine
             kesildiğini söyleriz. Normalde bu satır hiç çıkmaz. */
          const kesik = p._kesildi
            ? `<div style="font-size:10px;opacity:.6;margin-top:3px">${tr ? 'liste veri tarafında kesildi' : 'list truncated upstream'}</div>`
            : '';

          mk.bindPopup(
            `<div style="max-width:270px">
               <div style="font-weight:700;color:${CANON}">${name}</div>
               <div style="font-size:11px;opacity:.7;margin-bottom:2px">${p.count} ${olayKelime} · <span style="opacity:.65">${subs}</span></div>
               ${belSatiri}
               <div style="max-height:260px;overflow-y:auto">${rows}</div>${kesik}
             </div>`,
            { maxWidth: 310 },
          );
          group.addLayer(mk);
        });
        if (!cancelled) group.addTo(map);
      })
      .catch(() => { /* dosya yoksa sessizce boş katman — v1 haritası etkilenmez */ });

    return () => {
      cancelled = true;
      if (layerRef.current) { map.removeLayer(layerRef.current); layerRef.current = null; }
    };
  }, [map, visible, lang]);

  return null;
}
