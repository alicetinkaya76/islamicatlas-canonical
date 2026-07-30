/**
 * SynchronicStrips.jsx — H30: Alatlı senkronik atlası ("aynı tarihte Doğu ↔ Batı").
 *
 * Alatlı'nın (Tarihe Yön Veren Metinler) biricik katkısı senkronik bakış:
 * bir yılda İslam dünyasında kim yaşıyordu, aynı anda Batı'da kim?
 * Örnek (veriden): Mevlânâ ö.1273 ↔ Thomas Aquinas ö.1274.
 *
 * İKİ ŞERİT, İKİ KAYNAK DURUMU (ekranda da yazar):
 *   ▲ DOĞU  — canonical mağaza (pid'li, 227 kişi) → tıkla: Ulema Havuzu'nda ara
 *   ▼ BATI  — yan-tablo (MINT EDİLMEDİ, pid YOK, 274 kişi) → tıkla: Wikidata
 *
 * Veri: /view-data/alatli_synchronic.json (build_alatli_synchronic.py).
 * Telif: `publication_gate: "alatli"` — araştırma sürümü; kamu dump'a girmez.
 * Tarihsiz kayıt ÇİZİLMEZ (uydurma yok); yaşam aralığı yoksa nokta gösterilir.
 */
import { useEffect, useRef, useState, useMemo } from 'react';
import L from 'leaflet';
import 'leaflet/dist/leaflet.css';

const NAMED_LH = 13;        // H42: ad yazılabilen satır yüksekliği (LH=4 çok ince)
const GOLD = '#c9a84c';     // Doğu (v1 dili)
const CYAN = '#38bdf8';     // Batı (canonical/dış katman rengi — H26/H28 ile tutarlı)

export default function SynchronicStrips({ lang = 'tr' }) {
  const tr = lang !== 'en';
  const [data, setData] = useState(null);
  const [err, setErr] = useState(false);
  const [year, setYear] = useState(1300);
  const [hover, setHover] = useState(null);
  const [showMap, setShowMap] = useState(false);   // H32: seçili yılın haritası
  /* H42: ekran "flu renkli çizgiler"den ibaretti — 670 isimsiz çubuk, tıklayınca
     sessizce #scholars'a atıyordu (kullanıcı nereye gittiğini anlamıyordu).
     İki ekleme: (a) SEÇİLİ KAYIT paneli — tıklama artık yönlendirmez, kim
     olduğunu gösterir ve nereye gidileceğini AÇIK düğmeyle sorar; (b) YALNIZ
     ÇAĞDAŞLAR kipi — seçili yılda yaşamayanlar gizlenir, kalan az sayıda çubuğun
     yanına ADI YAZILIR. Ancak o zaman şerit "okunur" hale geliyor. */
  const [sel, setSel] = useState(null);
  const [onlyAlive, setOnlyAlive] = useState(false);
  const wrapRef = useRef(null);
  const mapElRef = useRef(null);
  const mapRef = useRef(null);
  const [w, setW] = useState(1200);

  useEffect(() => {
    fetch('/view-data/alatli_synchronic.json')
      .then((r) => (r.ok ? r.json() : Promise.reject(new Error(String(r.status)))))
      .then(setData)
      .catch(() => setErr(true));
  }, []);

  useEffect(() => {
    if (!wrapRef.current) return undefined;
    const ro = new ResizeObserver((es) => setW(Math.max(600, es[0].contentRect.width)));
    ro.observe(wrapRef.current);
    return () => ro.disconnect();
  }, [data]);

  /* Görüntü penceresi: veri -740..2007'ye uzanıyor ama okunabilirlik için
     İslam tarihi odağı (600–1950). Dışarıda kalanlar kenara kırpılır, SAYILIR. */
  const X0 = 600, X1 = 1950;
  const ml = 54, mr = 16;
  const x = (yr) => ml + ((Math.min(Math.max(yr, X0), X1) - X0) / (X1 - X0)) * (w - ml - mr);

  /* Şerit içi "lane" paketleme: çakışan yaşam çizgileri alt alta yığılır. */
  const packed = useMemo(() => {
    if (!data) return { bize: [], batiya: [], lanesE: 1, lanesW: 1 };
    const pack = (rows) => {
      const laneEnd = [];
      const out = [];
      rows.forEach((r) => {
        const b = r.birth_ce ?? r.anchor_ce;
        const d = r.death_ce ?? r.anchor_ce;
        const x0 = Math.min(b, d), x1 = Math.max(b, d);
        let lane = laneEnd.findIndex((e) => e < x0 - 12);
        if (lane === -1) { lane = laneEnd.length; laneEnd.push(x1); }
        else laneEnd[lane] = x1;
        out.push({ ...r, _x0: x0, _x1: x1, _lane: lane });
      });
      return { rows: out, lanes: Math.max(1, laneEnd.length) };
    };
    const e = pack(data.bize), b = pack(data.batiya);
    return { bize: e.rows, batiya: b.rows, lanesE: e.lanes, lanesW: b.lanes };
  }, [data]);

  /* H32: seçili YILDA yaşayan + KOORDİNATLI kişilerin haritası.
     Koordinat upstream'den aktarıldı (526 kişi); koordinatsız kayıt haritada
     GÖSTERİLMEZ (uydurma yok) — sayısı panelde yazar. */
  useEffect(() => {
    if (!showMap || !data || !mapElRef.current) return undefined;
    if (mapRef.current) { mapRef.current.remove(); mapRef.current = null; }
    const map = L.map(mapElRef.current, { scrollWheelZoom: false, zoomControl: true });
    L.tileLayer('https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png',
      { attribution: '© OpenStreetMap · CARTO', subdomains: 'abcd' }).addTo(map);
    const pts = [];
    [['bize', GOLD], ['batiya', CYAN]].forEach(([side, color]) => {
      (data[side] || []).forEach((r) => {
        if (r.lat == null || r.lon == null) return;
        const b = r.birth_ce, d = r.death_ce;
        const isAlive = (b != null && d != null)
          ? (year >= b && year <= d)
          : Math.abs(r.anchor_ce - year) <= 25;
        if (!isAlive) return;
        const mk = L.circleMarker([r.lat, r.lon], {
          radius: 6, weight: 1.2, color: '#0b1016', fillColor: color, fillOpacity: .9,
        }).addTo(map);
        mk.bindPopup(
          `<div style="font-weight:700;color:${color}">${r.name}</div>
           <div style="font-size:11px;opacity:.8">${r.birth_ce ?? '?'} – ${r.death_ce ?? '?'}${r.place ? ' · ' + r.place : ''}</div>
           ${r.cite ? `<div style="font-size:11px;color:#e0b34d">📖 ${r.cite.vol}${r.cite.book_page != null ? ' · s.' + r.cite.book_page : ''}</div>` : ''}`,
        );
        pts.push([r.lat, r.lon]);
      });
    });
    if (pts.length) map.fitBounds(L.latLngBounds(pts).pad(0.2), { maxZoom: 6 });
    else map.setView([33, 35], 3);
    mapRef.current = map;
    return () => { if (mapRef.current) { mapRef.current.remove(); mapRef.current = null; } };
  }, [showMap, data, year]);

  if (err) return <div style={{ padding: 30, opacity: .7 }}>{tr ? 'Senkronik veri bulunamadı — `python3 pipelines/frontend/build_alatli_synchronic.py` koşun.' : 'Synchronic data missing.'}</div>;
  if (!data) return <div style={{ padding: 30, opacity: .6 }}>{tr ? 'Senkronik atlas yükleniyor…' : 'Loading…'}</div>;

  /* Yerleşim: 358 + 308 kayıt lane-paketlenince şerit ekranı taşırıyordu
     (BATIYA görünmez oluyordu). Şerit başına lane TAVANI + ince lane ile İKİSİ
     DE aynı ekranda kalır; tavanı aşan lane'ler modulo ile sarılır (çizgiler
     üst üste binebilir — kayıt KAYBOLMAZ, tooltip/tıklama çalışır). */
  const LH = 4;
  const MAX_LANES = 42;
  const lanesE = Math.min(packed.lanesE, MAX_LANES);
  const lanesW = Math.min(packed.lanesW, MAX_LANES);

  const alive = (r) => {
    const b = r.birth_ce, d = r.death_ce;
    if (b != null && d != null) return year >= b && year <= d;
    return Math.abs(r.anchor_ce - year) <= 25;    // tek tarihli: ±25 yıl "çağdaş"
  };
  const nE = packed.bize.filter(alive).length;
  const nW = packed.batiya.filter(alive).length;

  /* Yükseklik KİPE bağlıdır: yalnız-çağdaşlar kipinde satır sayısı o yıl
     yaşayanların sayısıdır ve her satır ad yazacak kadar yüksektir. */
  const hE = onlyAlive ? Math.min(nE, MAX_LANES) * NAMED_LH + 26 : lanesE * LH + 26;
  const hW = onlyAlive ? Math.min(nW, MAX_LANES) * NAMED_LH + 26 : lanesW * LH + 26;
  const axisY = hE + 34;
  const H = hE + 68 + hW;

  /* Yalnız-çağdaşlar kipinde satır sırası: o yıl yaşayanların kendi içindeki
     sırası (özgün lane'ler seyrek kalır, ekranın yarısı boş görünürdü).

     DÜZ HESAP, useMemo DEĞİL: bu satır erken return'lerin (err / !data)
     ARDINDA geliyor; oraya hook koymak render'lar arasında hook sayısını
     değiştirir ve bileşeni çökertir. H17'de AlamView tam bu yüzden soğuk
     açılışta çöküyordu — aynı hataya düşmeyelim. 670 kayıt için maliyet
     ihmal edilebilir. */
  const aliveIdx = new Map();
  for (const rows of [packed.bize, packed.batiya]) {
    let k = 0;
    for (const r of rows) if (alive(r)) aliveIdx.set(r, k++);
  }
  const aliveIndex = (_rows, r) => aliveIdx.get(r) ?? 0;

  const strip = (rows, side, topY, color) => rows.map((r, i) => {
    const isAlive = alive(r);
    if (onlyAlive && !isAlive) return null;          // H42: ekranı temizle
    const x0 = x(r._x0), x1 = x(r._x1);
    /* Yalnız-çağdaşlar kipinde satırlar SIKIŞTIRILIR (özgün lane'ler seyrek
       kalırdı) ve her satıra ad yazacak yer açılır. */
    const yy = onlyAlive
      ? topY + (aliveIndex(rows, r) % MAX_LANES) * NAMED_LH
      : topY + (r._lane % MAX_LANES) * LH;
    const wd = Math.max(2, x1 - x0);
    const isSel = sel?.r === r;
    return (
      <g key={`${side}-${i}`}>
      {onlyAlive && (
        <text x={Math.min(x1 + 6, w - 120)} y={yy + NAMED_LH - 3}
          fill={color} fontSize={10} opacity={.92} style={{ pointerEvents: 'none' }}>
          {r.name}
        </text>
      )}
      <rect x={x0} y={yy} width={wd} height={(onlyAlive ? NAMED_LH : LH) - 2} rx={1.5}
        fill={color} opacity={isSel ? 1 : (isAlive ? 0.95 : 0.22)}
        stroke={isSel ? '#fff' : 'none'} strokeWidth={isSel ? 1.2 : 0}
        style={{ cursor: 'pointer' }}
        onMouseEnter={(ev) => setHover({ r, x: ev.clientX, y: ev.clientY, side })}
        onMouseLeave={() => setHover(null)}
        onClick={() => setSel({ r, side })} />
      </g>
    );
  });

  return (
    <div ref={wrapRef} style={{ padding: '4px 10px 20px' }}>
      {/* ── Yıl kaydırıcı + canlı sayaç ── */}
      <div style={{ display: 'flex', alignItems: 'center', gap: 14, flexWrap: 'wrap', marginBottom: 8 }}>
        <span style={{ color: GOLD, fontWeight: 700, fontSize: 15, minWidth: 92 }}>{year} <span style={{ opacity: .6, fontSize: 12 }}>M.</span></span>
        <input type="range" min={X0} max={X1} value={year} step={1}
          onChange={(e) => setYear(+e.target.value)}
          style={{ flex: 1, minWidth: 260, accentColor: GOLD }} />
        {/* H42: ekranı okunur kılan asıl anahtar. Kapalıyken 670 isimsiz çubuk
            var; açıkken yalnız o yıl yaşayanlar kalır ve HER ÇUBUĞUN YANINA ADI
            YAZILIR. "Flu renkli çizgiler" ancak böyle okunabilir hale geliyor. */}
        <button onClick={() => setOnlyAlive((p) => !p)}
          title={tr ? 'Yalnız seçili yılda yaşayanları göster — adlarıyla'
                    : 'Show only those alive in the selected year, with names'}
          style={{
            border: `1px solid ${onlyAlive ? GOLD : 'rgba(255,255,255,.18)'}`,
            background: onlyAlive ? 'rgba(201,168,76,.18)' : 'transparent',
            color: onlyAlive ? GOLD : '#a89b8c', borderRadius: 7,
            padding: '3px 9px', fontSize: 11.5, cursor: 'pointer', fontWeight: 600,
          }}>
          🔎 {tr ? 'Yalnız çağdaşlar (adlarıyla)' : 'Only contemporaries'}
        </button>
        <button onClick={() => setShowMap((p) => !p)}
          title={tr ? 'Seçili yılda yaşayanları haritada göster (yalnız koordinatlı kayıtlar)' : 'Map of those alive in the selected year'}
          style={{
            border: `1px solid ${showMap ? GOLD : 'rgba(255,255,255,.18)'}`,
            background: showMap ? 'rgba(201,168,76,.18)' : 'transparent',
            color: showMap ? GOLD : '#a89b8c', borderRadius: 7,
            padding: '3px 9px', fontSize: 11.5, cursor: 'pointer',
          }}>
          🗺 {tr ? 'Harita' : 'Map'}
        </button>
        <span style={{ fontSize: 12 }}>
          <span style={{ color: GOLD }}>▲ {tr ? 'Bize' : '“Bize”'} {nE}</span>
          <span style={{ opacity: .4, margin: '0 6px' }}>·</span>
          <span style={{ color: CYAN }}>▼ {tr ? 'Batıya' : '“Batıya”'} {nW}</span>
          <span style={{ opacity: .55, marginLeft: 6 }}>{tr ? 'çağdaş' : 'contemporaries'}</span>
        </span>
      </div>

      {/* H32: seçili yılın haritası (yalnız koordinatlı kayıtlar) */}
      {showMap && (
        <div style={{ marginBottom: 10 }}>
          <div ref={mapElRef} style={{
            height: 300, borderRadius: 10, border: '1px solid rgba(201,168,76,.3)',
          }} />
          <div style={{ fontSize: 10.5, opacity: .55, marginTop: 3 }}>
            {tr
              ? `Haritada yalnız KOORDİNATLI kayıtlar var (${data.counts.with_coords}/${data.counts.bize + data.counts.batiya}); koordinatsız olanlar uydurulmadı.`
              : `Only geocoded records are mapped (${data.counts.with_coords}); the rest are not invented.`}
          </div>
        </div>
      )}

      {/* H42: SEÇİLİ KAYIT. Önceden tıklama sessizce #scholars'a atıyordu ve
          kullanıcı nereye gittiğini/ne gördüğünü anlamıyordu. Artık tıklama
          kimliği burada açar; gidilecek yer AÇIK DÜĞMEYLE sorulur. */}
      {sel && (
        <div style={{
          border: `1px solid ${sel.side === 'bize' ? GOLD : CYAN}`, borderRadius: 10,
          padding: '10px 12px', marginBottom: 10, background: 'rgba(255,255,255,.03)',
        }}>
          <div style={{ display: 'flex', alignItems: 'baseline', gap: 8, flexWrap: 'wrap' }}>
            <b style={{ color: sel.side === 'bize' ? GOLD : CYAN, fontSize: 15 }}>{sel.r.name}</b>
            <span style={{ fontSize: 12, opacity: .7 }}>
              {sel.r.birth_ce != null ? sel.r.birth_ce : '?'} – {sel.r.death_ce != null ? sel.r.death_ce : '?'}
              {sel.r.place ? ` · ${sel.r.place}` : ''}
            </span>
            <span style={{ fontSize: 11, opacity: .55 }}>
              {sel.side === 'bize' ? (tr ? '▲ “Bize” kanonunda' : '▲ in “Bize”')
                                   : (tr ? '▼ “Batıya” kanonunda' : '▼ in “Batıya”')}
              {sel.r.both && (tr ? ' · her ikisinde' : ' · in both')}
            </span>
            <button onClick={() => setSel(null)}
              style={{ marginLeft: 'auto', border: 'none', background: 'none',
                color: '#a89b8c', cursor: 'pointer', fontSize: 15 }}>✕</button>
          </div>
          {sel.r.cite && (
            <div style={{ fontSize: 11.5, opacity: .75, marginTop: 5 }}>
              📖 {sel.r.cite.vol}{sel.r.cite.book_page != null && ` · s.${sel.r.cite.book_page}`}
              {sel.r.cite_count > 1 && <span style={{ opacity: .6 }}> (+{sel.r.cite_count - 1} {tr ? 'geçiş daha' : 'more'})</span>}
              {sel.r.cite.text && <div style={{ opacity: .7, marginTop: 2 }}>{String(sel.r.cite.text).slice(0, 160)}</div>}
            </div>
          )}
          {/* H43: bağ ADA göre değil PID'e göre kurulur. "Muhammed" gibi genel
              bir adla arama anlamsız sonuç veriyordu (#scholars?q=Muhammed);
              pid tek bir kişiyi adresler ve havuz modunu doğrudan açar. */}
          <div style={{ display: 'flex', gap: 8, marginTop: 9, flexWrap: 'wrap' }}>
            {sel.r.pid ? (
              <button onClick={() => { window.location.hash = `scholars?pid=${encodeURIComponent(sel.r.pid)}`; }}
                style={{ border: `1px solid ${GOLD}`, background: 'rgba(201,168,76,.12)', color: GOLD,
                  borderRadius: 7, padding: '4px 10px', fontSize: 11.5, cursor: 'pointer' }}>
                🎓 {tr ? 'Âlimler havuzunda aç' : 'Open in scholar pool'}
              </button>
            ) : (
              <span style={{ fontSize: 11, opacity: .55 }}>
                {tr ? 'Merkezî defterde karşılığı yok — yalnız antolojide.'
                    : 'No canonical record — anthology only.'}
              </span>
            )}
            {sel.r.qid && (
              <button onClick={() => window.open(`https://www.wikidata.org/wiki/${sel.r.qid}`, '_blank', 'noopener')}
                style={{ border: '1px solid rgba(255,255,255,.2)', background: 'none', color: '#a89b8c',
                  borderRadius: 7, padding: '4px 10px', fontSize: 11.5, cursor: 'pointer' }}>
                ↗ Wikidata ({sel.r.qid})
              </button>
            )}
          </div>
        </div>
      )}

      <svg width="100%" height={H} style={{ display: 'block' }}>
        {/* yüzyıl ızgarası */}
        {Array.from({ length: Math.floor((X1 - X0) / 100) + 1 }, (_, i) => X0 + i * 100).map((yr) => (
          <g key={yr}>
            <line x1={x(yr)} x2={x(yr)} y1={0} y2={H - 18} stroke="rgba(255,255,255,.07)" />
            <text x={x(yr)} y={H - 5} fill="#8a8272" fontSize={10} textAnchor="middle">{yr}</text>
          </g>
        ))}

        {/* şerit etiketleri */}
        <text x={4} y={12} fill={GOLD} fontSize={11} fontWeight="700">▲ {tr ? 'BİZE' : '“BIZE”'}</text>
        <text x={4} y={axisY + 30} fill={CYAN} fontSize={11} fontWeight="700">▼ {tr ? 'BATIYA' : '“BATIYA”'}</text>

        {strip(packed.bize, 'bize', 18, GOLD)}
        <line x1={ml} x2={w - mr} y1={axisY} y2={axisY} stroke="rgba(201,168,76,.35)" />
        {strip(packed.batiya, 'batiya', axisY + 36, CYAN)}

        {/* seçili yıl imleci */}
        <line x1={x(year)} x2={x(year)} y1={0} y2={H - 18} stroke="#fff" strokeWidth={1.5} opacity={.75} />
      </svg>

      {hover && (
        <div style={{
          position: 'fixed', left: Math.min(hover.x + 12, window.innerWidth - 260), top: hover.y + 12,
          background: 'rgba(12,14,20,.97)', border: `1px solid ${hover.side === 'bize' ? GOLD : CYAN}`,
          borderRadius: 8, padding: '7px 10px', fontSize: 12, zIndex: 3000, maxWidth: 250, pointerEvents: 'none',
        }}>
          <div style={{ fontWeight: 700, color: hover.side === 'bize' ? GOLD : CYAN }}>{hover.r.name}</div>
          <div style={{ opacity: .8 }}>
            {hover.r.birth_ce != null ? hover.r.birth_ce : '?'} – {hover.r.death_ce != null ? hover.r.death_ce : '?'}
            {hover.r.place ? ` · ${hover.r.place}` : ''}
          </div>
          {/* H32: kaynağa in — Alatlı cilt + sayfa atfı */}
          {hover.r.cite && (
            <div style={{ fontSize: 11, marginTop: 4, color: '#e0b34d' }}>
              📖 {hover.r.cite.vol}
              {hover.r.cite.book_page != null && ` · s.${hover.r.cite.book_page}`}
              {hover.r.cite_count > 1 && (
                <span style={{ opacity: .6 }}> (+{hover.r.cite_count - 1})</span>
              )}
              {hover.r.cite.text && (
                <div style={{ opacity: .7, fontSize: 10.5, marginTop: 1 }}>
                  {String(hover.r.cite.text).slice(0, 90)}
                </div>
              )}
            </div>
          )}
          <div style={{ opacity: .55, fontSize: 11, marginTop: 3 }}>
            {hover.r.both && <span style={{ color: '#e0b34d' }}>{tr ? 'Her iki kanonda · ' : 'In both canons · '}</span>}
            {hover.r.pid
              ? (tr ? 'Merkezî defterde var — tıkla: havuzda ara' : 'In canonical store — click to search pool')
              : (tr ? 'Defterde yok (antolojide var) — tıkla: Wikidata' : 'Not in store — click: Wikidata')}
          </div>
        </div>
      )}

      {/* Dürüstlük + telif kapısı notu — EKRANDA */}
      <div style={{ fontSize: 11, opacity: .6, marginTop: 8, lineHeight: 1.6 }}>
        {tr
          ? `⚠ “Bize” / “Batıya” ALATLI'NIN EDİTÖRYEL ÇERÇEVESİDİR — coğrafi ya da etnik bir ayrım DEĞİLDİR (antolojinin kendi terimleri: hangi metinler “bize”, hangileri “Batı'ya” yön verdi). ⚠ Sayaçlar da ANTOLOJİNİN SEÇİM DAĞILIMIDIR, tarihsel üretkenlik ölçüsü değil. · Kaynak: ${data.source}; ${data.counts.total_source_rows} kayıttan ${data.counts.undated_dropped} tanesi tarihsiz olduğu için çizilmedi. “Bize” ${data.counts.bize} · “Batıya” ${data.counts.batiya} (${data.counts.both} kayıt her iki kanonda). Bunların ${data.counts.linked_to_store}'i merkezî deftere bağlı; kalanı yalnız antolojide (inceleme kuyruğu veya kapsam dışı). Alatlı-türevli kayıtlar araştırma sürümündedir; kamuya açık dağıtıma izin/karar gelene kadar girmez.`
          : `⚠ “Bize”/“Batıya” is Alatlı's EDITORIAL FRAME — not a geographic or ethnic division. Counters reflect the anthology's selection, not historical productivity. Source: ${data.source}; ${data.counts.undated_dropped} of ${data.counts.total_source_rows} rows undated (not drawn). ${data.counts.linked_to_store} linked to the canonical store. Alatlı-derived records stay in the research build.`}
      </div>
    </div>
  );
}
