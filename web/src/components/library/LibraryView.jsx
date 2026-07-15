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

export default function LibraryView({ lang = 'tr', initialBook = null, initialSec = null }) {
  const tr = lang !== 'en';
  const [shelf, setShelf] = useState(null);
  const [err, setErr] = useState(null);
  const [book, setBook] = useState(null);        // manifest
  const [secIdx, setSecIdx] = useState(0);
  const [section, setSection] = useState(null);
  const [tocQuery, setTocQuery] = useState('');
  const secCache = useRef({});
  const readerRef = useRef(null);

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
      .then((r) => r.json())
      .then((m) => {
        secCache.current = {};
        setBook({ ...m, pidnum });
        setSecIdx(sec);
        setTocQuery('');
        window.location.hash = `library?book=${pidnum}&sec=${sec}`;
      });
  }, []);

  useEffect(() => {
    if (initialBook) openBook(initialBook, parseInt(initialSec || '0', 10) || 0);
  }, [initialBook, initialSec, openBook]);

  useEffect(() => {
    if (!book) return;
    const key = `${book.pidnum}:${secIdx}`;
    if (secCache.current[key]) { setSection(secCache.current[key]); return; }
    setSection(null);
    fetch(`/reading/${book.pidnum}/sec_${String(secIdx).padStart(4, '0')}.json`)
      .then((r) => r.json())
      .then((s) => { secCache.current[key] = s; setSection(s); readerRef.current?.scrollTo(0, 0); });
  }, [book, secIdx]);

  const gotoSec = useCallback((i) => {
    setSecIdx(i);
    if (book) window.location.hash = `library?book=${book.pidnum}&sec=${i}`;
  }, [book]);

  const filteredToc = useMemo(() => {
    if (!book) return [];
    const q = norm(tocQuery);
    return q ? book.sections.filter((s) => norm(s.title).includes(q)) : book.sections;
  }, [book, tocQuery]);

  /* ═══ stil kısayolları (v1 koyu-altın dili) ═══ */
  const card = { background: 'rgba(255,255,255,.04)', border: '1px solid rgba(201,168,76,.25)', borderRadius: 10 };
  const chip = { display: 'inline-block', padding: '2px 10px', borderRadius: 999, fontSize: 11, background: 'rgba(201,168,76,.15)', color: GOLD, marginRight: 6, marginBottom: 4 };

  if (err) return <div style={{ padding: 40, textAlign: 'center', opacity: .8 }}>{err}</div>;
  if (!shelf) return <div style={{ padding: 40, textAlign: 'center', opacity: .6 }}>{tr ? 'Kütüphane yükleniyor…' : 'Loading library…'}</div>;

  /* ═══════════ RAF GÖRÜNÜMÜ ═══════════ */
  if (!book) {
    return (
      <div style={{ maxWidth: 1200, margin: '0 auto', padding: '24px 16px 60px' }}>
        <h1 style={{ color: GOLD, fontSize: 26, margin: '4px 0 2px' }}>
          📚 {tr ? 'Kütüphane' : 'Library'}
        </h1>
        <p style={{ opacity: .75, margin: '0 0 20px', fontSize: 14 }}>
          {tr
            ? `Çekirdek Külliyat — parti ${shelf.batch}: ${shelf.theme}`
            : `Core canon — batch ${shelf.batch}: ${shelf.theme}`}
        </p>
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

      {/* ORTA: okuyucu */}
      <section ref={readerRef} style={{ overflowY: 'auto', padding: '18px 34px 60px' }}>
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
        {!section && <div style={{ opacity: .6, textAlign: 'center', padding: 40 }}>{tr ? 'Bölüm yükleniyor…' : 'Loading…'}</div>}
        {section && section.paras.map((p, i) => (
          <p key={i} dir="rtl" style={{ fontFamily: "'Amiri','Scheherazade New',serif", fontSize: 19, lineHeight: 2.05, margin: '0 0 14px', textAlign: 'justify' }}>
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
          <div style={{ display: 'flex', justifyContent: 'space-between', padding: '3px 0' }}>
            <span style={{ opacity: .65 }}>{tr ? 'Kalıcı kimlik' : 'PID'}</span><b style={{ fontSize: 10 }}>{book.pid}</b>
          </div>
        </div>
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
