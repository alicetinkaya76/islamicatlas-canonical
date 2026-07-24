/**
 * CanonicalLayer.jsx — H26: ana haritaya OPSİYONEL canonical olay katmanı.
 *
 * Ana #map v1'in db.json'ından beslenir (100 savaş + 200 olay). Bu katman,
 * canonical mağazadaki 5.618 kitap-türevi olayı (yer başına toplanmış, 721
 * marker) EK overlay olarak getirir — v1 render'ına DOKUNMADAN. Varsayılan
 * kapalı; toggle ile açılır. Ayırt edici renk (camgöbeği) = "canonical katman".
 *
 * Veri: /view-data/canonical_events.json (build_canonical_map_layer.py üretir).
 * DÜRÜSTLÜK: koordinat olayın değil, işaret ettiği canonical PLACE'in (gazetteer)
 * — popup bunu "yer" olarak sunar, olayı o yere yığar.
 *
 * Props: map (Leaflet instance) · lang · visible
 */
import { useEffect, useRef } from 'react';
import L from 'leaflet';

const CANON = '#38bdf8';   // camgöbeği — v1 altınından ayrışır

export default function CanonicalLayer({ map, lang = 'tr', visible }) {
  const layerRef = useRef(null);

  useEffect(() => {
    if (!map || !visible) return undefined;
    let cancelled = false;
    const group = L.layerGroup();
    layerRef.current = group;
    const tr = lang !== 'en';

    fetch('/view-data/canonical_events.json')
      .then((r) => (r.ok ? r.json() : Promise.reject(new Error(`canon ${r.status}`))))
      .then((places) => {
        if (cancelled) return;
        places.forEach((p) => {
          const radius = Math.min(4 + Math.log2(p.count + 1) * 2.2, 22);
          const mk = L.circleMarker([p.lat, p.lon], {
            radius, weight: 1, color: '#0b3a4a',
            fillColor: CANON, fillOpacity: 0.5,
          });
          const rows = p.events.slice(0, 12).map((e) => {
            const yr = e.year_ah != null ? `<span style="opacity:.55">H.${e.year_ah}</span> ` : '';
            const title = tr ? (e.title_tr || e.title_ar) : (e.title_ar || e.title_tr);
            const read = (e.book_pid && e.sec != null)
              ? ` <a href="#library?book=${e.book_pid}&sec=${e.sec}" style="color:${CANON};text-decoration:none">§${e.sec}↗</a>`
              : '';
            return `<div style="font-size:11px;margin:1px 0;line-height:1.35">${yr}${title}${read}</div>`;
          }).join('');
          const more = p.count > 12
            ? `<div style="font-size:10px;opacity:.5;margin-top:3px">+${p.count - 12} ${tr ? 'daha' : 'more'}</div>`
            : '';
          const subs = Object.entries(p.subtypes)
            .sort((a, b) => b[1] - a[1]).map(([k, n]) => `${k}·${n}`).join('  ');
          const name = tr ? (p.name_tr || p.name_ar) : (p.name_ar || p.name_tr);
          mk.bindPopup(
            `<div style="max-width:270px">
               <div style="font-weight:700;color:${CANON}">${name}</div>
               <div style="font-size:11px;opacity:.7;margin-bottom:5px">${p.count} ${tr ? 'canonical olay' : 'canonical events'} · <span style="opacity:.65">${subs}</span></div>
               ${rows}${more}
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
