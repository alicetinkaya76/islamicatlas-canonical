# Hafta 20 — Dalga 3: Ulema Havuzu + eşleştirme turu (2026-07-20)

## S1+S3 — ULEMA HAVUZU (sahip kararının icrası) — commit `3e66f67`

Karar (2026-07-19): *"Âlimler bölümü statik 450'lik set değil; mağazadaki
bütün kişi kayıtlarının süzüldüğü dinamik havuz olacak; her yeni kitapla
kendiliğinden büyür. 450'lik set isnad katmanıyla tohum."*

`build_ulema_pool.py` → `ulema_pool.json` (2,34 MB) + `_meta.json`:
**22.935 kişi** (mağazanın tamamı; kaynak-curie'siz kişi 0; kayıt
atılmadı — 6MB tavanı altında), deterministik sha256 kanıtlı.

Kaynak dağılımı: el-A'lâm 11.379 · DİA 7.383 · kitap/diğer 8.611 ·
EI-1 1.174 · 450-tohum 280 · Bilim 182. Çakışma: a∩d 67 · a∩e 106 ·
d∩e 70 · üçlü 1. Ölüm tarihi: hicrî 19.438 / milâdî 22.736 / tarihsiz
**102** (floruit-birth'ten ÇIKARIM YAPILMADI).

UI: `UlemaPool.jsx` + ScholarView'a **4. mod 🕌 Havuz**. Ağ/İsnâd/Zaman
Çizelgesi görünümlerine DOKUNULMADI (450 seti aynen; bookkit anayasası).
Havuz: bookkit VirtualList (terfi kuralının İLK meyvesi — ikinci tüketici),
TR/AR arama, kaynak filtreleri (meta'dan gerçek sayılar), seçili kişide
**kaynak izleri** → `personBridge.bridgeByPid()` ters indeksiyle
`#alam?id=` / `#dia/<slug>` / `#ei1/<id>` derin linkleri.

Tarayıcı kanıtı: 22.935/22.935; "Gazz" → 25 sonuç; Gazzâlî (ö.505/1111)
→ DİA izi `#dia/gazzali`.

**Dürüst sınırlar (meta'da yazılı):** 450-tohumun 275'i curie ile
izlenebilir, **175'i BİLİNMİYOR** — aynı kişi el-alam/dia curie'siyle
havuzda olabilir; isim eşleştirmesi Faz-2, "havuzda değil" DENMEDİ.
5 yetim `scholars:` curie'si (db.json'da karşılığı yok) listelendi,
otomatik çözülmedi. dia-chunks aileleri bilerek "b" koduna düştü.

**GÖZLEM:** havuz mükerrerleri görünür kıldı — aramada iki ayrı "Gazzâlî"
kaydı. Dup-merge oturumunun yeni kanıt yüzeyi.

## S2 — Eşleştirme turu (Le Strange + Darphaneler)

Teşhis doğrulandı: eksikler **mint değil eşleştirme** sorunu (Bağdat,
Basra, Kûfe, Sâmarrâ, Mûsul, Belh, Şîrâz — hepsi mağazada zaten var,
yalnız curie bağı yok). Curie-artığı her ikisinde 0.

Yeni: `pipelines/integrity/h20_layer_curie_resolve.py` (Tier-2; kalibrasyon
DEĞİŞTİRİLMEDİ, `resolver_weights.yaml` dokunulmadı).

| | evren | curie'siz | auto-match | kuyruk | unmatched |
|---|---|---|---|---|---|
| le-strange | 434 | 219 | **117** | 54 | 48 |
| darp-islam | 3.381 | 1.043 | **753** | 189 | 101 |

Toplamlar evrenle tutuyor. Kuyruklar: `data/review_queue/h20-lestrange.jsonl`
(54), `h20-darpislam.jsonl` (189) — hiçbir borderline otomatik karara
bağlanmadı. Augment (jenerik applier): le-strange 117 uygulandı;
darp-islam 57 yeni + **596 zaten vardı** (boşluk gerçekten yalnız curie
eşlemesiymiş). Şema değişikliği GEREKMEDİ (enum'da ikisi de vardı).

Örnekler: `le-strange:8` al-Kūfah → `iac:place-00010482` (0,9992);
`darp-islam:414/415/1651` Balkh varyantları → tek pid `00002102`;
`darp-islam:689` Carrhae → `Ḥarrān` (Arapça prefLabel exonym köprüsü).

**Zamansal sinyal bilerek verilmedi:** bu iki kaynakta yıl kimlik değil
tanıklık yılıdır (sikke basım aralığı) — ad + konum üstünden eşleşme.

### KARAR H20-1: "Iraq mıknatısı" — H11 S6 dersinin tekrarı

Le Strange `modern_name` alanı "Baghdad, Iraq" biçimli; ülke eki
`token_set_ratio`'da alt-küme sayılıp **koordinatsız "Iraq" kaydını FTS
mıknatısına** çevirdi (smoke koşusunda 34 kuyruk girdisinin 25'i tek
pid'e gidiyordu — H11 S6'nın "(Meçhul Cami)" vakasının aynısı). Ülke eki
kesildi; en yoğun aday 2 girdiye indi. **Kural pekişti: alt-küme
benzerliği kullanan her eşleştirmede "kapsayıcı/idari ek" temizliği
zorunlu ön-adımdır.**

## ALİ'NİN KARARINA KALAN İKİ NOKTA

1. **Kapsam yüzdesi HAREKET ETMEDİ** (le-strange %49,54 / darp %69,15) ve
   etmez: kap kapsamı `source_curie` → `provenance.derived_from`'dan
   üretilir; `derived_from_layers` curie DOĞURMAZ. Yüzdeyi taşımak için
   eşleşen kayıtlara `derived_from` girdisi = **"bu kayıt kısmen şu
   kaynaktan türedi" kimlik/provenance iddiası** yazmak gerekir. Tek
   taraflı YAPILMADI. Tam crosswalk (`curie → pid`) her iki sidecar'da
   `crosswalk` anahtarı altında hazır — karar verilirse promosyon tek koşu.
2. **9 katman-içi dublet adayı** (darp): darp kaydı yine darp'tan mint
   edilmiş bir pid'e eşleşti (ör. `darp-islam:2005` Nīshāpūr →
   `iac:place-00015255`, 0,9999). Augment EDİLMEDİ, `self_layer_matches`
   altında duruyor — DarpIslam-içi mükerrer mint şüphesi, insan bakmalı.

## Kapılar + dürüstlük notu

`make test` **160 passed** (2 skip, 3 xfail) + resolver smoke 5/5.
`build_containers.py` yeniden koştu: 10 kabın hepsi H19 sayılarıyla
birebir aynı.

**Süreç notu:** paralel çalışan iki ajanın işi tek çalışma ağacındaydı;
`3e66f67` (Ulema Havuzu) commit'i `git add -A` ile eşleştirme ajanının
`h20_layer_curie_resolve.py` dosyasını da içine aldı — içerik güncel,
kayıp yok, ama o commit mesajı dosyayı anmıyor. **Ders: paralel ajanlar
aynı ağaçta çalışırken commit kapsamını `git add -A` yerine dosya listesiyle
sınırla** (ya da ajanları worktree izolasyonuyla koş).

## Sıradaki: Dalga 4

rihla "durak" modeli (Evliyâ ve gelecek seyahatnâmelere şablon) + ei1
gürültü triyajı (~%17 unknown/artifact). Ardından yayın paketi
(ontoloji/w3id/v1.0.0/Zenodo) — akademik veritabanı hedefi.
