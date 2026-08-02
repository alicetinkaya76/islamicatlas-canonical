import { useMemo, useState, useRef, useEffect } from 'react';
import useAsyncData from '../../hooks/useAsyncData.jsx';
import { hn } from '../../data/i18n-utils';
import T from '../../data/i18n';

/* ═══ Geo type icons ═══ */
const GEO_ICONS = {
  city: '🏙', village: '🏘', mountain: '⛰', river: '🏞', fortress: '🏰',
  region: '📍', town: '🏛', district: '📌', valley: '🌿', water: '💧',
  well: '🕳', monastery: '⛪', spring: '💦', pass: '🛤', island: '🏝',
  desert: '🏜', place: '📍', market: '🏪', quarter: '🏠', wadi: '🌊', sea: '🌊',
};

const PERIOD_BADGE = {
  active:    { tr: 'Aktif', en: 'Active', color: '#66bb6a' },
  ruined:    { tr: 'Harap', en: 'Ruined', color: '#ff8a65' },
  legendary: { tr: 'Efsanevî', en: 'Legendary', color: '#ce93d8' },
};

export default function YaqutIdCard({ lang, ty, entry, detail, onClose, onLoadDetail }) {
  const t = T[lang];
  const [showFullText, setShowFullText] = useState(false);
  const [xrefPage, setXrefPage] = useState(0);
  const [eventsExpanded, setEventsExpanded] = useState(false);
  const [personsExpanded, setPersonsExpanded] = useState(false);
  const [xrefExpanded, setXrefExpanded] = useState(true);
  /* H54: canonical yer alanlarının HİÇBİRİ arayüze çıkmıyordu (grep: subtype 0,
     located_in 0, temporal_coverage 0, authority_xref 0) ve deponun en zengin
     yer katmanı `note` içinde string olarak hapisti (ülke 11.237, ince tip
     6.999, etimoloji 6.000). Yan dosya ikisini de yayına taşır.
     KAYNAK AYRIMI KORUNUR: `alan` = doğrulanmış canonical alan, `note` =
     metinden ayıklandı. Ayıklanmış bilgi, doğrulanmış alan gibi gösterilmez. */
  const [facets, setFacets] = useState(null);
  useEffect(() => {
    fetch('/view-data/place_facets.json')
      .then((r) => (r.ok ? r.json() : null))
      .then((d) => setFacets(d?.facets || {}))
      .catch(() => setFacets({}));
  }, []);
  const fac = facets && entry?.pid
    ? facets[String(entry.pid).replace(/^iac:place-0*/, '')] : null;
  const XREF_PER_PAGE = 15;

  // Lazy-load crossref data only when this component mounts
  const { data: YAQUT_CROSSREF } = useAsyncData('/data/yaqut_crossref.json');

  // Reset states when entry changes
  const prevIdRef = useRef(null);
  const entryId = entry ? entry.id : null;
  if (entryId !== prevIdRef.current) {
    prevIdRef.current = entryId;
    if (xrefPage !== 0) setXrefPage(0);
    if (showFullText) setShowFullText(false);
  }

  // Cross-ref persons — MUST be before any conditional return (React hooks rule)
  const crossRefPersons = useMemo(() => {
    if (!entryId || !YAQUT_CROSSREF) return [];
    return YAQUT_CROSSREF[String(entryId)] || [];
  }, [entryId, YAQUT_CROSSREF]);

  if (!entry) {
    return (
      <div className="yaqut-idcard-empty">
        <div className="yaqut-idcard-placeholder">
          <span className="yaqut-idcard-icon">🌍</span>
          <p>{ty.noSelection || 'Detay için bir yere tıklayın'}</p>
        </div>
      </div>
    );
  }
  const heading1 = hn(entry, lang);
  const heading2 = lang === "tr" ? entry.he : entry.ht;
  const summary = detail
    ? (lang === "tr" ? (detail.sft || entry.st) : (detail.sfe || entry.se))
    : (lang === "tr" ? entry.st : entry.se);
  const geoType = (lang === "tr" ? entry.gtt : entry.gte);
  const periodBadge = PERIOD_BADGE[entry.hp] || null;

  const xrefTotal = crossRefPersons.length;
  const xrefPages = Math.ceil(xrefTotal / XREF_PER_PAGE);
  const xrefSlice = crossRefPersons.slice(xrefPage * XREF_PER_PAGE, (xrefPage + 1) * XREF_PER_PAGE);

  return (
    <div className="yaqut-idcard">
      {/* Close button */}
      <button className="yaqut-idcard-close" onClick={onClose} aria-label="Close">✕</button>

      {/* Header */}
      <div className="yaqut-idcard-header">
        <h3 className="yaqut-idcard-h1">{heading1}</h3>
        <p className="yaqut-idcard-h2">{heading2}</p>
        <p className="yaqut-idcard-arabic" dir="rtl">{entry.h}</p>
      </div>

      {/* H54: merkezî defterden gelen ve v1 kartında BULUNMAYAN olgular.

          ÖLÇÜLDÜ — tekrar etmemek için: yaqut_lite zaten ülke (10.997), bölge
          (8.519) ve tip (12.935) taşıyor, üstelik tipi canonical'dan DAHA İNCE
          ("city" ↔ canonical "settlement"). Bu üçünü rozet olarak basmak kartı
          tekrarla şişirirdi. Yan dosyada duruyorlar (canonical'ın v1'den fakir
          olduğunun ölçüsü olarak değerliler) ama ekrana çıkmıyorlar.

          Ekrana yalnız v1'de KARŞILIĞI OLMAYAN olgular çıkar: etimoloji
          (5.988), tarihsel dönem (755), otorite bağlantısı (2.774), üst konum
          (1.429). Kaynağı 'note' olanlar KESİK çerçeveyle — metinden
          ayıklandıkları görülsün, doğrulanmış alan gibi durmasınlar. */}
      {fac && (fac.etimoloji || fac.donem || fac.xref || fac.ust) && (
        <div style={{ display: 'flex', flexWrap: 'wrap', gap: 6, margin: '8px 0 4px' }}>
          {fac.donem && (
            <span title={lang === 'tr' ? 'Kaynak metninden ayıklandı (doğrulanmış alan değil)'
                                       : 'Extracted from source note'}
              style={{ fontSize: 11, padding: '2px 8px', borderRadius: 999,
                border: '1px dashed rgba(201,168,76,.55)', color: '#c9a84c', opacity: .85 }}>
              {lang === 'tr' ? 'dönem' : 'period'}: {String(fac.donem.v)}
            </span>
          )}
          {fac.ust && (
            <span title={lang === 'tr' ? 'Merkezî defterde doğrulanmış üst konum' : 'Validated parent place'}
              style={{ fontSize: 11, padding: '2px 8px', borderRadius: 999,
                border: '1px solid rgba(201,168,76,.75)', color: '#c9a84c' }}>
              ⬆ {lang === 'tr' ? 'üst konum' : 'within'}
            </span>
          )}
          {fac.xref && (
            <span title={lang === 'tr' ? 'Merkezî defterde doğrulanmış otorite bağlantısı'
                                       : 'Validated authority cross-reference'}
              style={{ fontSize: 11, padding: '2px 8px', borderRadius: 999,
                border: '1px solid rgba(201,168,76,.75)', color: '#c9a84c' }}>
              🔗 {Array.isArray(fac.xref.v) ? fac.xref.v.length : 1} {lang === 'tr' ? 'otorite' : 'authority'}
            </span>
          )}
          {fac.etimoloji && (
            <span style={{ fontSize: 11, opacity: .72, width: '100%', marginTop: 2 }}
              title={lang === 'tr' ? 'Kaynak metninden ayıklandı' : 'Extracted from note'}>
              🏷 {String(fac.etimoloji.v)}
            </span>
          )}
        </div>
      )}

      {/* Type & Period badges */}
      <div className="yaqut-idcard-badges">
        {geoType && (
          <span className="yaqut-badge yaqut-badge-geo">
            {GEO_ICONS[entry.gt] || '📍'} {geoType}
          </span>
        )}
        {periodBadge && (
          <span className="yaqut-badge" style={{ borderColor: periodBadge.color, color: periodBadge.color }}>
            {periodBadge[lang]}
          </span>
        )}
        {entry.ds && (
          <a href={`https://islamansiklopedisi.org.tr/${entry.ds}`}
            target="_blank" rel="noopener noreferrer"
            className="yaqut-badge yaqut-badge-dia">
            📖 DİA ↗
          </a>
        )}
      </div>

      {/* Fields */}
      <div className="yaqut-idcard-fields">
        {entry.ct && (
          <div className="yaqut-idcard-row">
            <span className="yaqut-idcard-label">{ty.country || 'Ülke'}</span>
            <span className="yaqut-idcard-value">{entry.ct}{entry.rg ? ` — ${entry.rg}` : ''}</span>
          </div>
        )}
        {entry.lat != null && (
          <div className="yaqut-idcard-row">
            <span className="yaqut-idcard-label">{ty.coordinates || 'Koordinat'}</span>
            <span className="yaqut-idcard-value">{entry.lat}°, {entry.lon}°</span>
          </div>
        )}
        {detail && detail.hr && (
          <div className="yaqut-idcard-row">
            <span className="yaqut-idcard-label">{ty.hareke || 'Hareke'}</span>
            <span className="yaqut-idcard-value yaqut-arabic-text" dir="rtl">{detail.hr}</span>
          </div>
        )}
        {detail && detail.et && (
          <div className="yaqut-idcard-row">
            <span className="yaqut-idcard-label">{ty.etymology || 'Etimoloji'}</span>
            <span className="yaqut-idcard-value">{detail.et}</span>
          </div>
        )}
        {detail && detail.pl && (
          <div className="yaqut-idcard-row">
            <span className="yaqut-idcard-label">{ty.parentLocations || 'Üst Bölge'}</span>
            <span className="yaqut-idcard-value" dir="rtl">{detail.pl.join(' / ')}</span>
          </div>
        )}
      </div>

      {/* Summary */}
      {summary && (
        <div className="yaqut-idcard-desc">
          <p>{summary}</p>
          {detail?.ft && !showFullText && (
            <button
              className="yaqut-desc-truncated yaqut-desc-expand-btn"
              onClick={() => {
                setShowFullText(true);
                setTimeout(() => {
                  const el = document.querySelector('.yaqut-fulltext');
                  if (el) el.scrollIntoView({ behavior: 'smooth', block: 'center' });
                }, 300);
              }}
              title={lang === 'tr' ? 'Tam metni göster' : 'Show full text'}
            >
              {lang === 'tr' ? '📜 tam metni göster →' : '📜 show full text →'}
            </button>
          )}
        </div>
      )}

      {/* Atlas Tags */}
      {entry.tg && entry.tg.length > 0 && (
        <div className="yaqut-idcard-tags">
          {entry.tg.map((tag, i) => (
            <span key={i} className="yaqut-tag-badge">{tag}</span>
          ))}
          {detail && detail.tg && detail.tg.filter(t => !entry.tg.includes(t)).map((tag, i) => (
            <span key={`d-${i}`} className="yaqut-tag-badge">{tag}</span>
          ))}
        </div>
      )}

      {/* Alternate names */}
      {entry.an && entry.an.length > 0 && (
        <div className="yaqut-idcard-section">
          <h4 className="yaqut-idcard-section-title">📛 {ty.alternateNames || 'Diğer Adlar'}</h4>
          <div className="yaqut-alt-names" dir="rtl">
            {entry.an.join(' / ')}
            {detail && detail.an && detail.an.filter(a => !entry.an.includes(a)).length > 0 && (
              <span> / {detail.an.filter(a => !entry.an.includes(a)).join(' / ')}</span>
            )}
          </div>
        </div>
      )}

      {/* Historical Events — collapsible */}
      {detail && detail.ev && detail.ev.length > 0 && (
        <div className="yaqut-idcard-section">
          <button className="yaqut-section-toggle" onClick={() => setEventsExpanded(p => !p)}
            aria-expanded={eventsExpanded}>
            📅 {ty.events || 'Tarihî Olaylar'} ({detail.ev.length})
            <span className="yaqut-toggle-arrow">{eventsExpanded ? '▾' : '▸'}</span>
          </button>
          <div className={`yaqut-collapsible${eventsExpanded ? ' expanded' : ' collapsed'}`}>
            <div className="yaqut-events-list">
              {detail.ev.map((ev, i) => (
                <div key={i} className="yaqut-event-item">
                  {ev.y && <span className="yaqut-event-year">{ev.y} H</span>}
                  <span className="yaqut-event-desc">{ev.d}</span>
                </div>
              ))}
            </div>
          </div>
        </div>
      )}

      {/* Notable Persons (from Yaqut) — collapsible */}
      {detail && detail.np && detail.np.length > 0 && (
        <div className="yaqut-idcard-section">
          <button className="yaqut-section-toggle" onClick={() => setPersonsExpanded(p => !p)}
            aria-expanded={personsExpanded}>
            👤 {ty.notablePersons || 'Önemli Kişiler (Yâkût)'} ({detail.np.length})
            <span className="yaqut-toggle-arrow">{personsExpanded ? '▾' : '▸'}</span>
          </button>
          <div className={`yaqut-collapsible${personsExpanded ? ' expanded' : ' collapsed'}`}>
            <div className="yaqut-persons-list">
              {detail.np.map((p, i) => (
                <div key={i} className="yaqut-person-item">
                  <span className="yaqut-person-name" dir="rtl">{p.na}</span>
                  {p.nt && <span className="yaqut-person-tr">{p.nt}</span>}
                  <div className="yaqut-person-meta">
                    {p.r && <span className="yaqut-person-role">{p.r}</span>}
                    {p.d && <span className="yaqut-person-death">ö. {p.d} H</span>}
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>
      )}

      {/* Cross-ref persons (from al-A'lam / Zirikli) — collapsible */}
      {xrefTotal > 0 && (
        <div className="yaqut-idcard-section yaqut-xref-section">
          <button className="yaqut-section-toggle" onClick={() => setXrefExpanded(p => !p)}
            aria-expanded={xrefExpanded}>
            📖 {ty.crossRefPersons} ({xrefTotal})
            <span className="yaqut-toggle-arrow">{xrefExpanded ? '▾' : '▸'}</span>
          </button>
          <div className={`yaqut-collapsible${xrefExpanded ? ' expanded' : ' collapsed'}`}>
          <div className="yaqut-xref-list">
            {xrefSlice.map((p, i) => (
              <div key={i} className="yaqut-xref-item">
                <div className="yaqut-xref-name">
                  {hn(p, lang)}
                  <a href={`#alam?id=${p.id}`} className="yaqut-xref-alam-link"
                    title={t.alam.viewInAlam}>
                    📖
                  </a>
                </div>
                <div className="yaqut-xref-meta">
                  <span className="yaqut-xref-prof">{lang === "tr" ? p.pt : p.pe}</span>
                  {p.dh && <span className="yaqut-xref-death">ö. {p.dh} H / {p.dm}</span>}
                </div>
              </div>
            ))}
          </div>
          {xrefPages > 1 && (
            <div className="yaqut-xref-pager">
              <button disabled={xrefPage === 0} onClick={() => setXrefPage(p => p - 1)}>←</button>
              <span>{xrefPage + 1} / {xrefPages}</span>
              <button disabled={xrefPage >= xrefPages - 1} onClick={() => setXrefPage(p => p + 1)}>→</button>
            </div>
          )}
          </div>
        </div>
      )}

      {/* Poetry & Quran */}
      {(entry.py > 0 || (detail && detail.qr)) && (
        <div className="yaqut-idcard-section">
          <div className="yaqut-poetry-row">
            {entry.py > 0 && <span className="yaqut-poetry-badge">📜 {entry.py} {t.yaqut.idPoems}</span>}
            {detail && detail.qr && <span className="yaqut-quran-badge">📖 {t.yaqut.idQuranRef}</span>}
          </div>
        </div>
      )}

      {/* Ptolemaic coordinates */}
      {detail && detail.ct && (
        <div className="yaqut-idcard-section">
          <h4 className="yaqut-idcard-section-title">🧭 {ty.ptolemaic || 'Batlamyus Koord.'}</h4>
          <div className="yaqut-ptolemaic">
            {detail.ct.longitude_text && <span>Tûl: {detail.ct.longitude_text} ({detail.ct.longitude_approx}°)</span>}
            {detail.ct.latitude_text && <span>Arz: {detail.ct.latitude_text} ({detail.ct.latitude_approx}°)</span>}
          </div>
        </div>
      )}

      {/* Full text */}
      {detail && detail.ft && (
        <div className="yaqut-idcard-section">
          <button className="yaqut-fulltext-toggle" onClick={() => setShowFullText(p => !p)}>
            📜 {showFullText ? t.yaqut.idHideText : t.yaqut.idOriginalText}
          </button>
          {showFullText && (
            <div className="yaqut-fulltext" dir="rtl">
              {detail.ft}
            </div>
          )}
        </div>
      )}

      {/* Source footer */}
      <div className="yaqut-idcard-source">{ty.source || "Kaynak: Yâkût el-Hamevî, Mu'cemü'l-Büldân"}</div>
    </div>
  );
}
