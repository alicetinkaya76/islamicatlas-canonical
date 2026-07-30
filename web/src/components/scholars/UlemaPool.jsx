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
   Kodlar üreticinin sözleşmesi (ulema_pool.json): a/d/e/s/sc + bc/by/bo/ba/b.

   H46: 'b' TEK kovaydı ve href SABİT null'dı — 3.105 kişinin tek rozeti
   tıklanamıyordu. Alt-kodlara ayrıldı; her biri kendi açılabilir hedefine
   gider, hedefi olmayan önek DÜRÜSTÇE ayrı görünür ve neden açılmadığını
   söyler. href imzası (bridge, record): hedefler kayıttaki `t` alanından
   gelir ve üretici onları YALNIZ gerçekten çözüldüklerinde yazar.

   Bu tablo build_ulema_pool.py'nin CODE_LABELS'ıyla birlikte değişmek
   zorundadır (meta.kaynak_basina anahtar kümesi çipleri besliyor). */
const SRC = {
  a:  { label: "el-A'lâm",  color: '#c9a84c', href: (b) => (b && b.alam != null ? `#alam?id=${b.alam}` : null) },
  d:  { label: 'DİA',       color: '#4db6ac', href: (b) => (b && b.dia ? `#dia/${b.dia}` : null) },
  e:  { label: 'EI-1',      color: '#ff8a65', href: (b) => (b && b.ei1 != null ? `#ei1/${b.ei1}` : null) },
  s:  { label: 'Bilim Atlası', color: '#81c784', href: () => '#science' },
  sc: { label: '450 tohum', color: '#9575cd', href: () => '#scholars' },
  /* DİA madde-parçası. Hedef yalnız SLUG BU KİŞİYE AİTSE yazılır — ölçüldü:
     300 kayıtta slug BAŞKA bir pid'e bağlıydı ve link yanlış maddeyi açardı. */
  bc: { label: 'DİA (madde parçası)', color: '#4db6ac',
        href: (b, r) => (r?.t?.bc ? `#dia/${r.t.bc}` : null),
        bosNeden: 'Bu kişinin DİA madde-parçası başka bir kayda bağlı; yanlış madde açmamak için bağ verilmedi.' },
  /* Bosworth hükümdar listesi. Hedef HANEDANI haritada açar, kişinin kendi
     kaydını DEĞİL — etiket bunu söylüyor, "kişi sayfası" izlenimi vermiyor. */
  by: { label: 'Bosworth hanedanı', color: '#ba68c8',
        href: (b, r) => (r?.t?.by ? `#dynasty/${r.t.by}` : null) },
  /* OpenITI külliyatı: eser mağazada var ama sitede yalnız 17 kitap okunabilir. */
  bo: { label: 'OpenITI külliyatı', color: '#90a4ae', href: () => null,
        bosNeden: 'Eseri merkezî defterde kayıtlı, ama bu kitap sitede henüz okunabilir değil.' },
  /* Alatlı antolojisi: şeritte çizili ama şerit kişiye derin link kabul etmiyor. */
  ba: { label: 'Alatlı antolojisi', color: '#90a4ae', href: () => null,
        bosNeden: 'Senkronik şeritte çizili; şerit henüz kişiye doğrudan bağ kabul etmiyor.' },
  b:  { label: 'Kitap/diğer', color: '#90a4ae', href: () => null,
        bosNeden: 'Kaynak izi var, açılabilir bir sayfası yok.' },
};
const SRC_ORDER = ['a', 'd', 'e', 's', 'sc', 'bc', 'by', 'bo', 'ba', 'b'];

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
  /* H44 — HAVUZUN ASIL KAZANCI BURADA GÖRÜNÜR.
     Ali sordu: "havuzda artırınca ne elde ediyoruz?" Ölçüldü: havuz 22.824
     kişiye çıkmıştı ama yayınlanan kayıt yalnız 7 alan taşıyordu; mağazadaki
     7.919 hoca, 7.926 talebe, 8.298 yer bağı ve 21.883 biyografik notun
     HİÇBİRİ arayüze çıkmıyordu. Yani büyüme kayıt SAYISINI artırmış, kayıt
     DERİNLİĞİNİ ekrana taşımamıştı.
     Yan dosyalar LITE endeksi bozmadan bunu kapatır; liste aynı hızda kalır.
     Notlar 4 MB olduğu için AYRI dosyada ve ilk seçimde bir kez yüklenir. */
  const [links, setLinks] = useState(null);
  const [notes, setNotes] = useState(null);
  /* H45 ters yön: bu kişi Çekirdek Külliyat'ta bir kitabın müellifi mi?
     core_shelf.json'un 17 kaydının 17'sinde author_pid var. Küçük dosya,
     panel açılışında bir kez. Kitap yoksa rozet HİÇ çıkmaz — 22.824 kişinin
     yalnız 17'sinde (%0,07) görünür; bu bir "özellik" değil, külliyat
     büyüdükçe kendiliğinden büyüyen bir kapıdır. */
  const [shelfByAuthor, setShelfByAuthor] = useState(null);
  /* H47: AYNI KİŞİ OLABİLECEK öbür kayıtlar. Denetimin ölçtüğü asıl kusur:
     "22.824" bir kişi sayısı DEĞİL kayıt sayısıdır; aynı kişi 2-3 pid'e
     dağılmış ve bedeli sayı değil ZENGİNLİK PARÇALANMASI — biyografi bir
     kayıtta, eserleri başka kayıtta. Kullanıcı "bütün Gazzâlî"yi göremiyordu.
     BİRLEŞTİRME YAPILMIYOR (veri-yıkıcı, tarihçi kararı); parçalanma yalnızca
     GÖRÜNÜR kılınıyor: kullanıcı öbür kayda tek tıkla geçebiliyor. */
  const [clusters, setClusters] = useState(null);
  /* H49: yumuşak-silinen pid → kazanan. Birleştirmede kaybeden kayıt
     canonical'da YAŞAR ama havuzda görünmez; eski bağ (kitap müellifi,
     paylaşılmış derin link) yönlendirme olmadan BOŞ EKRANA düşerdi
     (ölçüldü: 17 kitabın 5'inin müellif bağı koptu). */
  const [redirects, setRedirects] = useState(null);

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
    let ara = Number(m[1]);
    /* Yönlendirme: gelen pid yumuşak-silinmişse kazanana çevir. Kullanıcı eski
       bir linkle gelse bile doğru kayda düşer — atıf istikrarının UI tarafı. */
    if (redirects && redirects[String(ara)] != null) ara = Number(redirects[String(ara)]);
    const hit = pool.find((r) => Number(r.id) === ara);
    if (!hit) return;
    setSelected(hit);
    /* Listeyi de o kişiye getir: 22.824 kayıtlık sanal listede seçili kayıt
       ekranın çok dışında kalıyordu (ölçüldü: sağ panel doğru kişiyi açarken
       liste Abū Bakr'dan başlıyordu). Arama kutusunu adıyla doldurmak, kaydırma
       hilesine gerek kalmadan kişiyi listenin başına getirir. */
    setQ(nameTr(hit) || '');
  }, [initialPid, pool, redirects]);

  useEffect(() => {
    fetch('/view-data/ulema_pool_links.json')
      .then((r) => (r.ok ? r.json() : null))
      .then((d) => setLinks(d?.links || {}))
      .catch(() => setLinks({}));
  }, []);
  useEffect(() => {
    fetch('/view-data/person_redirects.json')
      .then((r) => (r.ok ? r.json() : null))
      .then((d) => setRedirects(d?.redirects || {}))
      .catch(() => setRedirects({}));
  }, []);

  useEffect(() => {
    fetch('/view-data/person_clusters.json')
      .then((r) => (r.ok ? r.json() : null))
      .then((d) => setClusters(d?.clusters || {}))
      .catch(() => setClusters({}));
  }, []);

  useEffect(() => {
    fetch('/reading/core_shelf.json')
      .then((r) => (r.ok ? r.json() : null))
      .then((d) => {
        const m = {};
        for (const b of (d?.books || [])) {
          if (b.author_pid) (m[b.author_pid] ||= []).push(b);
        }
        setShelfByAuthor(m);
      })
      /* reading/ ağacı gitignore'da: temiz kopyada dosya YOKTUR ve rozet
         çıkmaz. Sessiz olduğu unutulmasın — "rozet neden yok?" sorusunun ilk
         cevabı `build_reading_data.py` koşulmamış olmasıdır. */
      .catch(() => setShelfByAuthor({}));
  }, []);
  useEffect(() => {                       // notlar: ilk seçimde, bir kez
    if (!selected || notes) return;
    fetch('/view-data/ulema_pool_notes.json')
      .then((r) => (r.ok ? r.json() : null))
      .then((d) => setNotes(d?.notes || {}))
      .catch(() => setNotes({}));
  }, [selected, notes]);

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
            {/* Aynı kişi olabilecek öbür kayıtlar — parçalanmayı görünür kılar */}
            {(() => {
              const c = clusters?.[String(selected.id)];
              /* `goster:false` → zayıf katman. ÖLÇÜLDÜ: 30 zayıf kümenin 15'i
                 gerçekte AYRI kişiydi. Yarısı yanlış olan bir uyarıyı göstermek
                 kullanıcıyı yanlış birleştirmeye teşvik eder; dosyada kalır,
                 ekranda çıkmaz. */
              if (!c || c.goster === false) return null;
              const digerleri = (c.uyeler || []).filter((u) => u !== selected.id);
              if (!digerleri.length) return null;
              const etiket = c.yargi === 'evet' ? (tr ? '✓ incelendi: aynı kişi' : '✓ verified')
                : c.yargi === 'belirsiz' ? (tr ? 'incelendi: doğrulanamadı' : 'inconclusive')
                : { kesin: tr ? 'güçlü kanıt' : 'strong evidence',
                    olasi: tr ? 'olası' : 'likely' }[c.guven] || c.guven;
              return (
                <div style={{ marginTop: 10, padding: '8px 10px', borderRadius: 8,
                  border: `1px solid ${c.yargi === 'evet' ? 'rgba(74,222,128,.45)' : 'rgba(186,104,200,.45)'}`,
                  background: c.yargi === 'evet' ? 'rgba(74,222,128,.07)' : 'rgba(186,104,200,.07)' }}>
                  <div style={{ fontSize: 11.5, color: c.yargi === 'evet' ? '#4ade80' : '#ce93d8', fontWeight: 700 }}>
                    {c.yargi === 'evet' ? '👤' : '⚠'} {tr ? `Aynı kişinin başka kaydı (${digerleri.length}) · ${etiket}`
                          : `Same person, other records (${digerleri.length}) · ${etiket}`}
                  </div>
                  <div style={{ fontSize: 11, opacity: .7, margin: '3px 0 5px' }}>
                    {(c.gerekce || []).join(' · ')}
                  </div>
                  {digerleri.map((u) => {
                    const k = pool?.find((x) => x.id === u);
                    return (
                      <a key={u} href={`#scholars?pid=iac:person-${String(u).padStart(8, '0')}`}
                        style={{ display: 'block', fontSize: 12.5, color: c.yargi === 'evet' ? '#4ade80' : '#ce93d8',
                          textDecoration: 'none', padding: '2px 0' }}>
                        → {k ? nameTr(k) : `iac:person-${String(u).padStart(8, '0')}`}
                        {k?.k?.length ? <span style={{ opacity: .6 }}> · {k.k.join(', ')}</span> : null}
                      </a>
                    );
                  })}
                  <div style={{ fontSize: 10.5, opacity: .55, marginTop: 4 }}>
                    {tr ? 'Kayıtlar BİRLEŞTİRİLMEDİ — birleştirme kararı tarihçinindir.'
                        : 'Records are NOT merged — merging is a historian decision.'}
                  </div>
                </div>
              );
            })()}

            {/* Nottan AYIKLANMIŞ bilgi. Ham `note` alanının %84'ü üretim izidir
                ("cross-reference", "slug=", "Chunk count") — o gösterilmez;
                içine gömülü gerçek bilgi çıkarılır (doğum yeri, uzmanlık,
                kaynağın kendi ölüm ifadesi, serbest not). */}
            {(() => {
              const N = notes?.[String(selected.id)];
              if (!N) return null;
              return (
                <div style={{ fontSize: 12.5, lineHeight: 1.7, marginTop: 10,
                  borderLeft: `2px solid ${GOLD}`, paddingLeft: 9 }}>
                  {N.y && <div><span style={{ opacity: .6 }}>{tr ? 'Doğum yeri' : 'Born in'}: </span>{N.y}</div>}
                  {N.k?.length > 0 && (
                    <div><span style={{ opacity: .6 }}>{tr ? 'Uzmanlık' : 'Field'}: </span>{N.k.join(' · ')}</div>
                  )}
                  {N.o && <div style={{ opacity: .75 }}><span style={{ opacity: .8 }}>{tr ? 'Kaynakta' : 'In source'}: </span>{N.o}</div>}
                  {N.s && <div style={{ opacity: .85, marginTop: 3 }}>{N.s}</div>}
                </div>
              );
            })()}

            {/* Çekirdek Külliyat'ta eseri okunabilen müellif → kitabına git */}
            {(() => {
              const pid = `iac:person-${String(selected.id).padStart(8, '0')}`;
              const kitaplar = shelfByAuthor?.[pid] || [];
              if (!kitaplar.length) return null;
              return (
                <div style={{ marginTop: 12 }}>
                  <div style={{ fontSize: 12, color: GOLD, fontWeight: 700, marginBottom: 5 }}>
                    {tr ? 'Kütüphanede eseri' : 'Readable work'}
                  </div>
                  {kitaplar.map((b) => (
                    <a key={b.pidnum} href={`#library?book=${b.pidnum}`}
                      style={{ display: 'block', padding: '5px 9px', borderRadius: 7, marginBottom: 4,
                        border: `1px solid ${GOLD}`, color: GOLD, textDecoration: 'none', fontSize: 12.5 }}>
                      📖 {b.name_tr} →
                    </a>
                  ))}
                </div>
              );
            })()}

            {/* İlişkiler — hoca / talebe / yer. Sayı gösterilir, tıklanınca
                ilgili kişiye gidilir (pid sözleşmesi, H43). */}
            {(() => {
              const L = links?.[String(selected.id)];
              if (!L) return null;
              const grup = [
                ['h', tr ? 'Hocaları' : 'Teachers'],
                ['o', tr ? 'Talebeleri' : 'Students'],
              ].filter(([k]) => L[k]?.length);
              if (!grup.length && !L.y?.length) return null;
              return (
                <div style={{ marginTop: 14 }}>
                  <div style={{ fontSize: 12, color: GOLD, fontWeight: 700, marginBottom: 6 }}>
                    {tr ? 'İsnâd ve yer bağları' : 'Isnād and place links'}
                  </div>
                  {grup.map(([k, lbl]) => (
                    <div key={k} style={{ fontSize: 12, marginBottom: 5 }}>
                      <span style={{ opacity: .65 }}>{lbl} ({L[k].length}): </span>
                      {L[k].slice(0, 6).map((pid) => {
                        const n = Number(String(pid).split('-').pop());
                        const kisi = pool?.find((x) => x.id === n);
                        /* Havuz dışındaki uç: ham pid basmak yerine DÜRÜST bir
                           etiket. Kenar gerçektir (mağazada var) ama karşı taraf
                           havuz süzgecine girmemiştir; tıklanabilir yapmak boş
                           ekrana götürürdü. */
                        return kisi ? (
                          <a key={pid} href={`#scholars?pid=${encodeURIComponent(pid)}`}
                            style={{ color: GOLD, textDecoration: 'none', marginRight: 8 }}>
                            {nameTr(kisi)}
                          </a>
                        ) : (
                          <span key={pid} style={{ opacity: .45, marginRight: 8 }}
                            title={pid}>{tr ? '(havuz dışı)' : '(outside pool)'}</span>
                        );
                      })}
                      {L[k].length > 6 && <span style={{ opacity: .5 }}>+{L[k].length - 6}</span>}
                    </div>
                  ))}
                  {L.y?.length > 0 && (
                    <div style={{ fontSize: 12, opacity: .7 }}>
                      📍 {tr ? 'Bağlı yer' : 'Places'}: {L.y.length}
                    </div>
                  )}
                </div>
              );
            })()}

            <div style={{ marginTop: 14, fontSize: 12, color: GOLD, fontWeight: 700 }}>
              {tr ? 'Kaynak izleri' : 'Source traces'}
            </div>
            <div style={{ display: 'flex', flexDirection: 'column', gap: 6, marginTop: 8 }}>
              {srcsOf(selected).map((s) => {
                const def = SRC[s];
                if (!def) return null;
                const href = def.href(bridgeByPid(selected.id), selected);
                return href ? (
                  <a key={s} href={href}
                    style={{ padding: '6px 10px', borderRadius: 8, border: `1px solid ${def.color}`, color: def.color, textDecoration: 'none', fontSize: 12.5 }}>
                    {def.label} →
                  </a>
                ) : (
                  <span key={s} title={def.bosNeden || undefined}
                    style={{ padding: '6px 10px', borderRadius: 8, border: '1px solid rgba(255,255,255,.15)', opacity: .55, fontSize: 12.5 }}>
                    {def.label}
                    {def.bosNeden && <span style={{ opacity: .7, fontSize: 11 }}> · {tr ? 'sayfa yok' : 'no page'}</span>}
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
