# Hafta 21 — Dalga 4: Durak modeli + EI-1 triyajı (DALGA PLANI TAMAM)

Bu hafta ile **yol haritasının beş dalgasının hepsi** (D0-D4) kapandı.

## S1+S3 — DURAK MODELİ (commit `e7378b9`)

`build_visits.py` → `visits.json`: **18 seyahat / 5.969 durak** ortak
şemada (rihla 317 · ibn-jubayr 208 · evliya 5.444); koordinatlı 5.885,
koordinatsız 84, şüpheli 7 (haritada gizli), pid kapsaması %84,64.
`docs/h21/DURAK_MODELI.md` = şema sözleşmesi + "yeni seyahatnâme nasıl
eklenir" 5 adımlık runbook.

UI: yeni **🧭 Seyahatnâmeler** sekmesi — v1'in Rihla/Evliyâ görünümlerine
dokunulmadı. Tarayıcı kanıtı: İbn Cübeyr Gırnata→Hicaz (208) ile İbn
Battûta ilk hac (65) yan yana; durak #151 Münbic → metindeki varış
ifadesi aynen (Rebî' + Haziran çift takvim) + dup-cluster uyarısı.

### KARAR H21-1: Evliyâ'nın kayıt sırası güzergâh DEĞİL

Ajanın ölçümü: 5.444 kayıt `voyage_id`'ye göre **343 ayrı bloğa örülü**;
`EC_` id'leri dışa-aktarım sırası. `seq: 1..N` yazmak veriye olmayan bir
**güzergâh iddiası** eklerdi. Çözüm: şemaya `sira_turu`
(`metin_tanikli` | `dosya_sirasi`); **UI kuralı: dosya_sirasi'nda çizgi
ÇİZİLMEZ** (çipte ◦ rozeti + tooltip). Ayrıca Evliyâ'da
`volume`/`year_approx` 5444/5444 null (taşınmadı),
`category_confidence` durak güveni DEĞİL (eşlenmedi).

## S2 — EI-1 GÜRÜLTÜ TRİYAJI (en riskli kaynak, bu yüzden son dalgada)

**7.568 = 5.168 sağlam + 388 artifact + 2.012 belirsiz.** Hiçbir kayıt
SİLİNMEDİ; `ei1_lite.json` kaynak dosyasına dokunulmadı — yalnız
işaretleme (`data/_state/ei1_triage.json`).

8 artifact kuralı (hepsi veriden çıkarıldı, örnekli): sayfa üstbilgisi
80 (`al-AHSA  AIBEG`), yazar-imza 176 (`R BASSET and R HARTMANN`),
Roma rakamı 72 (`XVII`), kaynakça kısaltması 32 (`ZDMG`), atıf parçası
14, editoryal aparat 8, yayıncı künyesi 5, hurda 1.

**Belirsiz kova (2.012) insan kuyruğunda**, eşleştirmeye SOKULMADI:
devam-sayfası parçası 858, gövdesiz madde 933, birebir tekrar 221.
Denenip **elenen** kural adayları da raporlandı (kısa başlık 562 —
çoğu meşru 3-harfli Arapça terim; dejenere gövde 541 — çoğu `B.`=ibn'de
kırpılmış gerçek biyografi; küçük-harf başlangıç 150 — OCR bozulması).

**Tip-bazlı eşleştirme** (kalibrasyon değişmedi):
- biography→person 2.352 → auto **24**, kuyruk 947, eşleşmeyen 1.378
- geography→place 836 → auto **0**, kuyruk 336, eşleşmeyen 500

Place'te auto sıfır **yapısal**: resolver auto kapısı ≥2 sinyal ister,
EI-1 yer kayıtlarında koordinat yok → tek sinyal → hepsi kuyruğa.
Person'daki 24 eşleşmenin tamamı 2 sinyalli (etiket + ölüm yılı);
tek sinyalle otomatik eşleşen kayıt YOK.

**H20-1 mıknatıs ön-adımı uygulandı:** EI-1'de virgüllü ülke eki yok
(ölçüldü 0/7.568); buradaki karşılığı iki-maddebaşlı sayfa üstbilgisi
(`al-AHSA  AIBEG` hem "al-Ahsa" hem "Aibeg"in alt kümesi olur) — bunlar
eşleştirmeden ÖNCE artifact'e düştü (94 kayıt). **Mıknatıs kontrolü
temiz:** kuyrukta 1.283 girdi / 1.052 tekil hedef, en yoğun pid 12 girdi
(%0,9) — H20'deki %74 ile kıyaslanamaz.

Augment: 15 person kaydına `derived_from_layers += "ei1"` (idempotent
doğrulandı). Şema: `person.schema.json`'a opsiyonel `derived_from_layers`
(additionalProperties:false olduğu için şarttı), `place.schema.json`
enum'una `"ei1"` — ikisi de geriye-uyumlu.

### ALİ KUYRUĞU — mağaza kirlilik denetimi (bağımsız doğrulama)

Mağazadaki 1.174 `ei1:*` curie'li kaydın **27'si artifact kovasından
mint edilmiş hayalet kişiler**: `iac:person-00024883` = `Lxxxix` (Roma
rakamı), `00025221` = `Zdpv` (dergi kısaltması), `00025523` = `G O W`,
`00025045` = `Ai-KArlSlVA  KADJAR` (sayfa üstbilgisi)… 27'sinin tamamı
gözle doğrulandı, yanlış pozitif yok — bu aynı zamanda kuralların
**bağımsız hassasiyet kanıtı**. 265'i de belirsiz kovasından geliyor.
**Hiçbiri silinmedi/birleştirilmedi**; tam liste `ei1_triage.json` →
`_meta.magaza_kirlilik_denetimi.artifact_kayitlari`. Karar insanda.

## Kapı

`make test` **160 passed** (2 skip, 3 xfail). Kuyruklar: `h21-ei1.jsonl`
1.283 satır (+ H20'den 243) — tarihçi oturumuna hazır.

Süreç dersi uygulandı: commit'ler `git add -A` yerine **dosya listesiyle**
yapıldı; paralel ajanların dosyaları karışmadı (H20 vakasının tekrarı
önlendi).

## DALGA PLANI KAPANDI — sıradaki: yayın paketi

| Dalga | Konu | Durum |
|---|---|---|
| D0 | bookkit + onarımlar + iki bölümlü raf | ✅ H17 |
| D1 | tam-pid beşlisi kaba + yer→kitap köprüsü + arama | ✅ H18 |
| D2 | %80+ beşlisi + kişi köprüsü + Kahire dürüstlüğü | ✅ H19 |
| D3 | eşleştirme turu + ULEMA HAVUZU | ✅ H20 |
| D4 | durak modeli + EI-1 triyajı | ✅ H21 |

**Sırada (kullanıcı onayına):** yayın/akademik paket — ontoloji + w3id
kalıcı adresler + v1.0.0 + Zenodo DOI + veri indirme/API + data paper.
Ön şart olarak duran insan kararları: İSAM izin belgesi (ADR-014),
dup-merge oturumu (artık somut listeler var: work dubletleri, Bağdat×2,
Mekke×8, 27 hayalet EI-1 kaydı), xref↔store id-evreni kopukluğu (1.312),
kap kapsam-yüzdesi promosyonu (provenance iddiası), hosting/DNS.
