import { useState, useEffect, useMemo, useCallback } from 'react';
import { VirtualList, normalize } from '../shared/bookkit';
import { ensurePersonBridge, bridgeByPid } from '../../data/personBridge';

/**
 * UlemaPool — Ulema Havuzu (H20 S3, Dalga-3).
 *
 * SAHİP KARARI (2026-07-19): Âlimler bölümü statik 450'lik set DEĞİL;
 * mağazadaki TÜM kişi kayıtlarının süzüldüğü DİNAMİK havuz. Her yeni
 * kitap işlendiğinde çıkan âlimler havuza kendiliğinden akar — endeks
 * elle güncellenen bir liste değil, boru hattının yan ürünüdür
 * (pipelines/frontend/build_ulema_pool.py).
 *
 * 450'lik set BURADA YOK OLMAZ: ağ/isnad/zaman çizelgesi görünümleri
 * aynen durur (sevilen v1 UI); havuz onların yanına 4. mod olarak gelir
 * ve 450'lik küme havuzda "tohum" rozetiyle işaretlidir.
 *
 * bookkit'in VirtualList'i burada İKİNCİ tüketicisini buldu (terfi
 * kuralının ilk meyvesi — H17 KARAR-2).
 */

/* Kaynak kısa kodları → rozet + derin link üreteci.
   Kodlar üreticinin sözleşmesi (ulema_pool.json): a/d/e/s/sc/b. */
const SRC = {
  a:  { label: "el-A'lâm",  color: '#c9a84c', href: (b) => (b && b.alam != null ? `#alam?id=${b.alam}` : null) },
  d:  { label: 'DİA',       color: '#4db6ac', href: (b) => (b && b.dia ? `#dia/${b.dia}` : null) },
  e:  { label: 'EI-1',      color: '#ff8a65', href: (b) => (b && b.ei1 != null ? `#ei1/${b.ei1}` : null) },
  s:  { label: 'Bilim Atlası', color: '#81c784', href: () => '#science' },
  sc: { label: '450 tohum', color: '#9575cd', href: () => '#scholars' },
  b:  { label: 'Kitap/diğer', color: '#90a4ae', href: () => null },
};
const SRC_ORDER = ['a', 'd', 'e', 's', 'sc', 'b'];

/* Üretici alan adları TR; eski/İng. varyantlara karşı tek okuma noktası. */
const nameTr = (r) => r.ad_tr || '';
const nameAr = (r) => r.ad_ar || '';
const deathH = (r) => (r.oh != null ? r.oh : null);
const deathM = (r) => (r.om != null ? r.om : null);
const srcsOf = (r) => r.k || [];
const roleOf = (r) => (r.m && r.m.length ? r.m[0] : '');

const ITEM_H = 62;

export default function UlemaPool({ lang = 'tr', initialPid, initialSearch }) {
  const tr = lang !== 'en';
  const [pool, setPool] = useState(null);
  const [meta, setMeta] = useState(null);
  const [err, setErr] = useState(false);
  const [q, setQ] = useState(initialSearch || '');
  const [srcFilter, setSrcFilter] = useState(new Set());
  const [selected, setSelected] = useState(null);

  useEffect(() => {
    const base = import.meta.env.BASE_URL || '/';
    ensurePersonBridge();   // kaynak izlerinin derin linkleri için
    fetch(`${base}books/ulema_pool.json`, { cache: 'no-cache' })
      .then((r) => (r.ok ? r.json() : Promise.reject()))
      .then((d) => setPool(Array.isArray(d) ? d : (d.kisiler || [])))
      .catch(() => setErr(true));
    fetch(`${base}books/ulema_pool_meta.json`, { cache: 'no-cache' })
      .then((r) => (r.ok ? r.json() : null)).then(setMeta).catch(() => {});
  }, []);

  const toggleSrc = useCallback((k) => {
    setSrcFilter((prev) => {
      const next = new Set(prev);
      if (next.has(k)) next.delete(k); else next.add(k);
      return next;
    });
  }, []);

  /* H43: dışarıdan gelen pid'i kayda çöz. Havuz kimliği SAYIDIR
     (_pid_format: "iac:person-%08d") — gelen 'iac:person-00005687' → 5687.
     Ölçüldü: senkronik şeritteki 231 pid'in 231'i havuzda karşılık buluyor. */
  useEffect(() => {
    if (!initialPid || !pool) return;
    const m = String(initialPid).match(/(\d+)\s*$/);
    if (!m) return;
    const hit = pool.find((r) => Number(r.id) === Number(m[1]));
    if (!hit) return;
    setSelected(hit);
    /* Listeyi de o kişiye getir: 22.824 kayıtlık sanal listede seçili kayıt
       ekranın çok dışında kalıyordu (ölçüldü: sağ panel doğru kişiyi açarken
       liste Abū Bakr'dan başlıyordu). Arama kutusunu adıyla doldurmak, kaydırma
       hilesine gerek kalmadan kişiyi listenin başına getirir. */
    setQ(nameTr(hit) || '');
  }, [initialPid, pool]);

  const filtered = useMemo(() => {
    if (!pool) return [];
    let arr = pool;
    if (srcFilter.size) arr = arr.filter((r) => srcsOf(r).some((s) => srcFilter.has(s)));
    if (q.trim().length >= 2) {
      const n = normalize(q.trim());
      arr = arr.filter((r) => normalize(nameTr(r)).includes(n) || normalize(nameAr(r)).includes(n));
    }
    return arr;
  }, [pool, q, srcFilter]);

  const GOLD = '#c9a84c';
  const card = { background: 'rgba(255,255,255,.04)', border: '1px solid rgba(201,168,76,.25)', borderRadius: 10 };

  if (err) return (
    <div style={{ padding: 40, textAlign: 'center', opacity: .8 }}>
      {tr ? 'Havuz verisi bulunamadı — `python3 pipelines/frontend/build_ulema_pool.py` koşun.'
          : 'Pool data missing — run build_ulema_pool.py.'}
    </div>
  );
  if (!pool) return <div style={{ padding: 40, textAlign: 'center', opacity: .6 }}>{tr ? 'Havuz yükleniyor…' : 'Loading pool…'}</div>;

  return (
    <div style={{ display: 'grid', gridTemplateColumns: '1fr 320px', gap: 14, height: 'calc(100vh - 210px)', minHeight: 420, padding: '0 14px' }}>
      {/* SOL: arama + filtre + sanal liste */}
      <div style={{ display: 'flex', flexDirection: 'column', overflow: 'hidden' }}>
        <div style={{ display: 'flex', gap: 8, alignItems: 'center', marginBottom: 8, flexWrap: 'wrap' }}>
          <input value={q} onChange={(e) => setQ(e.target.value)}
            placeholder={tr ? 'Âlim ara (TR/AR)…' : 'Search scholars…'}
            style={{ flex: '1 1 220px', padding: '7px 12px', borderRadius: 8, border: '1px solid rgba(201,168,76,.3)', background: 'rgba(0,0,0,.3)', color: 'inherit', fontSize: 13 }} />
          <span style={{ fontSize: 12, opacity: .75, fontVariantNumeric: 'tabular-nums' }}>
            {filtered.length.toLocaleString('tr-TR')} / {pool.length.toLocaleString('tr-TR')}
          </span>
        </div>
        <div style={{ display: 'flex', gap: 6, flexWrap: 'wrap', marginBottom: 8 }}>
          {SRC_ORDER.map((k) => (
            <button key={k} onClick={() => toggleSrc(k)}
              style={{ padding: '2px 10px', borderRadius: 999, fontSize: 11.5, cursor: 'pointer',
                background: srcFilter.has(k) ? SRC[k].color : 'rgba(0,0,0,.25)',
                color: srcFilter.has(k) ? '#0f1419' : SRC[k].color,
                border: `1px solid ${SRC[k].color}`, fontWeight: srcFilter.has(k) ? 700 : 400 }}>
              {SRC[k].label}{meta && meta.kaynak_basina_kisi && meta.kaynak_basina_kisi[k] != null
                ? ` ${Number(meta.kaynak_basina_kisi[k]).toLocaleString('tr-TR')}` : ''}
            </button>
          ))}
        </div>
        <div style={{ ...card, flex: 1, overflow: 'hidden' }}>
          <VirtualList
            items={filtered}
            itemHeight={ITEM_H}
            className="ulema-pool-list"
            getKey={(r) => r.id}
            renderItem={(r) => (
              <button key={r.id} onClick={() => setSelected(r)}
                style={{ display: 'block', width: '100%', height: ITEM_H, textAlign: 'left', padding: '8px 14px',
                  background: (selected && selected.id === r.id) ? 'rgba(201,168,76,.16)' : 'none',
                  border: 'none', borderBottom: '1px solid rgba(255,255,255,.05)', color: 'inherit', cursor: 'pointer' }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', gap: 10, alignItems: 'baseline' }}>
                  <span style={{ fontSize: 13.5, fontWeight: 600, overflow: 'hidden', whiteSpace: 'nowrap', textOverflow: 'ellipsis' }}>{nameTr(r)}</span>
                  {nameAr(r) && <span dir="rtl" style={{ fontFamily: "'Amiri',serif", fontSize: 15, color: GOLD, flexShrink: 0 }}>{nameAr(r)}</span>}
                </div>
                <div style={{ display: 'flex', gap: 6, alignItems: 'center', marginTop: 3 }}>
                  {deathH(r) != null && <span style={{ fontSize: 11, opacity: .7, fontVariantNumeric: 'tabular-nums' }}>ö. {deathH(r)} H{deathM(r) != null ? ` / ${deathM(r)} M` : ''}</span>}
                  {roleOf(r) && <span style={{ fontSize: 11, opacity: .6 }}>· {roleOf(r)}</span>}
                  <span style={{ marginLeft: 'auto', display: 'flex', gap: 3 }}>
                    {srcsOf(r).map((s) => SRC[s] && (
                      <span key={s} title={SRC[s].label}
                        style={{ width: 7, height: 7, borderRadius: '50%', background: SRC[s].color, display: 'inline-block' }} />
                    ))}
                  </span>
                </div>
              </button>
            )}
          />
        </div>
      </div>

      {/* SAĞ: seçili kişinin kaynak izleri */}
      <aside style={{ ...card, padding: '14px 16px', overflowY: 'auto' }}>
        {!selected ? (
          <div style={{ opacity: .6, fontSize: 13, lineHeight: 1.7 }}>
            <b style={{ color: GOLD }}>{tr ? 'Ulema Havuzu' : 'Ulema Pool'}</b><br />
            {tr ? 'Mağazadaki bütün kişi kayıtları tek endekste. Her yeni kitap işlendiğinde çıkan âlimler havuza kendiliğinden akar.'
                : 'Every person record in the store, in one index. New books feed the pool automatically.'}
            {meta && (
              <div style={{ marginTop: 14, fontSize: 12 }}>
                {meta.toplam_kisi != null && <div>👤 {Number(meta.toplam_kisi).toLocaleString('tr-TR')} {tr ? 'kişi' : 'persons'}</div>}
                {meta.olum_tarihi && meta.olum_tarihi.en_az_biri != null &&
                  <div>📅 {Number(meta.olum_tarihi.en_az_biri).toLocaleString('tr-TR')} {tr ? 'tarihli kayıt' : 'dated'}</div>}
              </div>
            )}
          </div>
        ) : (
          <>
            <div style={{ fontSize: 16, fontWeight: 700 }}>{nameTr(selected)}</div>
            {nameAr(selected) && <div dir="rtl" style={{ fontFamily: "'Amiri',serif", fontSize: 20, color: GOLD, margin: '4px 0' }}>{nameAr(selected)}</div>}
            {deathH(selected) != null && (
              <div style={{ fontSize: 12, opacity: .8, marginTop: 4 }}>
                ö. {deathH(selected)} H{deathM(selected) != null ? ` / ${deathM(selected)} M` : ''}
              </div>
            )}
            {roleOf(selected) && <div style={{ fontSize: 12, opacity: .7, marginTop: 2 }}>{roleOf(selected)}</div>}
            <div style={{ fontSize: 10.5, opacity: .45, marginTop: 8, fontFamily: 'monospace' }}>
              iac:person-{String(selected.id).padStart(8, '0')}
            </div>
            <div style={{ marginTop: 14, fontSize: 12, color: GOLD, fontWeight: 700 }}>
              {tr ? 'Kaynak izleri' : 'Source traces'}
            </div>
            <div style={{ display: 'flex', flexDirection: 'column', gap: 6, marginTop: 8 }}>
              {srcsOf(selected).map((s) => {
                const def = SRC[s];
                if (!def) return null;
                const href = def.href(bridgeByPid(selected.id));
                return href ? (
                  <a key={s} href={href}
                    style={{ padding: '6px 10px', borderRadius: 8, border: `1px solid ${def.color}`, color: def.color, textDecoration: 'none', fontSize: 12.5 }}>
                    {def.label} →
                  </a>
                ) : (
                  <span key={s} style={{ padding: '6px 10px', borderRadius: 8, border: '1px solid rgba(255,255,255,.15)', opacity: .7, fontSize: 12.5 }}>
                    {def.label}
                  </span>
                );
              })}
            </div>
          </>
        )}
      </aside>
    </div>
  );
}
