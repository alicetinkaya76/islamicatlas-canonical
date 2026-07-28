/**
 * CanonicalIsnadNetwork.jsx — H34: merkezî defterden hoca–talebe (isnâd) ağı.
 *
 * v1 ağı 450 âlim / 155 kenardı (db.json). Bu mod canonical mağazanın DİA
 * ilişkilerinden gelen **3.393 kişi / 7.869 kenar**lık gerçek isnâd ağını
 * gösterir. v1 ağı DEĞİŞMEZ — bu ayrı bir moddur (H26/H28 "ek katman" deseni).
 *
 * Ölçek gerçeği: 3.393 düğüm kuvvet-yerleşiminde ağırdır. Bu yüzden DERECE
 * EŞİĞİ vardır (varsayılan 8): eşiğin altındaki düğümler çizilmez, kaç tanesi
 * gizlendiği EKRANDA yazar — "az veri var" izlenimi verilmez.
 *
 * Veri: /view-data/scholar_network.json (build_scholar_network.py).
 * Yön: hoca → talebe (H11 S11'de veriyle doğrulandı; v1 sitesi ters gösteriyordu).
 */
import { useEffect, useRef, useState, useMemo } from 'react';
import * as d3 from 'd3';

const GOLD = '#c9a84c';
const CYAN = '#38bdf8';

export default function CanonicalIsnadNetwork({ lang = 'tr' }) {
  const tr = lang !== 'en';
  const [data, setData] = useState(null);
  const [err, setErr] = useState(false);
  const [minDeg, setMinDeg] = useState(8);
  const [sel, setSel] = useState(null);
  const svgRef = useRef(null);
  const wrapRef = useRef(null);
  const [w, setW] = useState(1000);

  useEffect(() => {
    fetch('/view-data/scholar_network.json')
      .then((r) => (r.ok ? r.json() : Promise.reject(new Error(String(r.status)))))
      .then(setData)
      .catch(() => setErr(true));
  }, []);

  useEffect(() => {
    if (!wrapRef.current) return undefined;
    const ro = new ResizeObserver((es) => setW(Math.max(560, es[0].contentRect.width)));
    ro.observe(wrapRef.current);
    return () => ro.disconnect();
  }, [data]);

  /* Eşik süzgeci: düğüm + iki ucu da kalan kenarlar. */
  const view = useMemo(() => {
    if (!data) return { nodes: [], links: [], hidden: 0 };
    const keep = new Set(data.nodes.filter((n) => n.deg >= minDeg).map((n) => n.pid));
    return {
      nodes: data.nodes.filter((n) => keep.has(n.pid)).map((n) => ({ ...n })),
      links: data.edges.filter((e) => keep.has(e.s) && keep.has(e.t))
        .map((e) => ({ source: e.s, target: e.t })),
      hidden: data.nodes.length - keep.size,
    };
  }, [data, minDeg]);

  useEffect(() => {
    if (!data || !svgRef.current) return undefined;
    const H = 560;
    const svg = d3.select(svgRef.current);
    svg.selectAll('*').remove();
    svg.attr('viewBox', `0 0 ${w} ${H}`);
    const g = svg.append('g');

    svg.call(d3.zoom().scaleExtent([0.25, 4]).on('zoom', (ev) => g.attr('transform', ev.transform)));

    const link = g.append('g').attr('stroke', 'rgba(201,168,76,.22)')
      .selectAll('line').data(view.links).join('line').attr('stroke-width', 1);

    const rOf = (d) => Math.min(3 + Math.sqrt(d.deg) * 1.6, 16);
    const node = g.append('g').selectAll('circle').data(view.nodes).join('circle')
      .attr('r', rOf)
      .attr('fill', (d) => (d.death_ce != null && d.death_ce < 1000 ? GOLD : CYAN))
      .attr('fill-opacity', .85)
      .attr('stroke', '#0b1016').attr('stroke-width', 1)
      .style('cursor', 'pointer')
      .on('click', (_e, d) => setSel(d));

    node.append('title').text((d) => `${d.name} · ${d.deg} bağ${d.death_ce != null ? ` · ö. ${d.death_ce}` : ''}`);

    const sim = d3.forceSimulation(view.nodes)
      .force('link', d3.forceLink(view.links).id((d) => d.pid).distance(38).strength(.25))
      .force('charge', d3.forceManyBody().strength(-70))
      .force('center', d3.forceCenter(w / 2, H / 2))
      .force('collide', d3.forceCollide().radius((d) => rOf(d) + 2))
      .on('tick', () => {
        link.attr('x1', (d) => d.source.x).attr('y1', (d) => d.source.y)
          .attr('x2', (d) => d.target.x).attr('y2', (d) => d.target.y);
        node.attr('cx', (d) => d.x).attr('cy', (d) => d.y);
      });

    return () => sim.stop();
  }, [data, view, w]);

  if (err) return <div style={{ padding: 30, opacity: .7 }}>{tr ? 'Ağ verisi bulunamadı — `python3 pipelines/frontend/build_scholar_network.py` koşun.' : 'Network data missing.'}</div>;
  if (!data) return <div style={{ padding: 30, opacity: .6 }}>{tr ? 'İsnâd ağı yükleniyor…' : 'Loading…'}</div>;

  return (
    <div ref={wrapRef} style={{ padding: '6px 10px 16px' }}>
      <div style={{ display: 'flex', alignItems: 'center', gap: 14, flexWrap: 'wrap', marginBottom: 6 }}>
        <span style={{ fontSize: 12, opacity: .8 }}>
          {tr ? 'En az bağ' : 'Min. degree'}: <b style={{ color: GOLD }}>{minDeg}</b>
        </span>
        <input type="range" min={1} max={15} value={minDeg} step={1}
          onChange={(e) => setMinDeg(+e.target.value)}
          style={{ width: 200, accentColor: GOLD }} />
        <span style={{ fontSize: 12 }}>
          <b style={{ color: GOLD }}>{view.nodes.length.toLocaleString('tr-TR')}</b> {tr ? 'âlim' : 'scholars'}
          <span style={{ opacity: .4 }}> · </span>
          <b style={{ color: GOLD }}>{view.links.length.toLocaleString('tr-TR')}</b> {tr ? 'bağ' : 'links'}
          <span style={{ opacity: .55 }}> {tr ? `(eşik altında ${view.hidden.toLocaleString('tr-TR')} âlim gizli)` : `(${view.hidden} below threshold)`}</span>
        </span>
      </div>

      <svg ref={svgRef} width="100%" height={560}
        style={{ display: 'block', border: '1px solid rgba(201,168,76,.2)', borderRadius: 10, background: 'rgba(0,0,0,.16)' }} />

      {sel && (
        <div style={{
          marginTop: 8, padding: '8px 12px', borderRadius: 8,
          border: `1px solid ${GOLD}`, background: 'rgba(201,168,76,.08)', fontSize: 13,
        }}>
          <b style={{ color: GOLD }}>{sel.name}</b>
          <span style={{ opacity: .75 }}>
            {sel.death_ce != null ? ` · ö. ${sel.death_ce}` : ''} · {sel.deg} {tr ? 'bağ' : 'links'}
            {sel.layers?.length ? ` · ${sel.layers.join(', ')}` : ''}
          </span>
          <button onClick={() => { window.location.hash = `scholars?q=${encodeURIComponent(sel.name)}`; }}
            style={{ marginLeft: 10, border: `1px solid ${GOLD}`, background: 'none', color: GOLD, borderRadius: 6, padding: '2px 8px', fontSize: 11.5, cursor: 'pointer' }}>
            {tr ? 'Havuzda ara' : 'Search pool'}
          </button>
          <button onClick={() => setSel(null)}
            style={{ marginLeft: 6, border: 'none', background: 'none', color: '#a89b8c', cursor: 'pointer' }}>✕</button>
        </div>
      )}

      <div style={{ fontSize: 11, opacity: .58, marginTop: 8, lineHeight: 1.6 }}>
        {tr
          ? `Merkezî defterden isnâd ağı: toplam ${data.counts.nodes.toLocaleString('tr-TR')} âlim · ${data.counts.edges.toLocaleString('tr-TR')} hoca–talebe bağı (kaynak: DİA ilişkileri). Kenar yönü hoca → talebe. Mağazada karşılığı olmayan ${data.counts.dropped_ghost_ends} uç atıldı (hayalet bağ çizilmez). Altın = ö. 1000 öncesi, camgöbeği = sonrası. Kaydırıcı yalnız GÖRÜNÜRLÜĞÜ süzer, veriyi değiştirmez.`
          : `Canonical isnād network: ${data.counts.nodes} scholars · ${data.counts.edges} teacher–student links (source: TDV İA relations). ${data.counts.dropped_ghost_ends} ghost ends dropped. The slider filters display only.`}
      </div>
    </div>
  );
}
