/**
 * CausalReview.jsx — H37: nedensellik bağlarının TARİHÇİ İNCELEME aracı.
 *
 * H36'da 170 kaynak-tanıklı nedensel bağ üretildi, ama hepsi
 * `needs_human_review: true` — yani tarihçi onayı olmadan hiçbir yere
 * bağlanamaz. Bu ekran o onayı mümkün kılar; katmanı "ölü veri" olmaktan
 * çıkaran tek adım.
 *
 * NE YAPAR
 *   - Her bağı Arapça asıl pasajı + bağlacı + sebep/sonuç okumasıyla gösterir.
 *   - Kalite alanlarını (link_type, güven, kanıt-tam, sebep-önerme mi,
 *     sonuç gerçekleşti mi, kim iddia ediyor) rozet olarak açar.
 *   - ✓ onayla / ✗ reddet / ⏭ atla — kararlar localStorage'da tutulur.
 *   - "Kararları indir" → JSON; repoya alınıp `causal_links.json`a işlenir.
 *
 * NE YAPMAZ
 *   - Veriyi DEĞİŞTİRMEZ. Karar dosyası ayrı üretilir; onay olmadan hiçbir bağ
 *     atlas/analiz görünümüne girmez.
 *
 * Veri: /view-data/causal_review.json (data/sources/causal/causal_links.json'dan).
 */
import { useEffect, useMemo, useState } from 'react';

const GOLD = '#c9a84c';
const OK = '#4ade80';
const NO = '#f87171';
const LS_KEY = 'iac_causal_review_v1';

const LINK_LABEL = {
  explicit_talil: { tr: 'Açık ta\'lîl', en: 'Explicit ta\'līl' },
  motive_reported: { tr: 'Aktör gerekçesi', en: 'Reported motive' },
  fa_consequential: { tr: 'Sonuç fâ\'sı', en: 'Consequential fā\'' },
  onomastic: { tr: 'Ad verme', en: 'Onomastic' },
  state_description: { tr: 'Durum betimi', en: 'State description' },
};

export default function CausalReview({ lang = 'tr' }) {
  const tr = lang !== 'en';
  const [data, setData] = useState(null);
  const [err, setErr] = useState(false);
  const [decisions, setDecisions] = useState({});
  const [i, setI] = useState(0);
  const [filter, setFilter] = useState('undecided');   // undecided | all | high | flagged

  useEffect(() => {
    fetch('/view-data/causal_review.json')
      .then((r) => (r.ok ? r.json() : Promise.reject(new Error(String(r.status)))))
      .then(setData).catch(() => setErr(true));
    try {
      const s = localStorage.getItem(LS_KEY);
      if (s) setDecisions(JSON.parse(s));
    } catch { /* bozuk kayıt yoksayılır */ }
  }, []);

  const save = (next) => {
    setDecisions(next);
    try { localStorage.setItem(LS_KEY, JSON.stringify(next)); } catch { /* kota */ }
  };

  const key = (r) => `${r.book_pid}:${r.seq}`;

  const list = useMemo(() => {
    if (!data) return [];
    return data.records.filter((r) => {
      if (filter === 'all') return true;
      if (filter === 'undecided') return !decisions[key(r)];
      if (filter === 'high') return r.confidence === 'high';
      // flagged: denetimin işaret ettiği riskli kayıtlar
      return r.evidence_complete === false || r.cause_is_proposition === false
        || r.effect_realized !== 'realized';
    });
  }, [data, filter, decisions]);

  useEffect(() => { setI(0); }, [filter]);

  if (err) return <div style={{ padding: 30, opacity: .7 }}>{tr ? 'İnceleme verisi yok — H36 hattını koşun.' : 'Review data missing.'}</div>;
  if (!data) return <div style={{ padding: 30, opacity: .6 }}>{tr ? 'Yükleniyor…' : 'Loading…'}</div>;

  const r = list[i];
  const decided = Object.keys(decisions).length;
  const approved = Object.values(decisions).filter((d) => d.verdict === 'approve').length;
  const rejected = Object.values(decisions).filter((d) => d.verdict === 'reject').length;

  const decide = (verdict) => {
    if (!r) return;
    save({ ...decisions, [key(r)]: { verdict, at: new Date().toISOString() } });
    setI((n) => Math.min(n + 1, Math.max(list.length - 1, 0)));
  };

  const download = () => {
    const payload = {
      _doc: 'Nedensellik inceleme kararları — tarihçi onayı. causal_links.json bu dosyayla işlenir.',
      source: 'web CausalReview (H37)',
      total_records: data.records.length,
      decided, approved, rejected,
      decisions,
    };
    const blob = new Blob([JSON.stringify(payload, null, 1)], { type: 'application/json' });
    const a = document.createElement('a');
    a.href = URL.createObjectURL(blob);
    a.download = 'causal_review_decisions.json';
    a.click();
    URL.revokeObjectURL(a.href);
  };

  const chip = (label, value, tone) => (
    <span style={{
      display: 'inline-block', padding: '2px 8px', borderRadius: 999, fontSize: 11,
      border: `1px solid ${tone || 'rgba(255,255,255,.18)'}`,
      color: tone || '#a89b8c', marginRight: 6, marginBottom: 4,
    }}>{label}{value != null ? `: ${value}` : ''}</span>
  );

  return (
    <div style={{ maxWidth: 980, margin: '0 auto', padding: '18px 16px 60px' }}>
      <h1 style={{ color: GOLD, fontSize: 22, margin: '0 0 4px' }}>
        ⚖️ {tr ? 'Nedensellik Onayı' : 'Causal Review'}
      </h1>
      <p style={{ opacity: .72, fontSize: 12.5, margin: '0 0 12px', lineHeight: 1.65 }}>
        {tr
          ? `${data.records.length} bağ — hepsi kaynağın Arapça asılda kendi kurduğu sebep–sonuç; hiçbiri yorum değil. Onaylanmayan bağ atlas/analiz görünümüne GİRMEZ. Kararlar tarayıcıda saklanır; "Kararları indir" ile repoya alınır.`
          : `${data.records.length} links extracted from the Arabic source itself. Unapproved links never reach the atlas.`}
      </p>

      {/* Sayaç + filtre + indir */}
      <div style={{ display: 'flex', gap: 10, flexWrap: 'wrap', alignItems: 'center', marginBottom: 12 }}>
        <span style={{ fontSize: 12 }}>
          <b style={{ color: OK }}>{approved}</b> {tr ? 'onay' : 'approved'} ·{' '}
          <b style={{ color: NO }}>{rejected}</b> {tr ? 'red' : 'rejected'} ·{' '}
          <b>{data.records.length - decided}</b> {tr ? 'kaldı' : 'left'}
        </span>
        {[
          ['undecided', tr ? 'Karar bekleyen' : 'Undecided'],
          ['high', tr ? 'Yüksek güven' : 'High confidence'],
          ['flagged', tr ? 'İşaretli (riskli)' : 'Flagged'],
          ['all', tr ? 'Tümü' : 'All'],
        ].map(([k, lbl]) => (
          <button key={k} onClick={() => setFilter(k)}
            style={{
              padding: '3px 10px', borderRadius: 7, fontSize: 11.5, cursor: 'pointer',
              border: `1px solid ${filter === k ? GOLD : 'rgba(255,255,255,.18)'}`,
              background: filter === k ? 'rgba(201,168,76,.16)' : 'transparent',
              color: filter === k ? GOLD : '#a89b8c',
            }}>{lbl}</button>
        ))}
        <button onClick={download}
          style={{ marginLeft: 'auto', padding: '3px 10px', borderRadius: 7, fontSize: 11.5,
            border: `1px solid ${GOLD}`, background: 'rgba(201,168,76,.12)', color: GOLD, cursor: 'pointer' }}>
          ⬇ {tr ? 'Kararları indir' : 'Download decisions'}
        </button>
      </div>

      {!r ? (
        <div style={{ padding: 40, textAlign: 'center', opacity: .7 }}>
          {tr ? 'Bu süzgeçte inceleyecek bağ kalmadı.' : 'Nothing left in this filter.'}
        </div>
      ) : (
        <div style={{ border: '1px solid rgba(201,168,76,.28)', borderRadius: 12, padding: '14px 16px' }}>
          <div style={{ fontSize: 11.5, opacity: .6, marginBottom: 8 }}>
            {i + 1} / {list.length} · {r.book} · §{r.sec}{r.page ? ` · ${r.page}` : ''}
            {r.date_text ? ` · ${r.date_text}` : ''}
          </div>

          {/* Arapça asıl — kanıt */}
          <div dir="rtl" style={{
            fontFamily: "'Amiri','Scheherazade New',serif", fontSize: 19, lineHeight: 2,
            background: 'rgba(0,0,0,.22)', borderRadius: 8, padding: '10px 14px', marginBottom: 10,
          }}>{r.quote_ar}</div>

          <div style={{ fontSize: 12.5, marginBottom: 6 }}>
            <span style={{ opacity: .6 }}>{tr ? 'Bağlaç' : 'Connector'}: </span>
            <span dir="rtl" style={{ fontFamily: "'Amiri',serif", color: GOLD, fontSize: 16 }}>{r.connector_ar}</span>
          </div>
          <div style={{ fontSize: 13.5, lineHeight: 1.7, marginBottom: 8 }}>
            <div><b style={{ color: GOLD }}>{tr ? 'Sebep' : 'Cause'}:</b> {r.cause_tr}</div>
            <div><b style={{ color: GOLD }}>{tr ? 'Sonuç' : 'Effect'}:</b> {r.effect_tr}</div>
          </div>

          {/* Kalite rozetleri — denetimin ürettiği alanlar */}
          <div style={{ marginBottom: 10 }}>
            {chip(LINK_LABEL[r.link_type]?.[tr ? 'tr' : 'en'] || r.link_type, null, GOLD)}
            {chip(tr ? 'güven' : 'conf', r.confidence,
              r.confidence === 'high' ? OK : r.confidence === 'low' ? NO : undefined)}
            {r.evidence_complete === false && chip(tr ? 'kanıt eksik (sebep/sonuç alıntı dışında)' : 'evidence incomplete', null, NO)}
            {r.cause_is_proposition === false && chip(tr ? 'sebep çıplak ad (önerme değil)' : 'cause not a proposition', null, NO)}
            {r.effect_realized && r.effect_realized !== 'realized' && chip(tr ? 'sonuç' : 'effect', r.effect_realized, NO)}
            {r.asserted_by && chip(tr ? 'iddia' : 'asserted', r.asserted_by)}
          </div>

          <div style={{ display: 'flex', gap: 8 }}>
            <button onClick={() => decide('approve')}
              style={{ flex: 1, padding: '8px 0', borderRadius: 8, cursor: 'pointer',
                border: `1px solid ${OK}`, background: 'rgba(74,222,128,.12)', color: OK, fontWeight: 700 }}>
              ✓ {tr ? 'Onayla' : 'Approve'}
            </button>
            <button onClick={() => decide('reject')}
              style={{ flex: 1, padding: '8px 0', borderRadius: 8, cursor: 'pointer',
                border: `1px solid ${NO}`, background: 'rgba(248,113,113,.12)', color: NO, fontWeight: 700 }}>
              ✗ {tr ? 'Reddet' : 'Reject'}
            </button>
            <button onClick={() => setI((n) => Math.min(n + 1, list.length - 1))}
              style={{ padding: '8px 14px', borderRadius: 8, cursor: 'pointer',
                border: '1px solid rgba(255,255,255,.18)', background: 'none', color: '#a89b8c' }}>
              ⏭ {tr ? 'Atla' : 'Skip'}
            </button>
          </div>
        </div>
      )}

      <div style={{ fontSize: 11, opacity: .55, marginTop: 12, lineHeight: 1.65 }}>
        {tr
          ? `Kaynak: 7 kronik (11.253 olay) → Arapça asılda kelime-sınırlı nedensel işaret (195 güçlü aday) → yapılandırılmış çıkarım (iki bağımsız denetim turunun kurallarıyla). Alıntılar kaynakla bayt-bayt aynıdır. Bu ekran veriyi DEĞİŞTİRMEZ; kararlar ayrı dosyaya yazılır.`
          : 'Quotes are byte-identical to the source. This screen never modifies the data.'}
      </div>
    </div>
  );
}
