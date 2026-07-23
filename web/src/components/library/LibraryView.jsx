/**
 * LibraryView — Çekirdek Külliyat rafı + kitap okuyucu (H13 S-D D3, v0).
 *
 * Veri: /reading/core_shelf.json (build_reading_data.py üretir; gitignored)
 *       /reading/<pidnum>/manifest.json + sec_NNNN.json (bölüm bazlı fetch)
 * Derinlik çıtası uygulaması: RTL Amiri okuyucu, sayfa-çapası rozetleri
 * (PageVxxPyyy → paylaşılabilir atıf), 3 sütun, bölüm ağacında
 * diakritik-duyarsız arama, kimlik kartında çift bilgi blokları.
 */
import { useState, useEffect, useMemo, useCallback, useRef } from 'react';
import L from 'leaflet';
import 'leaflet/dist/leaflet.css';
import { fmtCount } from '../../data/sourceCounts';

const GOLD = '#c9a84c';
const norm = (s) =>
  (s || '')
    .toLowerCase()
    .normalize('NFD')
    .replace(/[̀-ًͯ-ٰٟ]/g, '')
    .replace(/[ıİ]/g, 'i');

function openitiRepoUrl(uri) {
  const m = uri.match(/^(\d{4})/);
  if (!m) return null;
  const death = parseInt(m[1], 10);
  const bucket = String(Math.ceil(death / 25) * 25).padStart(4, '0') + 'AH';
  const author = uri.split('.')[0];
  return `https://github.com/OpenITI/${bucket}/tree/master/data/${author}/${uri}`;
}

export default function LibraryView({ lang = 'tr', initialBook = null, initialSec = null, initialP = null }) {
  const tr = lang !== 'en';
  const [shelf, setShelf] = useState(null);
  const [err, setErr] = useState(null);
  const [book, setBook] = useState(null);        // manifest
  const [secIdx, setSecIdx] = useState(0);
  const [section, setSection] = useState(null);
  const [tocQuery, setTocQuery] = useState('');
  const [mentions, setMentions] = useState(null);   // kitap→yer anılmaları
  const [stopsDraft, setStopsDraft] = useState(null); // çıkarılmış rota
  const [layerData, setLayerData] = useState(null);   // olay/yapı katmanı
  const [mode, setMode] = useState('text');         // text | map | route | layer
  const secCache = useRef({});
  const mapRef = useRef(null);
  const mapElRef = useRef(null);
  const readerRef = useRef(null);
  /* H17 S4: &p= çapası — link üretiliyordu ama açılışta hiç kullanılmıyordu */
  const pendingP = useRef(null);
  /* Ref yalnız ilk mount'ta dolarsa remount/HMR'da kaybolur; prop her
     geldiğinde kurulur, kaydırma gerçekleşince tüketilir. */
  useEffect(() => { if (initialP) pendingP.current = initialP; }, [initialP]);

  useEffect(() => {
    fetch('/reading/core_shelf.json')
      .then((r) => (r.ok ? r.json() : Promise.reject(r.status)))
      .then(setShelf)
      .catch(() => setErr(tr
        ? 'Okuma verisi bulunamadı — `python3 pipelines/reading/build_reading_data.py` koşun.'
        : 'Reading data missing — run build_reading_data.py.'));
  }, [tr]);

  const openBook = useCallback((pidnum, sec = 0) => {
    fetch(`/reading/${pidnum}/manifest.json`)
      .then((r) => (r.ok ? r.json() : Promise.reject(new Error(`manifest ${r.status}`))))
      .then((m) => {
        secCache.current = {};
        setBook({ ...m, pidnum });
        setSecIdx(sec);
        setTocQuery('');
        setMode('text');
        setMentions(null);
        fetch(`/reading/${pidnum}/mentions.json`)
          .then((r) => (r.ok ? r.json() : null))
          .then(setMentions)
          .catch(() => setMentions(null));
        setStopsDraft(null);
        fetch(`/reading/${pidnum}/stops_draft.json`)
          .then((r) => (r.ok ? r.json() : null))
          .then(setStopsDraft)
          .catch(() => setStopsDraft(null));
        setLayerData(null);
        fetch(`/reading/${pidnum}/layer.json`)
          .then((r) => (r.ok ? r.json() : null))
          .then(setLayerData)
          .catch(() => setLayerData(null));
        window.location.hash = `library?book=${pidnum}&sec=${sec}`;
      })
      /* H17 S4: bozuk pidnum sessiz beyaz ekran bırakıyordu */
      .catch(() => setErr(tr
        ? `Kitap açılamadı (${pidnum}) — okuma verisi eksik olabilir; scripts/start_local.sh veri kontrolünü koşun.`
        : `Could not open book (${pidnum}) — reading data may be missing.`));
  }, [tr]);

  useEffect(() => {
    if (initialBook) openBook(initialBook, parseInt(initialSec || '0', 10) || 0);
  }, [initialBook, initialSec, openBook]);

  useEffect(() => {
    if (!book) return;
    const key = `${book.pidnum}:${secIdx}`;
    if (secCache.current[key]) { setSection(secCache.current[key]); return; }
    setSection(null);
    /* H24: bölüm fetch'i guard'sızdı — bozuk/eksik sec dosyası kalıcı
       "Bölüm yükleniyor…" kilidine sokuyordu. r.ok kontrolü + .catch ile
       hata durumunda kilit yerine boş-bölüm mesajı gösterilir. */
    fetch(`/reading/${book.pidnum}/sec_${String(secIdx).padStart(4, '0')}.json`)
      .then((r) => (r.ok ? r.json() : Promise.reject(new Error(`sec ${r.status}`))))
      .then((s) => { secCache.current[key] = s; setSection(s); readerRef.current?.scrollTo(0, 0); })
      .catch(() => setSection({ paras: [], _error: true }));
  }, [book, secIdx]);

  /* H17 S4: bölüm yüklenince bekleyen sayfa-çapasına kaydır + kısa vurgu.
     Çapa ancak paragraflar boyandıktan sonra bulunur — birkaç kare denenir
     (ilk rAF, StrictMode/uzun bölüm boyamasında erken kalıyordu). */
  useEffect(() => {
    if (!section || !pendingP.current) return;
    const p = pendingP.current;
    let tries = 0;
    const attempt = () => {
      if (pendingP.current !== p) return;
      const el = document.getElementById(`para-${p}`);
      if (el) {
        /* pending BURADA sıfırlanmaz: StrictMode'da ikinci openBook koşusu
           bölümü yeniden indirip scrollTo(0,0) ile ezebiliyor; çapa ancak
           kullanıcı bölüm değiştirince (gotoSec) düşer, yeniden-yüklemede
           tekrar kazanır. */
        el.scrollIntoView({ block: 'start' });
        el.style.background = 'rgba(201,168,76,.14)';
        setTimeout(() => { el.style.background = ''; }, 2500);
      } else if (++tries < 30) {
        setTimeout(attempt, 60);
      }
    };
    /* rAF DEĞİL setTimeout: gömülü/arka-plan sekmelerde rAF kısılıp hiç
       ateşlenmeyebiliyor (tarayıcı panelinde canlı gözlendi). */
    setTimeout(attempt, 0);
  }, [section]);

  const gotoSec = useCallback((i) => {
    pendingP.current = null;   // kullanıcı gezinmesi bekleyen çapayı düşürür
    setSecIdx(i);
    if (book) window.location.hash = `library?book=${book.pidnum}&sec=${i}`;
  }, [book]);

  // Kitap haritası: koyu CARTO zemin + anılma yoğunluğuna göre marker
  useEffect(() => {
    if (mode !== 'map' || !mentions || !mapElRef.current) return;
    if (mapRef.current) { mapRef.current.remove(); mapRef.current = null; }
    const pts = mentions.places.filter((pl) =>
      pl.lat != null && (pl.total >= 2 || pl.name.includes(' ')));
    const map = L.map(mapElRef.current, { scrollWheelZoom: true, zoomControl: true });
    L.tileLayer('https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png',
      { attribution: '© OpenStreetMap · CARTO', subdomains: 'abcd' }).addTo(map);
    const grp = [];
    pts.forEach((pl) => {
      const r = Math.min(4 + Math.log2(pl.total + 1) * 2.4, 16);
      const mk = L.circleMarker([pl.lat, pl.lon], {
        radius: r, weight: 1.2, color: GOLD,
        fillColor: GOLD, fillOpacity: 0.55,
      }).addTo(map);
      const secBtns = pl.secs.slice(0, 8).map((s) =>
        `<button data-sec="${s}" style="margin:2px;padding:1px 8px;border-radius:8px;border:1px solid ${GOLD};background:none;color:${GOLD};cursor:pointer;font-size:11px">§${s}</button>`).join('');
      mk.bindPopup(`<div dir="rtl" style="font-family:Amiri,serif;font-size:16px"><b>${pl.name}</b></div>
        <div style="font-size:11px;opacity:.8">${pl.total} ${lang === 'en' ? 'mentions' : 'anılma'} · ${pl.secs.length} ${lang === 'en' ? 'sections' : 'bölüm'}</div>
        <div>${secBtns}</div>`);
      mk.on('popupopen', (e) => {
        e.popup.getElement().querySelectorAll('button[data-sec]').forEach((b) => {
          b.onclick = () => { setMode('text'); gotoSec(parseInt(b.dataset.sec, 10)); };
        });
      });
      grp.push([pl.lat, pl.lon]);
    });
    if (grp.length) map.fitBounds(L.latLngBounds(grp).pad(0.15), { maxZoom: 7 });
    mapRef.current = map;
    return () => { if (mapRef.current) { mapRef.current.remove(); mapRef.current = null; } };
  }, [mode, mentions, lang, gotoSec]);

  // Rota (taslak): sıralı duraklar + altın kesikli polyline + numaralı marker
  useEffect(() => {
    if (mode !== 'route' || !stopsDraft || !mapElRef.current) return;
    if (mapRef.current) { mapRef.current.remove(); mapRef.current = null; }
    const pts = stopsDraft.stops.filter((s) => s.lat != null && !s.geo_suspect);
    const map = L.map(mapElRef.current, { scrollWheelZoom: true });
    L.tileLayer('https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png',
      { attribution: '© OpenStreetMap · CARTO', subdomains: 'abcd' }).addTo(map);
    const line = pts.map((s) => [s.lat, s.lon]);
    if (line.length > 1) L.polyline(line, { color: GOLD, weight: 2, dashArray: '6 8', opacity: .7 }).addTo(map);
    pts.forEach((s) => {
      const mk = L.circleMarker([s.lat, s.lon], {
        radius: s.is_stay ? 9 : 5, weight: 1.5, color: '#0f1419',
        fillColor: s.confidence === 'high' ? GOLD : '#8a7440', fillOpacity: .95,
      }).addTo(map);
      mk.bindTooltip(String(s.seq), { permanent: true, direction: 'center',
        className: 'route-seq-label', opacity: 1 });
      mk.bindPopup(`<div dir="rtl" style="font-family:Amiri,serif;font-size:16px"><b>${s.name_ar}</b></div>
        <div style="font-size:12px"><b>${s.seq}. ${s.name_tr || ''}</b></div>
        ${s.arrival_text ? `<div dir="rtl" style="font-size:11px;opacity:.85">📅 ${s.arrival_text}</div>` : ''}
        <div style="font-size:11px;opacity:.85;max-width:230px">${(s.stay_summary_tr || '').slice(0, 220)}</div>
        <button data-sec="${s.sec}" style="margin-top:3px;padding:1px 8px;border-radius:8px;border:1px solid ${GOLD};background:none;color:${GOLD};cursor:pointer;font-size:11px">${lang === 'en' ? 'read section' : 'bölümü oku'} §${s.sec}</button>`);
      mk.on('popupopen', (e) => {
        e.popup.getElement().querySelectorAll('button[data-sec]').forEach((b) => {
          b.onclick = () => { setMode('text'); gotoSec(parseInt(b.dataset.sec, 10)); };
        });
      });
    });
    if (line.length) map.fitBounds(L.latLngBounds(line).pad(0.12), { maxZoom: 7 });
    mapRef.current = map;
    return () => { if (mapRef.current) { mapRef.current.remove(); mapRef.current = null; } };
  }, [mode, stopsDraft, lang, gotoSec]);

  // Olay/yapı katmanı haritası: tür-renkli markerlar
  const LAYER_COLORS = useMemo(() => ({
    conquest: '#c9a84c', battle: '#d9534f', treaty: '#5bc0de', raid: '#e08e45',
    siege: '#b8607a', founding: '#5cb85c', revolt: '#9b59b6', administration: '#7f8c8d',
    gate: '#c9a84c', well: '#5bc0de', mosque: '#5cb85c', quarter: '#e08e45',
    monument: '#9b59b6', boundary_marker: '#7f8c8d', mountain: '#8a7440', entry: '#c9a84c',
    canal: '#5bc0de', street: '#e08e45', fief: '#5cb85c', bath: '#b8607a',
    migration: '#5bc0de', revelation_context: '#8a7440', region: '#c9a84c',
    cemetery: '#b8607a', house: '#d9534f', marker: '#5bc0de', other: '#aaa',
  }), []);
  useEffect(() => {
    if (mode !== 'layer' || !layerData || !mapElRef.current) return;
    if (mapRef.current) { mapRef.current.remove(); mapRef.current = null; }
    const pts = layerData.records.filter((r) => r.lat != null && !r.geo_suspect);
    const map = L.map(mapElRef.current, { scrollWheelZoom: true });
    L.tileLayer('https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png',
      { attribution: '© OpenStreetMap · CARTO', subdomains: 'abcd' }).addTo(map);
    const grp = [];
    if (layerData.kind === 'routes') {
      layerData.records.filter((r) => r.from_lat != null && r.to_lat != null).forEach((r) => {
        const line = L.polyline([[r.from_lat, r.from_lon], [r.to_lat, r.to_lon]],
          { color: GOLD, weight: 1.6, opacity: .55 }).addTo(map);
        line.bindPopup(`<div dir="rtl" style="font-family:Amiri,serif;font-size:14px"><b>${r.from_ar} ← ${r.to_ar}</b></div>
          ${r.distance_text ? `<div dir="rtl" style="font-size:11px">📏 ${r.distance_text}</div>` : ''}
          <button data-sec="${r.sec}" style="margin-top:3px;padding:1px 8px;border-radius:8px;border:1px solid ${GOLD};background:none;color:${GOLD};cursor:pointer;font-size:11px">§${r.sec}</button>`);
        line.on('popupopen', (e) => {
          e.popup.getElement().querySelectorAll('button[data-sec]').forEach((b) => {
            b.onclick = () => { setMode('text'); gotoSec(parseInt(b.dataset.sec, 10)); };
          });
        });
        grp.push([r.from_lat, r.from_lon], [r.to_lat, r.to_lon]);
      });
    }
    pts.forEach((r) => {
      const typ = r.event_type || r.type || 'other';
      const mk = L.circleMarker([r.lat, r.lon], {
        radius: 7, weight: 1.2, color: '#0f1419',
        fillColor: LAYER_COLORS[typ] || '#aaa', fillOpacity: .9,
      }).addTo(map);
      mk.bindPopup(`<div dir="rtl" style="font-family:Amiri,serif;font-size:15px"><b>${r.title_ar || r.name_ar || ''}</b></div>
        <div style="font-size:12px"><b>${r.title_tr || r.name_tr || ''}</b> · <span style="opacity:.7">${typ}</span></div>
        ${r.date_text ? `<div dir="rtl" style="font-size:11px;opacity:.85">📅 ${r.date_text}</div>` : ''}
        ${r.measurements_text ? `<div dir="rtl" style="font-size:11px;opacity:.85">📏 ${r.measurements_text.slice(0, 90)}</div>` : ''}
        ${r.summary_ar ? `<div dir="rtl" style="font-family:Amiri,serif;font-size:12px;opacity:.9;max-width:250px">${r.summary_ar.slice(0, 180)}</div>` : ''}
        ${r.longitude_text ? `<div dir="rtl" style="font-size:11px;color:#c9a84c">🧭 tûl (boylam): ${r.longitude_text} · arz (enlem): ${r.latitude_text || '—'}${r.clime_text ? ' · '+r.clime_text : ''}</div>` : ''}
        ${r.vocalization_ar ? `<div dir="rtl" style="font-family:Amiri,serif;font-size:11px;opacity:.75;max-width:250px">🔤 ${r.vocalization_ar.slice(0, 120)}</div>` : ''}
        ${r.region_hint_ar ? `<div dir="rtl" style="font-size:11px;opacity:.75;max-width:250px">🧭 ${r.region_hint_ar.slice(0, 100)}</div>` : ''}
        <div style="font-size:11px;opacity:.85;max-width:240px">${(r.summary_tr || '').slice(0, 200)}</div>
        <button data-sec="${r.sec}" style="margin-top:3px;padding:1px 8px;border-radius:8px;border:1px solid ${GOLD};background:none;color:${GOLD};cursor:pointer;font-size:11px">${lang === 'en' ? 'read' : 'bölümü oku'} §${r.sec}</button>`);
      mk.on('popupopen', (e) => {
        e.popup.getElement().querySelectorAll('button[data-sec]').forEach((b) => {
          b.onclick = () => { setMode('text'); gotoSec(parseInt(b.dataset.sec, 10)); };
        });
      });
      grp.push([r.lat, r.lon]);
    });
    if (grp.length) map.fitBounds(L.latLngBounds(grp).pad(0.15), { maxZoom: 9 });
    mapRef.current = map;
    return () => { if (mapRef.current) { mapRef.current.remove(); mapRef.current = null; } };
  }, [mode, layerData, lang, gotoSec, LAYER_COLORS]);

  const filteredToc = useMemo(() => {
    if (!book) return [];
    const q = norm(tocQuery);
    return q ? book.sections.filter((s) => norm(s.title).includes(q)) : book.sections;
  }, [book, tocQuery]);

  /* H18 S3: kitap istatistikleri — tamamı mevcut veriden istemcide sayılır
     (mentions + layer); elle sayı yok. */
  const bookStats = useMemo(() => {
    if (!book) return null;
    const topPlaces = mentions
      ? [...mentions.places].sort((a, b) => b.total - a.total).slice(0, 20)
      : [];
    const kindCounts = {};
    if (layerData) {
      layerData.records.forEach((r) => {
        const k = r.event_type || r.type || 'other';
        kindCounts[k] = (kindCounts[k] || 0) + 1;
      });
    }
    const kinds = Object.entries(kindCounts).sort((a, b) => b[1] - a[1]);
    return {
      topPlaces,
      maxTotal: topPlaces.length ? topPlaces[0].total : 1,
      kinds,
      nLayer: layerData ? layerData.records.length : 0,
      nGeoLayer: layerData ? layerData.records.filter((r) => r.lat != null || r.from_lat != null).length : 0,
    };
  }, [book, mentions, layerData]);

  /* ═══ stil kısayolları (v1 koyu-altın dili) ═══ */
  const card = { background: 'rgba(255,255,255,.04)', border: '1px solid rgba(201,168,76,.25)', borderRadius: 10 };
  const chip = { display: 'inline-block', padding: '2px 10px', borderRadius: 999, fontSize: 11, background: 'rgba(201,168,76,.15)', color: GOLD, marginRight: 6, marginBottom: 4 };

  if (err) return <div style={{ padding: 40, textAlign: 'center', opacity: .8 }}>{err}</div>;
  if (!shelf) return <div style={{ padding: 40, textAlign: 'center', opacity: .6 }}>{tr ? 'Kütüphane yükleniyor…' : 'Loading library…'}</div>;

  /* ═══════════ RAF GÖRÜNÜMÜ (H17 S4: iki bölümlü) ═══════════ */
  if (!book) {
    /* Kürasyonlu Atlas Görünümleri — v1'in sevilen kitap sayfaları rafta
       kart olarak; tıklama mevcut sekmelerine gider (Dalga-0 raf birleşmesi).
       Rozet sayıları veriden (sourceCounts) — elle sayı yasak. */
    const curated = [
      { tab: 'yaqut', ar: 'معجم البلدان', name: tr ? "Mu'cemü'l-Büldân" : 'Muʿjam al-Buldān', by: 'Yâkût el-Hamevî', key: 'yaqut', caps: '🗺 🌍 📊 🕸' },
      { tab: 'rihla', ar: 'الرحلة', name: tr ? 'Rihle' : 'Riḥla', by: 'İbn Battûta', key: 'rihla', caps: '🛤 🗺' },
      { tab: 'evliya', ar: 'سياحتنامه', name: 'Seyahatnâme', by: 'Evliyâ Çelebi', key: 'evliya', caps: '🛤 🗺 🕰' },
      { tab: 'muqaddasi', ar: 'أحسن التقاسيم', name: tr ? "Ahsenü't-Tekāsîm" : 'Aḥsan al-Taqāsīm', by: 'Makdisî', key: 'muqaddasi', caps: '🗺 🛤 📐' },
      { tab: 'khitat', ar: 'الخطط', name: tr ? 'el-Hıtat' : 'al-Khiṭaṭ', by: 'Makrîzî', key: 'khitat', caps: '🏛 🗺' },
      { tab: 'lestrange', ar: '', name: 'Lands of the Eastern Caliphate', by: 'G. Le Strange', key: 'lestrange', caps: '🗺 🔗' },
      { tab: 'salibiyyat', ar: '', name: tr ? 'Salibiyyât (6 kronik)' : 'Crusades (6 chronicles)', by: tr ? 'Müslüman kronikçiler' : 'Muslim chroniclers', key: 'salibiyyat', caps: '⚔️ 🕰 🕸' },
    ];
    return (
      <div style={{ maxWidth: 1200, margin: '0 auto', padding: '24px 16px 60px' }}>
        <h1 style={{ color: GOLD, fontSize: 26, margin: '4px 0 2px' }}>
          📚 {tr ? 'Kütüphane' : 'Library'}
        </h1>
        <p style={{ opacity: .75, margin: '0 0 14px', fontSize: 14 }}>
          {tr
            ? `${shelf.books.length} kitap · ${shelf.batches.length} parti — ${shelf.theme}`
            : `${shelf.books.length} books · ${shelf.batches.length} batches — ${shelf.theme}`}
        </p>

        <h2 style={{ color: GOLD, fontSize: 15, margin: '4px 0 8px', opacity: .9, letterSpacing: '.04em' }}>
          ✨ {tr ? 'Kürasyonlu Atlas Görünümleri' : 'Curated Atlas Views'}
        </h2>
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill,minmax(240px,1fr))', gap: 10, marginBottom: 22 }}>
          {curated.map((c) => (
            <button key={c.tab} onClick={() => { window.location.hash = `#${c.tab}`; }}
              style={{ ...card, borderColor: 'rgba(201,168,76,.45)', padding: '10px 14px', textAlign: 'left', cursor: 'pointer', color: 'inherit', transition: 'border-color .15s' }}
              onMouseEnter={(e) => (e.currentTarget.style.borderColor = GOLD)}
              onMouseLeave={(e) => (e.currentTarget.style.borderColor = 'rgba(201,168,76,.45)')}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'baseline', gap: 8 }}>
                <div style={{ fontWeight: 700, fontSize: 14 }}>{c.name}</div>
                {c.ar && <div dir="rtl" style={{ fontFamily: "'Amiri',serif", fontSize: 15, color: GOLD }}>{c.ar}</div>}
              </div>
              <div style={{ fontSize: 11.5, opacity: .7, margin: '2px 0 6px' }}>{c.by}</div>
              <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: 11 }}>
                <span style={{ opacity: .85 }}>{c.caps}</span>
                <span style={{ ...chip, marginRight: 0 }}>{fmtCount(c.key)}</span>
              </div>
            </button>
          ))}
        </div>

        <h2 style={{ color: GOLD, fontSize: 15, margin: '4px 0 8px', opacity: .9, letterSpacing: '.04em' }}>
          📖 {tr ? 'Çekirdek Külliyat — tam metin' : 'Core canon — full text'}
        </h2>
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill,minmax(320px,1fr))', gap: 14 }}>
          {shelf.books.map((b) => (
            <button key={b.pid} onClick={() => openBook(b.pidnum)}
              style={{ ...card, padding: '16px 18px', textAlign: 'right', cursor: 'pointer', color: 'inherit', transition: 'border-color .15s' }}
              onMouseEnter={(e) => (e.currentTarget.style.borderColor = GOLD)}
              onMouseLeave={(e) => (e.currentTarget.style.borderColor = 'rgba(201,168,76,.25)')}>
              <div dir="rtl" style={{ fontFamily: "'Amiri','Scheherazade New',serif", fontSize: 24, color: GOLD, lineHeight: 1.4 }}>
                {b.title_ar || b.name_tr}
              </div>
              <div dir="ltr" style={{ textAlign: 'left', fontWeight: 700, fontSize: 15, margin: '6px 0 4px' }}>{b.name_tr}</div>
              <div dir="ltr" style={{ textAlign: 'left', fontSize: 12, opacity: .7, marginBottom: 8 }}>
                {b.n_sections.toLocaleString('tr-TR')} {tr ? 'bölüm' : 'sections'} · {b.total_words.toLocaleString('tr-TR')} {tr ? 'kelime' : 'words'}
              </div>
              <div dir="ltr" style={{ textAlign: 'left', fontSize: 12, opacity: .85, fontStyle: 'italic' }}>🗺 {b.atlas_role}</div>
            </button>
          ))}
        </div>
      </div>
    );
  }

  /* ═══════════ OKUYUCU (3 sütun) ═══════════ */
  const tocEntry = book.sections[secIdx] || {};
  return (
    <div style={{ display: 'grid', gridTemplateColumns: '290px 1fr 280px', gap: 0, height: 'calc(100vh - 120px)', minHeight: 420 }}>
      {/* SOL: bölüm ağacı */}
      <aside style={{ borderRight: '1px solid rgba(201,168,76,.2)', display: 'flex', flexDirection: 'column', overflow: 'hidden' }}>
        <div style={{ padding: '10px 12px' }}>
          <button onClick={() => { setBook(null); window.location.hash = 'library'; }}
            style={{ background: 'none', border: 'none', color: GOLD, cursor: 'pointer', fontSize: 13, padding: 0 }}>
            ← {tr ? 'Kütüphane' : 'Library'}
          </button>
          <input value={tocQuery} onChange={(e) => setTocQuery(e.target.value)}
            placeholder={tr ? 'Bölüm ara…' : 'Search sections…'}
            style={{ width: '100%', marginTop: 8, padding: '6px 10px', borderRadius: 8, border: '1px solid rgba(201,168,76,.3)', background: 'rgba(0,0,0,.3)', color: 'inherit', fontSize: 13 }} />
          <div style={{ fontSize: 11, opacity: .6, marginTop: 4 }}>
            {filteredToc.length.toLocaleString('tr-TR')} / {book.n_sections.toLocaleString('tr-TR')} {tr ? 'bölüm' : 'sections'}
          </div>
        </div>
        <div style={{ overflowY: 'auto', flex: 1 }}>
          {filteredToc.slice(0, 800).map((s) => (
            <button key={s.i} onClick={() => gotoSec(s.i)}
              style={{
                display: 'block', width: '100%', textAlign: 'right', padding: `6px 12px 6px ${8 + (s.level - 1) * 10}px`,
                background: s.i === secIdx ? 'rgba(201,168,76,.18)' : 'none', border: 'none',
                borderRight: s.i === secIdx ? `3px solid ${GOLD}` : '3px solid transparent',
                color: 'inherit', cursor: 'pointer', fontSize: 13, lineHeight: 1.5,
              }} dir="rtl">
              <span style={{ fontFamily: "'Amiri',serif" }}>{s.title}</span>
              {s.page && <span dir="ltr" style={{ ...chip, fontSize: 9, marginRight: 0, marginLeft: 6 }}>{s.page}</span>}
            </button>
          ))}
          {filteredToc.length > 800 && <div style={{ padding: 12, fontSize: 12, opacity: .6 }}>… {tr ? 'daraltmak için arayın' : 'search to narrow'}</div>}
        </div>
      </aside>

      {/* ORTA: okuyucu / kitap haritası */}
      <section ref={readerRef} style={{ overflowY: 'auto', padding: '18px 34px 60px', position: 'relative' }}>
        <div style={{ display: 'flex', justifyContent: 'center', gap: 6, marginBottom: 10 }}>
          <button onClick={() => setMode('text')}
            style={{ ...chip, cursor: 'pointer', border: 'none', background: mode === 'text' ? GOLD : 'rgba(201,168,76,.15)', color: mode === 'text' ? '#0f1419' : GOLD, fontWeight: 700 }}>
            📖 {tr ? 'Metin' : 'Text'}
          </button>
          <button onClick={() => setMode('map')} disabled={!mentions}
            style={{ ...chip, cursor: mentions ? 'pointer' : 'default', border: 'none', background: mode === 'map' ? GOLD : 'rgba(201,168,76,.15)', color: mode === 'map' ? '#0f1419' : GOLD, fontWeight: 700, opacity: mentions ? 1 : .4 }}>
            🗺 {tr ? 'Kitap Haritası' : 'Book Map'}{mentions ? ` (${mentions.n_geocoded.toLocaleString('tr-TR')})` : ''}
          </button>
          {layerData && (
            <button onClick={() => setMode('layer')}
              style={{ ...chip, cursor: 'pointer', border: 'none', background: mode === 'layer' ? GOLD : 'rgba(201,168,76,.15)', color: mode === 'layer' ? '#0f1419' : GOLD, fontWeight: 700 }}>
              {({ structures: '🏛', entries: '🗺', routes: '🛤', regions: '🌍' }[layerData.kind] || '⚔️')} {tr ? ({ structures: 'Yapılar', entries: 'Maddeler', events: 'Olaylar', routes: 'Yollar', regions: 'Bölgeler' }[layerData.kind] || 'Katman') : ({ structures: 'Structures', entries: 'Entries', events: 'Events', routes: 'Routes', regions: 'Regions' }[layerData.kind] || 'Layer')} ({layerData.records.length})
            </button>
          )}
          {stopsDraft && (
            <button onClick={() => setMode('route')}
              style={{ ...chip, cursor: 'pointer', border: 'none', background: mode === 'route' ? GOLD : 'rgba(201,168,76,.15)', color: mode === 'route' ? '#0f1419' : GOLD, fontWeight: 700 }}>
              🧭 {tr ? 'Rota' : 'Route'} ({stopsDraft.stops.length})
            </button>
          )}
          {(mentions || layerData) && (
            <button onClick={() => setMode('stats')}
              style={{ ...chip, cursor: 'pointer', border: 'none', background: mode === 'stats' ? GOLD : 'rgba(201,168,76,.15)', color: mode === 'stats' ? '#0f1419' : GOLD, fontWeight: 700 }}>
              📊 {tr ? 'İstatistik' : 'Stats'}
            </button>
          )}
        </div>
        {(mode === 'map' || mode === 'route' || mode === 'layer') && (
          <div ref={mapElRef} style={{ height: 'calc(100vh - 240px)', minHeight: 380, borderRadius: 10, border: '1px solid rgba(201,168,76,.3)' }} />
        )}
        {mode === 'stats' && bookStats && (
          <div style={{ maxWidth: 760, margin: '0 auto' }}>
            {/* sayı kutuları — hepsi veriden */}
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit,minmax(130px,1fr))', gap: 10, marginBottom: 18 }}>
              {[
                [book.n_sections, tr ? 'bölüm' : 'sections'],
                [book.total_words, tr ? 'kelime' : 'words'],
                mentions && [mentions.n_places, tr ? 'anılan yer' : 'places'],
                mentions && [mentions.n_geocoded, tr ? 'koordinatlı yer' : 'geocoded'],
                layerData && [bookStats.nLayer, ({ structures: tr ? 'yapı' : 'structures', entries: tr ? 'madde' : 'entries', events: tr ? 'olay' : 'events', routes: tr ? 'yol' : 'routes', regions: tr ? 'bölge' : 'regions' }[layerData.kind] || (tr ? 'katman kaydı' : 'layer records'))],
              ].filter(Boolean).map(([nVal, lbl]) => (
                <div key={lbl} style={{ ...card, padding: '12px 10px', textAlign: 'center' }}>
                  <div style={{ color: GOLD, fontSize: 22, fontWeight: 700 }}>{Number(nVal).toLocaleString('tr-TR')}</div>
                  <div style={{ fontSize: 11, opacity: .7 }}>{lbl}</div>
                </div>
              ))}
            </div>
            {/* katman tür dağılımı */}
            {bookStats.kinds.length > 1 && (
              <div style={{ ...card, padding: '12px 16px', marginBottom: 18 }}>
                <div style={{ color: GOLD, fontSize: 13, fontWeight: 700, marginBottom: 8 }}>
                  {tr ? 'Katman tür dağılımı' : 'Layer kind distribution'}
                </div>
                <div style={{ display: 'flex', flexWrap: 'wrap', gap: 6 }}>
                  {bookStats.kinds.map(([k, c]) => (
                    <span key={k} style={{ ...chip, background: 'rgba(0,0,0,.25)', border: `1px solid ${LAYER_COLORS[k] || '#aaa'}`, color: LAYER_COLORS[k] || '#ccc', marginRight: 0 }}>
                      {k} · {c.toLocaleString('tr-TR')}
                    </span>
                  ))}
                </div>
              </div>
            )}
            {/* ilk 20 yer — anılma sayısı barları */}
            {bookStats.topPlaces.length > 0 && (
              <div style={{ ...card, padding: '12px 16px' }}>
                <div style={{ color: GOLD, fontSize: 13, fontWeight: 700, marginBottom: 10 }}>
                  {tr ? 'En çok anılan yerler' : 'Most mentioned places'}
                </div>
                {bookStats.topPlaces.map((pl) => (
                  <button key={pl.pid} onClick={() => setMode('map')}
                    title={tr ? 'Kitap haritasında gör' : 'View on book map'}
                    style={{ display: 'grid', gridTemplateColumns: '150px 1fr 48px', alignItems: 'center', gap: 8, width: '100%', background: 'none', border: 'none', cursor: 'pointer', color: 'inherit', padding: '3px 0' }}>
                    <span dir="rtl" style={{ fontFamily: "'Amiri',serif", fontSize: 15, textAlign: 'left', overflow: 'hidden', whiteSpace: 'nowrap', textOverflow: 'ellipsis' }}>{pl.name}</span>
                    <span style={{ height: 8, borderRadius: 4, background: 'rgba(201,168,76,.18)', overflow: 'hidden' }}>
                      <span style={{ display: 'block', height: '100%', width: `${Math.max(3, (pl.total / bookStats.maxTotal) * 100)}%`, background: GOLD, borderRadius: 4 }} />
                    </span>
                    <span style={{ fontSize: 11, opacity: .8, textAlign: 'right', fontVariantNumeric: 'tabular-nums' }}>{pl.total.toLocaleString('tr-TR')}</span>
                  </button>
                ))}
              </div>
            )}
          </div>
        )}
        {mode === 'text' && (
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 14 }}>
          <button disabled={secIdx <= 0} onClick={() => gotoSec(secIdx - 1)}
            style={{ ...chip, cursor: secIdx > 0 ? 'pointer' : 'default', border: 'none', opacity: secIdx > 0 ? 1 : .35 }}>
            ← {tr ? 'Önceki' : 'Prev'}
          </button>
          <h2 dir="rtl" style={{ fontFamily: "'Amiri',serif", color: GOLD, fontSize: 21, margin: 0, textAlign: 'center', flex: 1, padding: '0 12px' }}>
            {tocEntry.title}
          </h2>
          <button disabled={secIdx >= book.n_sections - 1} onClick={() => gotoSec(secIdx + 1)}
            style={{ ...chip, cursor: secIdx < book.n_sections - 1 ? 'pointer' : 'default', border: 'none', opacity: secIdx < book.n_sections - 1 ? 1 : .35 }}>
            {tr ? 'Sonraki' : 'Next'} →
          </button>
        </div>
        )}
        {mode === 'text' && !section && <div style={{ opacity: .6, textAlign: 'center', padding: 40 }}>{tr ? 'Bölüm yükleniyor…' : 'Loading…'}</div>}
        {mode === 'text' && section && section._error && <div style={{ opacity: .7, textAlign: 'center', padding: 40 }}>{tr ? 'Bu bölüm yüklenemedi (dosya eksik olabilir). Başka bir bölüm seçin.' : 'This section could not be loaded.'}</div>}
        {mode === 'text' && section && section.paras.map((p, i) => (
          <p key={i} id={p.p ? `para-${p.p}` : undefined} dir="rtl" style={{ fontFamily: "'Amiri','Scheherazade New',serif", fontSize: 19, lineHeight: 2.05, margin: '0 0 14px', textAlign: 'justify' }}>
            {p.p && (
              <a href={`#library?book=${book.pidnum}&sec=${secIdx}&p=${p.p}`}
                title={tr ? 'Sayfa çapası — link kopyalanabilir' : 'Page anchor'}
                style={{ ...chip, fontSize: 10, textDecoration: 'none', verticalAlign: 'middle', float: 'left', marginTop: 8 }}>
                {p.p}
              </a>
            )}
            {p.t}
          </p>
        ))}
      </section>

      {/* SAĞ: kimlik kartı */}
      <aside style={{ borderLeft: '1px solid rgba(201,168,76,.2)', overflowY: 'auto', padding: '14px 14px 40px' }}>
        <div dir="rtl" style={{ fontFamily: "'Amiri',serif", fontSize: 23, color: GOLD, lineHeight: 1.45 }}>{book.title_ar}</div>
        <div style={{ fontWeight: 700, fontSize: 14, margin: '6px 0 2px' }}>{book.name_tr}</div>
        <div style={{ fontSize: 12, opacity: .7, marginBottom: 10 }}>{book.title_tr}</div>
        {book.author && (
          <div style={{ ...card, padding: '10px 12px', fontSize: 12, marginBottom: 10 }}>
            <div style={{ fontSize: 11, textTransform: 'uppercase', letterSpacing: '.06em', opacity: .65, marginBottom: 4 }}>
              ✍️ {tr ? 'Müellif' : 'Author'}
            </div>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'baseline', gap: 8 }}>
              <b>{book.author.name_tr}</b>
              {book.author.name_ar && <span dir="rtl" style={{ fontFamily: "'Amiri',serif", fontSize: 15, color: GOLD }}>{book.author.name_ar}</span>}
            </div>
            {(book.author.death_ah || book.author.death_ce) && (
              <div style={{ opacity: .75, marginTop: 2 }}>
                {tr ? 'ö.' : 'd.'} {book.author.death_ah ? `${book.author.death_ah} H` : ''}{book.author.death_ah && book.author.death_ce ? ' / ' : ''}{book.author.death_ce ? `${book.author.death_ce} M` : ''}
              </div>
            )}
            <div style={{ marginTop: 6 }}>
              {book.author.dia_slug && (
                <a href={`#dia?search=${encodeURIComponent(book.author.name_tr || book.author.dia_slug)}`}
                  style={{ ...chip, textDecoration: 'none', cursor: 'pointer' }}>
                  {tr ? "DİA'da" : 'in TDV'} →
                </a>
              )}
              {book.author.alam_id && (
                <a href={`#alam?id=${book.author.alam_id}`}
                  style={{ ...chip, textDecoration: 'none', cursor: 'pointer' }}>
                  el-Aʿlâm →
                </a>
              )}
            </div>
          </div>
        )}
        {book.description_tr && (
          <div style={{ ...card, padding: '10px 12px', fontSize: 12.5, lineHeight: 1.65, marginBottom: 10 }}>
            {tr ? book.description_tr : (book.description_en || book.description_tr)}
          </div>
        )}
        <div style={{ ...card, padding: '10px 12px', fontSize: 12, marginBottom: 10 }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', padding: '3px 0' }}>
            <span style={{ opacity: .65 }}>{tr ? 'Bölüm' : 'Sections'}</span><b>{book.n_sections.toLocaleString('tr-TR')}</b>
          </div>
          <div style={{ display: 'flex', justifyContent: 'space-between', padding: '3px 0' }}>
            <span style={{ opacity: .65 }}>{tr ? 'Kelime' : 'Words'}</span><b>{book.total_words.toLocaleString('tr-TR')}</b>
          </div>
          <div style={{ display: 'flex', justifyContent: 'space-between', padding: '3px 0' }}>
            <span style={{ opacity: .65 }}>{tr ? 'Sürüm' : 'Version'}</span>
            <b style={{ fontSize: 10, maxWidth: 150, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>{book.version_file}</b>
          </div>
          {book.composition && (book.composition.ah || book.composition.ce) && (
            <div style={{ display: 'flex', justifyContent: 'space-between', padding: '3px 0' }}>
              <span style={{ opacity: .65 }}>{tr ? 'Telif' : 'Composed'}</span>
              <b>{book.composition.approx === 'before' ? (tr ? '≤ ' : '≤ ') : ''}{book.composition.ah ? `${book.composition.ah} H` : ''}{book.composition.ah && book.composition.ce ? ' / ' : ''}{book.composition.ce ? `${book.composition.ce} M` : ''}</b>
            </div>
          )}
          <div style={{ display: 'flex', justifyContent: 'space-between', padding: '3px 0' }}>
            <span style={{ opacity: .65 }}>{tr ? 'Kalıcı kimlik' : 'PID'}</span><b style={{ fontSize: 10 }}>{book.pid}</b>
          </div>
        </div>
        {mentions && mentions.sec_pids && mentions.sec_pids[String(secIdx)] && (
          <div style={{ ...card, padding: '10px 12px', marginBottom: 10 }}>
            <div style={{ fontSize: 11, textTransform: 'uppercase', letterSpacing: '.06em', opacity: .65, marginBottom: 6 }}>
              📍 {tr ? 'Bu bölümdeki yerler' : 'Places in this section'}
            </div>
            <div dir="rtl">
              {(mentions.sections[String(secIdx)] || []).map((nm, k) => (
                <button key={k} onClick={() => setMode('map')}
                  title={tr ? 'Kitap haritasında gör' : 'Show on book map'}
                  style={{ ...chip, cursor: 'pointer', border: 'none', fontFamily: "'Amiri',serif", fontSize: 13 }}>
                  {nm}
                </button>
              ))}
            </div>
          </div>
        )}
        {book.atlas_role && (
          <div style={{ ...card, padding: '10px 12px', fontSize: 12, marginBottom: 10, fontStyle: 'italic' }}>
            🗺 {book.atlas_role}
          </div>
        )}
        <a href={openitiRepoUrl(book.uri)} target="_blank" rel="noreferrer"
          style={{ ...chip, textDecoration: 'none', display: 'inline-block' }}>
          OpenITI ↗
        </a>
        <div style={{ fontSize: 10, opacity: .5, marginTop: 14, lineHeight: 1.6 }}>
          {tr
            ? 'Metin: OpenITI corpus (CC BY-NC-SA). Sayfa çapaları basılı neşrin cilt/sayfa numaralarıdır.'
            : 'Text: OpenITI corpus (CC BY-NC-SA). Page anchors reference the printed edition.'}
        </div>
      </aside>
    </div>
  );
}
