# Hafta 10 — AP (dia_works rich-mint) kickoff

**Status:** Teçhiz edildi, çalıştırılmayı bekliyor. **Blokörler:** (1) Ali'nin
2 kararı (aşağıda), (2) `data/_state` onarım koşularının bitmesi (arka plan
görevi + PHASE0_CLOSEOUT §2). **Ön koşul (hazır):** `adr009_rich_gate()`
(test_work_canonicalize_lib), PidMinter `session()`, work-PID state onarımı
(h9_001), `dia_chunks_rich.json`.

---

## Kritik sınır (H9 close'da saptandı) — AP toplu-mint DEĞİL

ADR-009 bir DiA-side work kaydını ancak (a) ≥2 dil prefLabel, (b) description,
(c) cilt+sayfa locator karşılıyorsa yazdırır. Kaynaklar:

- **AO (`dia_chunks_rich.json`) (c)'yi verdi** — her âlim maddesi için cilt+sayfa
  (Hassâf → cilt 16 s.395). Bu madde-DÜZEYİ; âlimin Arapça adını + locator'ı
  taşır, tek tek eserlerin başlığını/açıklamasını DEĞİL.
- **`dia_works_h5_audit.json` (44.611 başlık)** güven bantları:

| Bant | Sayı | Anlam |
|---|---:|---|
| `no_external_match_dia_only` | **42.449** | ADR-009'un YASAKLADIĞI sig-mint bölgesi (dış doğrulama yok) |
| `low_likely_misattribution` | 1.457 | upstream parser hatası sinyali |
| `moderate_validated_one_source` | **37** | OpenITI/science ile tek-kaynak doğrulanmış |
| `matched_in_either` (toplam) | ~1.519 | en az bir dış eşleşme (Arapça başlık kaynağı olabilir) |

**Sonuç:** Per-work (a) Arapça başlık + (b) açıklama, 42K DiA-only başlık için
YOK (bunları elde etmek her maddenin "eserleri" bölümünü tek tek ayrıştırmayı
gerektirir — AO bunu yapmadı). AP'nin zengin-mint edilebilir kümesi
**dış-eşleşmeli alt küme** (~1.519, kalite filtresi öncesi). 42K DiA-only
başlık ADR-009 gereği MINT EDİLMEZ — bu bir kusur değil, "doğrulanmamış atıf
yok" garantisidir.

## Ali'nin 2 kararı (AP başlamadan)

**Karar A — ADR-009 (a) eşiği, Arapça-başlıksız 2.681 madde için.**
title_ar olmayan maddeler (çoğu modern/Batılı figür) yalnız `tr` prefLabel
taşır → (a)'yı DiA verisiyle geçemez.
- **A1 (öneri):** Katı kal — yalnız ar+tr (veya dış-eşleşmeden gelen ar)
  geçsin; ar-siz maddelerin işleri review kuyruğunda kalsın. En savunulabilir,
  ADR-009'u yazıldığı gibi uygular, yayın için en temiz.
- **A2:** ADR-009 v1.1 ile gevşet — ar yoksa `tr` + Latin transliterasyon (he
  alanı / ALA-LC) 2. dil sayılsın. Mint kapsamı genişler ama "iki dil" iddiası
  zayıflar.

**Karar B — TDV katkıcısı (madde yazarı) modellemesi (proposal Q3/Q4).**
1.423 müellif (`author_raw`, rich dosyada hazır) nereye?
- **B1 (öneri):** Ayrı `iac:contributor-*` namespace (ya da person'da
  `is_tdv_contributor` işaretli minimal kayıt) — DiA katkıcısı ≠ tarihsel
  şahsiyet; ikisini karıştırmak person namespace'i kirletir. `attributed_to`
  buna bağlanır.
- **B2:** Mevcut person namespace'e mint et (basit ama modern akademisyenler
  tarihsel şahsiyetlerle aynı uzayda).
- **B3:** Bu iterasyonda modelleme — yalnız `provenance.attributed_to` string
  olarak ham byline sakla, namespace kararını sonraya ertele (en düşük risk).

> Cevabın "senin önerinle git" ise: **A1 + B1** ile ilerlerim (en savunulabilir,
> ADR-009 doktrinine ve North Star'a en uygun).

## Uygulama iskeleti (Claude, karar sonrası)

1. `pipelines/adapters/dia_works/` — ADR-006 dört-dosya, GERÇEK canonical-mint
   adapter'ı (AO'nun aksine). extract: audit ⋈ dia_chunks_rich ⋈
   dia_slug_to_pid (author linkage). canonicalize: Hassâf şablonu (@type
   [iac:Work], labels ar/tr[/en], composition_temporal âlim ölümünden,
   provenance.derived_from locator = "TDV DİA cilt N s. M", authors=[scholar
   pid], dia_slug="<slug>:title_<i>").
2. **Pre-write gate = `adr009_rich_gate()`** (hazır+testli). Geçemeyen her
   başlık `data/_state/dia_works_review_queue.jsonl`'a → `needs_human_review`,
   ASLA sessiz yazım.
3. **PidMinter `session()`** ile toplu mint (I/O maliyeti ~0).
4. Hassâf `iac:work-00009331`'e idempotent `dia-rich:hassaf` derived_from
   augment (yeniden mint değil).
5. Phase-5 cross-validation testleri: dia-chunks (`dia-chunks:<slug>` person)
   ↔ dia-rich (`dia-rich:<slug>` work) slug tutarlılığı; her mint'in gate'i
   geçtiği; author linkage'ın yalnız disk-doğrulamalı PID kullandığı
   (el_alam guard deseni; phantom-PID audit çıktısına bağlı).
6. `bidirectional`: person.authored_works ↔ work.authors integrity check'i.
7. K raporu: kaç work mint edildi, kaç review kuyruğunda, bant dağılımı —
   koddan sayılır (tahmin yok).

## Kabul (bittiğinde)

- [ ] Yalnız gate'i geçen work'ler canonical'da; geçemeyenler review kuyruğunda,
      sayıları raporlu.
- [ ] Hassâf idempotent augment; çift kayıt yok.
- [ ] Cross-validation + bidirectional testleri yeşil; suite additive.
- [ ] `full_reindex --dry-run` yeni work'lerle 0 fail.
- [ ] AP journal + Karar + K raporu; ADR-009 v1.1 (gevşetme seçilirse).

## Bu doküman ne yapmaz

Mint çalıştırmaz (Ali kararı + onarım koşuları beklenir). Şema değiştirmez
(work.schema `dia_slug`/`authors` mevcut; gerekirse ADR-013 ile v0.4.0).
