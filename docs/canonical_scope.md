# Canonical Scope — Phase 0 Week 1 Kararı

> **Durum:** Taslak  
> **Sahibi:** Ali Çetinkaya  
> **Teslim tarihi:** Week 1 sonu  
> **İlgili issue:** #2

## Amaç

`audit_output_example/summary.md`'deki 47 dosyanın her birini 4 kategoriden birine yerleştirmek:

| Kategori | Ne demek | Phase 0'daki rolü |
|---|---|---|
| **in-scope canonical** | Canonical store'a migrate edilecek | Week 5 ETL'in girdisi |
| **auxiliary** | Canonical'a doğrudan girmez, ama ETL'e yardımcı (xref, geo lookup) | Week 5 ETL'de ara veri |
| **backup-delete** | Yedek/duplicate, silinecek | Hemen temizlenir |
| **defer-to-phase-1** | Şimdilik bekletilir | Phase 1'de değerlendirilir |

Bu karar Week 5 ETL'in "hangi kaynak canonical'a nereden giriyor" haritasıdır. Taşları buraya doğru dizmek sonraki beş haftayı belirler.

---

## Karar tablosu

### Yer (Place) katmanları

| Dosya | Kayıt | Karar | Canonical hedef | Not |
|---|---:|:-:|---|---|
| `yaqut_lite.json` | 12.954 | **in-scope** | `Place` | Birincil place kaynak; 88.6% koordinat |
| `yaqut_detail.json` | 12.954 | **in-scope** | `Attestation` (surface_form + context) | Yâkût'un tam metni her place için |
| `yaqut_crossref.json` | 8.692 | auxiliary | `Place.attestations` üretimi için | Yâkût ↔ kişi bağlantısı |
| `le_strange_eastern_caliphate.json` | 434 | **in-scope** | `Place` + `Attestation` | Doğu Halifeliği özel, yüksek kalite |
| `le_strange_xref.json` | 468 | auxiliary | ETL sırasında lookup | |
| `muqaddasi_atlas_layer.json` | 3.497 | **in-scope** | `Place` + `Attestation` + `iqlim` | 21 iqlim + 2049 places + routes |
| `muqaddasi_xref.json` | 1.932 | auxiliary | ETL lookup | |
| `dia_geo.json` | 3.803 | auxiliary | `Place.sameAs.dia_url` + koordinat | Geo-only DİA alt kümesi |
| `darpislam_lite.json` | 3.381 | **in-scope** | `Place` (subtype: mint) | 100% koordinat |
| `darpislam_detail_0..6.json` | ~3.381 | auxiliary / **in-scope** | ? | Attestation detayları; karar lazım |
| `ei1_geo.json` | 474 | auxiliary | `Place.sameAs` + koordinat | EI-1 geo alt kümesi |
| `evliya_atlas_layer.json` | 5.454 | **in-scope** | `Place` + `Route` (voyages) | 13.34 MB — büyük |
| `ibn_battuta_atlas_layer.json` | 325 | **in-scope** | `Route` (rihla) + `Place` | 8 duplicate ID — temizle |
| `maqrizi_khitat_atlas_layer.json` | 834 | **in-scope** | `Place` (Cairo structures) | |
| `city-atlas/konya.json` | 583 | **in-scope** | `Place` (Konya structures) | 2 duplicate ID |
| `city-atlas/cairo.json` | 801 | **in-scope** | `Place` (Cairo structures) | Maqrizi ile overlap — ER lazım |

### Kişi (Person) katmanları

| Dosya | Kayıt | Karar | Canonical hedef | Not |
|---|---:|:-:|---|---|
| `alam_lite.json` | 13.940 | **in-scope** | `Person` | Birincil biyografi kaynak |
| `dia_lite.json` | 8.528 | **in-scope** | `Person` + `Place` + `Event` (karışık) | DİA tüm madde tipleri |
| `dia_alam_xref.json` | 2680 | auxiliary | ER köprüsü | Alam ↔ DİA |
| `ei1_lite.json` | 7.568 | **in-scope** | çoklu tip | DİA'ya benzer karışık |
| `science_layer.json` scholars | 182 | **in-scope** | `Person` | Kurası az ama zengin |
| `science_layer.json` institutions | 37 | **in-scope** | `Place` (subtype: institution) | |
| `all_rulers_merged.csv` | 830 | **in-scope** | `Person` (subtype: ruler) | dynasty_id FK |
| `scholars.csv` | 49 | **in-scope** | `Person` | Bosworth ek kayıt; Science Layer ile overlap — ER |

### Hanedan (Dynasty) katmanları

| Dosya | Kayıt | Karar | Canonical hedef | Not |
|---|---:|:-:|---|---|
| `all_dynasties_enriched.csv` | 186 | **in-scope** | `Dynasty` | Bosworth canonical; en olgun CSV |
| `dynasty_analytics.csv` | 186 | auxiliary | `Dynasty.analytics` nested | |
| `dynasty_relations.csv` | 101 | auxiliary | `Dynasty.relations` | |

### Olay (Event) katmanları

| Dosya | Kayıt | Karar | Canonical hedef | Not |
|---|---:|:-:|---|---|
| `battles.csv` | 50 | **in-scope** | `Event` (type: battle) | |
| `events.csv` | 50 | **in-scope** | `Event` | |
| `diplomacy.csv` | 30 | **in-scope** | `Event` (type: diplomatic) | |
| `causal_links.csv` | 200 | auxiliary | `Event.causal_relations` | |
| `salibiyyat_atlas_layer.json` events | 790 | **in-scope** | `Event` | Haçlı seferleri |
| `salibiyyat_atlas_layer.json` castles | 24 | **in-scope** | `Place` (subtype: fortress) | |
| `salibiyyat_atlas_layer.json` routes | 11 | **in-scope** | `Route` | |

### Eser (Work) katmanları

| Dosya | Kayıt | Karar | Canonical hedef | Not |
|---|---:|:-:|---|---|
| `dia_works.json` | dict | **in-scope** | `Work` | DİA'daki eser listeleri |
| `ei1_works.json` | dict | **in-scope** | `Work` | |

### İlişki / edge dosyaları

| Dosya | Karar | Not |
|---|:-:|---|
| `dia_relations.json` | auxiliary | Kişi-kişi edge listesi (`teacher_of`, `cited` vb.) |
| `ei1_relations.json` | auxiliary | EI-1 cross-reference edges |

### Şehir katmanları (major_cities)

| Dosya | Karar | Not |
|---|:-:|---|
| `major_cities.csv` (69) | **in-scope** | `Place` (büyük şehirler, 20 şehir × birden fazla dönem) |

### Yedek dosyalar

| Dosya | Karar | Aksiyon |
|---|:-:|---|
| `salibiyyat_atlas_layer_backup.json` | **backup-delete** | Silinecek |
| `App.jsx.bak` (src/) | **backup-delete** | Silinecek |
| `alam_xrefs_backup.json` (src/) | **backup-delete** | Silinecek |

### Büyük çift yükler

| Dosya | Karar | Not |
|---|:-:|---|
| `dia_chunks.json` (69.5 MB) | **defer-to-phase-1** | RAG için; canonical'a direkt girmez. Phase 2+ embedding pipeline'ında kullanılabilir |
| `src/data/ibn_battuta_atlas_layer.json` (duplicate) | **backup-delete** | `public/data/` versiyonu canonical |
| `src/data/maqrizi_khitat_atlas_layer.json` (duplicate) | **backup-delete** | `public/data/` versiyonu canonical |

### Kaynak yönetimi (Source registry)

Her **in-scope** kayıt için kaynak Source'u belirlenecek. Week 5'te kurulacak Source registry:

| Source ID | Tam kaynak | Reliability tier |
|---|---|---|
| `src_yaqut_mujam` | Yāqūt al-Ḥamawī, *Muʿjam al-buldān* (Beirut: Dār Ṣādir, 1977 reprint) | gold |
| `src_zirikli_alam` | Ḫayr al-Dīn al-Ziriklī, *al-Aʿlām* (15. baskı, 2002) | gold |
| `src_dia` | Türkiye Diyanet Vakfı *İslâm Ansiklopedisi* (1988-2013, 44 cilt) | gold |
| `src_ei1` | *Encyclopaedia of Islam*, 1st ed. (Brill, 1913-1936) | silver |
| `src_bosworth_2004` | Bosworth, C.E. *The New Islamic Dynasties* (Edinburgh UP, 2004) | gold |
| `src_le_strange_1905` | Le Strange, G. *Lands of the Eastern Caliphate* (Cambridge UP, 1905) | gold |
| `src_muqaddasi` | al-Muqaddasī, *Aḥsan al-taqāsīm fī maʿrifat al-aqālīm* | gold |
| `src_maqrizi_khitat` | al-Maqrīzī, *al-Mawāʿiẓ wa'l-iʿtibār (al-Khiṭaṭ)* | gold |
| `src_evliya_seyahatname` | Evliyâ Çelebi, *Seyâhatnâme* (YKY 10-cilt edisyonu) | gold |
| `src_ibn_battuta_rihla` | Ibn Baṭṭūṭa, *Tuḥfat al-nuẓẓār (Riḥla)* | gold |
| `src_darpislam` | DarpIslam corpus / mint registry | silver |
| `src_konyapedia` | Konyapedia (crowdsource tabanlı) | bronze |
| `src_konyali` | İbrahim Hakkı Konyalı, *Konya Tarihi* | gold |

---

## Özet sayılar

Bu karar tablosuna göre:

| Kategori | Dosya sayısı | Kayıt ~ |
|---|---:|---:|
| in-scope canonical | ~25 | ~62.000 |
| auxiliary | ~15 | ~25.000 |
| backup-delete | ~5 | - |
| defer-to-phase-1 | ~2 | ~20.000 |

---

## Açık sorular (ADR gerekebilir)

1. **`darpislam_detail_0..6.json` fragmentasyonu** — bunlar attestation mı, yoksa `Place` detayı mı? Her `mint` için bir place (canonical) vs. her mint için birden fazla attestation (detail)? Karar: ETL'de her detail bloku bir `Attestation` olur, ana mint `Place` olur.

2. **Cairo + Maqrizi çakışması** — Maqrizi Khitat 834 structure, Cairo city atlas 801. Overlap yüksek olmalı. Aynı yapı iki kaynakta görülüyorsa: tek `Place` + iki `Attestation`. Entity resolution (Week 3-4) bunu çözecek.

3. **Science Layer vs. al-Aʿlām vs. scholars.csv overlap** — el-Harezmî en az 3 dosyada. ER kritik.

4. **DİA'nın madde karışıklığı** — DİA'da 8.528 madde var ama bazıları Person, bazıları Place, bazıları Event, bazıları Work. `dia_lite.json`'daki `c1` alanı (bp? fl?) kategorize etmeye yetiyor mu, yoksa Week 2'de bir sınıflandırıcı mı lazım?

5. **Konyapedia tier** — bronze mı silver mi? Reliability tier'ı moderate-quality crowdsource için net değil.

---

## Yapılacaklar (Week 1 sonuna kadar)

- [ ] Yukarıdaki tabloların her hücresi doldurulsun
- [ ] Source registry'de 13 kaynak için tam bibliyografik kayıt hazırlansın (isbn/doi dahil)
- [ ] 5 açık soru için ilk görüş
- [ ] Week 5 ETL'in "kaynak → canonical" mapping dosyasının taslağı (`etl/mapping.yaml` — sonra yazılır)

---

**Son güncellenme:** _________ (Ali tarafından doldurulacak)
