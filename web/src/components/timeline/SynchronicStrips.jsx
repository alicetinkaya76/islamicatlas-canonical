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

const GOLD = '#c9a84c';     // Doğu (v1 dili)
const CYAN = '#38bdf8';     // Batı (canonical/dış katman rengi — H26/H28 ile tutarlı)

export default function SynchronicStrips({ lang = 'tr' }) {
  const tr = lang !== 'en';
  const [data, setData] = useState(null);
  const [err, setErr] = useState(false);
  const [year, setYear] = useState(1300);
  const [hover, setHover] = useState(null);
  const wrapRef = useRef(null);
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
    if (!data) return { dogu: [], bati: [], lanesE: 1, lanesW: 1 };
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
    const e = pack(data.dogu), b = pack(data.bati);
    return { dogu: e.rows, bati: b.rows, lanesE: e.lanes, lanesW: b.lanes };
  }, [data]);

  if (err) return <div style={{ padding: 30, opacity: .7 }}>{tr ? 'Senkronik veri bulunamadı — `python3 pipelines/frontend/build_alatli_synchronic.py` koşun.' : 'Synchronic data missing.'}</div>;
  if (!data) return <div style={{ padding: 30, opacity: .6 }}>{tr ? 'Senkronik atlas yükleniyor…' : 'Loading…'}</div>;

  const LH = 7;                                   // lane yüksekliği
  const hE = packed.lanesE * LH + 26;
  const hW = packed.lanesW * LH + 26;
  const axisY = hE + 34;
  const H = hE + 68 + hW;

  const alive = (r) => {
    const b = r.birth_ce, d = r.death_ce;
    if (b != null && d != null) return year >= b && year <= d;
    return Math.abs(r.anchor_ce - year) <= 25;    // tek tarihli: ±25 yıl "çağdaş"
  };
  const nE = packed.dogu.filter(alive).length;
  const nW = packed.bati.filter(alive).length;

  const strip = (rows, side, topY, color) => rows.map((r, i) => {
    const isAlive = alive(r);
    const x0 = x(r._x0), x1 = x(r._x1);
    const yy = topY + r._lane * LH;
    const wd = Math.max(2, x1 - x0);
    return (
      <rect key={`${side}-${i}`} x={x0} y={yy} width={wd} height={LH - 2} rx={1.5}
        fill={color} opacity={isAlive ? 0.95 : 0.22}
        style={{ cursor: 'pointer' }}
        onMouseEnter={(ev) => setHover({ r, x: ev.clientX, y: ev.clientY, side })}
        onMouseLeave={() => setHover(null)}
        onClick={() => {
          if (side === 'dogu') window.location.hash = `scholars?q=${encodeURIComponent(r.name)}`;
          else if (r.qid) window.open(`https://www.wikidata.org/wiki/${r.qid}`, '_blank', 'noopener');
        }} />
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
        <span style={{ fontSize: 12 }}>
          <span style={{ color: GOLD }}>▲ {tr ? 'Doğu' : 'East'} {nE}</span>
          <span style={{ opacity: .4, margin: '0 6px' }}>·</span>
          <span style={{ color: CYAN }}>▼ {tr ? 'Batı' : 'West'} {nW}</span>
          <span style={{ opacity: .55, marginLeft: 6 }}>{tr ? 'çağdaş' : 'contemporaries'}</span>
        </span>
      </div>

      <svg width="100%" height={H} style={{ display: 'block' }}>
        {/* yüzyıl ızgarası */}
        {Array.from({ length: Math.floor((X1 - X0) / 100) + 1 }, (_, i) => X0 + i * 100).map((yr) => (
          <g key={yr}>
            <line x1={x(yr)} x2={x(yr)} y1={0} y2={H - 18} stroke="rgba(255,255,255,.07)" />
            <text x={x(yr)} y={H - 5} fill="#8a8272" fontSize={10} textAnchor="middle">{yr}</text>
          </g>
        ))}

        {/* şerit etiketleri */}
        <text x={4} y={12} fill={GOLD} fontSize={11} fontWeight="700">▲ {tr ? 'DOĞU' : 'EAST'}</text>
        <text x={4} y={axisY + 30} fill={CYAN} fontSize={11} fontWeight="700">▼ {tr ? 'BATI' : 'WEST'}</text>

        {strip(packed.dogu, 'dogu', 18, GOLD)}
        <line x1={ml} x2={w - mr} y1={axisY} y2={axisY} stroke="rgba(201,168,76,.35)" />
        {strip(packed.bati, 'bati', axisY + 36, CYAN)}

        {/* seçili yıl imleci */}
        <line x1={x(year)} x2={x(year)} y1={0} y2={H - 18} stroke="#fff" strokeWidth={1.5} opacity={.75} />
      </svg>

      {hover && (
        <div style={{
          position: 'fixed', left: Math.min(hover.x + 12, window.innerWidth - 260), top: hover.y + 12,
          background: 'rgba(12,14,20,.97)', border: `1px solid ${hover.side === 'dogu' ? GOLD : CYAN}`,
          borderRadius: 8, padding: '7px 10px', fontSize: 12, zIndex: 3000, maxWidth: 250, pointerEvents: 'none',
        }}>
          <div style={{ fontWeight: 700, color: hover.side === 'dogu' ? GOLD : CYAN }}>{hover.r.name}</div>
          <div style={{ opacity: .8 }}>
            {hover.r.birth_ce != null ? hover.r.birth_ce : '?'} – {hover.r.death_ce != null ? hover.r.death_ce : '?'}
            {hover.r.place ? ` · ${hover.r.place}` : ''}
          </div>
          <div style={{ opacity: .55, fontSize: 11, marginTop: 3 }}>
            {hover.side === 'dogu'
              ? (tr ? 'Merkezî defterde kayıtlı — tıkla: havuzda ara' : 'In canonical store — click to search pool')
              : (tr ? 'Yan-tablo (mint edilmedi) — tıkla: Wikidata' : 'Side table (not minted) — click: Wikidata')}
          </div>
        </div>
      )}

      {/* Dürüstlük + telif kapısı notu — EKRANDA */}
      <div style={{ fontSize: 11, opacity: .6, marginTop: 8, lineHeight: 1.6 }}>
        {tr
          ? `⚠ Sayaçlar ANTOLOJİNİN SEÇİM DAĞILIMIDIR — tarihsel üretkenlik ölçüsü DEĞİL. Bir yılda "Batı 41 / Doğu 5" görmek, o çağda Batı'nın daha üretken olduğunu değil, Alatlı'nın o dönem için daha çok Batılı metin seçtiğini gösterir. · Kaynak: ${data.source}. Doğu ${data.counts.dogu} kişi merkezî defterden (pid'li); Batı ${data.counts.bati} kişi yan-tablodan — mağazaya MINT EDİLMEDİ (kapsam+telif kararı), pid taşımaz. Tarihsiz kayıtlar çizilmez. Alatlı-türevli kayıtlar araştırma sürümündedir; kamuya açık dağıtıma izin/karar gelene kadar girmez.`
          : `⚠ Counters reflect the ANTHOLOGY'S SELECTION, not historical productivity. Source: ${data.source}. East ${data.counts.dogu} from the canonical store; West ${data.counts.bati} from a side table — not minted (scope+rights). Undated records are not drawn. Alatlı-derived records stay in the research build.`}
      </div>
    </div>
  );
}
