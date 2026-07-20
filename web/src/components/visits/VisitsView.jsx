import { useState, useEffect, useMemo, useRef } from 'react';
import L from 'leaflet';
import 'leaflet/dist/leaflet.css';

/**
 * VisitsView — Seyahatnâmeler, tek harita dili (H21 S3, Dalga-4).
 *
 * Durak modeli (build_visits.py → books/visits.json) üç kaynağı aynı
 * şemada birleştirir: İbn Battûta (Rihle), İbn Cübeyr (er-Rihle),
 * Evliyâ Çelebi (Seyahatnâme). Amaç yol haritasının D4 vaadi: "İbn
 * Battûta ile İbn Cübeyr'in rotaları aynı harita dilinde yan yana".
 *
 * v1'in kendi Rihla/Evliyâ görünümleri DOKUNULMADI — bu, onların
 * yanına gelen karşılaştırma katmanıdır (bookkit anayasası).
 *
 * geo_suspect'li duraklar haritada GİZLİ (H14 süreklilik süpürmesi
 * kararı); sayıları panelde dürüstçe yazılır.
 */

const GOLD = '#c9a84c';
/* Kaynak renkleri — bookkit paletiyle çakışmayan, seyahat-ayırt edici. */
const SRC_COLOR = {
  rihla: '#4fc3f7',        // İbn Battûta — mavi
  'ibn-jubayr': '#ffb74d', // İbn Cübeyr — turuncu
  evliya: '#81c784',       // Evliyâ Çelebi — yeşil
};
const SRC_LABEL = {
  rihla: 'İbn Battûta',
  'ibn-jubayr': 'İbn Cübeyr',
  evliya: 'Evliyâ Çelebi',
};

export default function VisitsView({ lang = 'tr' }) {
  const tr = lang !== 'en';
  const [data, setData] = useState(null);
  const [meta, setMeta] = useState(null);
  const [err, setErr] = useState(false);
  const [active, setActive] = useState(new Set());
  const [sel, setSel] = useState(null);
  const mapElRef = useRef(null);
  const mapRef = useRef(null);
  const layersRef = useRef([]);

  useEffect(() => {
    const base = import.meta.env.BASE_URL || '/';
    fetch(`${base}books/visits.json`, { cache: 'no-cache' })
      .then((r) => (r.ok ? r.json() : Promise.reject()))
      .then((d) => {
        setData(d);
        /* Açılışta iki hac seyahatnâmesi seçili gelsin (karşılaştırmanın
           kendisi bu görünümün varlık sebebi); yoksa ilk seyahat. */
        const trips = d.seyahatler || [];
        const seed = trips.filter((t) => t.sira_turu === 'metin_tanikli')
          .slice(0, 2).map((t) => t.id);
        setActive(new Set(seed.length ? seed : trips.slice(0, 1).map((t) => t.id)));
      })
      .catch(() => setErr(true));
    fetch(`${base}books/visits_meta.json`, { cache: 'no-cache' })
      .then((r) => (r.ok ? r.json() : null)).then(setMeta).catch(() => {});
  }, []);

  const stopsByTrip = useMemo(() => {
    if (!data) return {};
    const m = {};
    (data.duraklar || []).forEach((s) => { (m[s.sid] = m[s.sid] || []).push(s); });
    Object.values(m).forEach((arr) => arr.sort((a, b) => (a.seq || 0) - (b.seq || 0)));
    return m;
  }, [data]);

  const tripById = useMemo(() => {
    const m = {};
    (data?.seyahatler || []).forEach((t) => { m[t.id] = t; });
    return m;
  }, [data]);

  /* Harita çizimi */
  useEffect(() => {
    if (!data || !mapElRef.current) return;
    if (!mapRef.current) {
      const map = L.map(mapElRef.current, { scrollWheelZoom: true, zoomControl: true });
      L.tileLayer('https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png',
        { attribution: '© OpenStreetMap · CARTO', subdomains: 'abcd' }).addTo(map);
      map.setView([28, 40], 4);
      mapRef.current = map;
    }
    const map = mapRef.current;
    layersRef.current.forEach((l) => map.removeLayer(l));
    layersRef.current = [];

    const bounds = [];
    active.forEach((tid) => {
      const trip = tripById[tid];
      if (!trip) return;
      const color = SRC_COLOR[trip.kaynak] || GOLD;
      /* geo_suspect gizli (H14 kararı); koordinatsızlar zaten çizilemez */
      const pts = (stopsByTrip[tid] || []).filter(
        (s) => s.lat != null && s.lon != null && !(s.geo_note || '').includes('suspect'));
      /* H21 KARAR: çizgi YALNIZ metin-tanıklı sırada çizilir. Evliyâ'nın
         kayıt sırası güzergâh DEĞİL (dosya/dışa-aktarım sırası; 5.444 kayıt
         343 ayrı bloğa örülü) — çizgi çizmek veriye olmayan bir güzergâh
         iddiası eklerdi. build_visits.py bunu `sira_turu` ile bildirir. */
      if (pts.length > 1 && trip.sira_turu === 'metin_tanikli') {
        const line = L.polyline(pts.map((s) => [s.lat, s.lon]),
          { color, weight: 2, opacity: .55, dashArray: '5,5' }).addTo(map);
        layersRef.current.push(line);
      }
      pts.forEach((s) => {
        const mk = L.circleMarker([s.lat, s.lon], {
          radius: s.is_stay ? 6.5 : 4.5, weight: 1.2, color: '#0f1419',
          fillColor: color, fillOpacity: .9,
        }).addTo(map);
        mk.bindPopup(
          `<div style="font-family:Amiri,serif;font-size:16px" dir="rtl"><b>${s.ad_ar || ''}</b></div>` +
          `<div style="font-size:12.5px"><b>${s.ad_tr || ''}</b></div>` +
          `<div style="font-size:11px;opacity:.75">${SRC_LABEL[trip.kaynak] || trip.kaynak} · ${tr ? 'durak' : 'stop'} #${s.seq}</div>` +
          (s.varis_metin ? `<div dir="rtl" style="font-size:11.5px;opacity:.9;margin-top:3px">📅 ${s.varis_metin}</div>` : '') +
          (s.geo_note ? `<div style="font-size:10.5px;opacity:.65;margin-top:2px">⚠ ${s.geo_note}</div>` : ''));
        mk.on('click', () => setSel({ ...s, _trip: trip }));
        layersRef.current.push(mk);
        bounds.push([s.lat, s.lon]);
      });
    });
    if (bounds.length) map.fitBounds(L.latLngBounds(bounds).pad(0.12), { maxZoom: 7 });
  }, [data, active, stopsByTrip, tripById, tr]);

  useEffect(() => () => { if (mapRef.current) { mapRef.current.remove(); mapRef.current = null; } }, []);

  const card = { background: 'rgba(255,255,255,.04)', border: '1px solid rgba(201,168,76,.25)', borderRadius: 10 };

  if (err) return (
    <div style={{ padding: 40, textAlign: 'center', opacity: .8 }}>
      {tr ? 'Seyahat verisi bulunamadı — `python3 pipelines/frontend/build_visits.py` koşun.'
          : 'Visit data missing — run build_visits.py.'}
    </div>
  );
  if (!data) return <div style={{ padding: 40, textAlign: 'center', opacity: .6 }}>{tr ? 'Seyahatler yükleniyor…' : 'Loading…'}</div>;

  const trips = data.seyahatler || [];

  return (
    <div style={{ padding: '14px 16px 30px' }}>
      <h1 style={{ color: GOLD, fontSize: 22, margin: '0 0 2px' }}>
        🧭 {tr ? 'Seyahatnâmeler' : 'Travel Accounts'}
      </h1>
      <p style={{ opacity: .75, fontSize: 13, margin: '0 0 12px' }}>
        {tr ? `${trips.length} seyahat · ${(data.duraklar || []).length.toLocaleString('tr-TR')} durak — üç seyyah aynı harita dilinde`
            : `${trips.length} journeys · ${(data.duraklar || []).length} stops — three travellers, one map language`}
      </p>

      {/* Seyahat seçiciler */}
      <div style={{ display: 'flex', flexWrap: 'wrap', gap: 6, marginBottom: 10 }}>
        {trips.map((t) => {
          const on = active.has(t.id);
          const color = SRC_COLOR[t.kaynak] || GOLD;
          return (
            <button key={t.id}
              onClick={() => setActive((p) => { const n = new Set(p); n.has(t.id) ? n.delete(t.id) : n.add(t.id); return n; })}
              style={{ padding: '3px 11px', borderRadius: 999, fontSize: 11.5, cursor: 'pointer',
                background: on ? color : 'rgba(0,0,0,.25)', color: on ? '#0f1419' : color,
                border: `1px solid ${color}`, fontWeight: on ? 700 : 400 }}>
              {t.ad_tr || t.id} {t.n_durak != null ? `(${t.n_durak})` : ''}
              {t.sira_turu === 'dosya_sirasi' && (
                <span title={tr ? 'Kayıt sırası güzergâh değil — çizgi çizilmez' : 'Record order is not an itinerary — no line drawn'}
                  style={{ marginLeft: 4, opacity: .8 }}>◦</span>
              )}
            </button>
          );
        })}
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: '1fr 300px', gap: 12 }}>
        <div ref={mapElRef} style={{ height: 'calc(100vh - 290px)', minHeight: 400, borderRadius: 10, border: '1px solid rgba(201,168,76,.3)' }} />
        <aside style={{ ...card, padding: '12px 14px', overflowY: 'auto', maxHeight: 'calc(100vh - 290px)' }}>
          {!sel ? (
            <div style={{ fontSize: 12.5, opacity: .75, lineHeight: 1.7 }}>
              <b style={{ color: GOLD }}>{tr ? 'Durak modeli' : 'Visit model'}</b><br />
              {tr ? 'Bir durağa tıklayın. Kesikli çizgiler seyahat sırasını, dolu daireler konaklamaları gösterir.'
                  : 'Click a stop. Dashed lines show sequence; filled circles are stays.'}
              {meta && meta.toplam && (
                <div style={{ marginTop: 12, fontSize: 11.5, lineHeight: 1.9 }}>
                  {meta.toplam.durak != null && <div>🧭 {tr ? 'durak' : 'stops'}: {Number(meta.toplam.durak).toLocaleString('tr-TR')}</div>}
                  {meta.toplam.koordinatsiz != null && <div>📍 {tr ? 'koordinatsız' : 'ungeocoded'}: {meta.toplam.koordinatsiz}</div>}
                  {meta.toplam.supheli != null && <div>⚠ {tr ? 'şüpheli (gizli)' : 'suspect (hidden)'}: {meta.toplam.supheli}</div>}
                </div>
              )}
            </div>
          ) : (
            <>
              <div dir="rtl" style={{ fontFamily: "'Amiri',serif", fontSize: 20, color: GOLD }}>{sel.ad_ar}</div>
              <div style={{ fontSize: 14, fontWeight: 700, marginTop: 2 }}>{sel.ad_tr}</div>
              <div style={{ fontSize: 11.5, opacity: .7, marginTop: 3 }}>
                {SRC_LABEL[sel._trip.kaynak] || sel._trip.kaynak} · {tr ? 'durak' : 'stop'} #{sel.seq}
                {sel.is_stay ? ` · ${tr ? 'konaklama' : 'stay'}` : ''}
              </div>
              {sel.varis_metin && (
                <div dir="rtl" style={{ fontSize: 12.5, marginTop: 8, padding: '6px 8px', background: 'rgba(0,0,0,.25)', borderRadius: 6 }}>
                  📅 {sel.varis_metin}
                </div>
              )}
              {sel.geo_note && <div style={{ fontSize: 11, opacity: .7, marginTop: 6 }}>⚠ {sel.geo_note}</div>}
              {sel.yer_pid && (
                <div style={{ fontSize: 10.5, opacity: .5, marginTop: 8, fontFamily: 'monospace' }}>{sel.yer_pid}</div>
              )}
              {sel.sec != null && sel._trip.pidnum && (
                <a href={`#library?book=${sel._trip.pidnum}&sec=${sel.sec}`}
                  style={{ display: 'inline-block', marginTop: 10, padding: '5px 10px', borderRadius: 8,
                    border: `1px solid ${GOLD}`, color: GOLD, textDecoration: 'none', fontSize: 12 }}>
                  📖 {tr ? 'bölümü oku' : 'read section'} §{sel.sec}
                </a>
              )}
            </>
          )}
        </aside>
      </div>
    </div>
  );
}
