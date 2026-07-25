# H25 — Alatlı QID audit (store %33,7 FP'sine katkı)

islamicatlas'ın bilinen sorunu (H10 S11): store QID xref'lerinin %33,7'si
false-positive. Alatlı füzyonunun **yan ürünü** kanıt-güdümlü bir worklist üretti.

## Yöntem
Alatlı'nın 564 QID'i **çift-kaynaklı** (korpus/TDV ölüm yılı + Wikidata tarih-teyidi).
Store'da AYNI Wikidata QID'i **çok farklı tarihli** bir kişide duruyorsa → o store
xref muhtemel FP (ya da store'un tarih hatası). `alatli_qid_audit.py` bunu tarar.

## Bulgular — 11 tarih-çelişkisi (>25 yıl), otomatik düzeltme YOK

| QID | Alatlı (doğru) | store etiketi / yıl | Δ |
|---|---|---|---|
| Q39619 | Hz. Ali ö.661 | "Abū 'l-Hasan 'Alī (1.)" ö.1482 | 821 |
| Q9458 | Muhammed ö.632 | "Muhammad" ö.1058 | 426 |
| Q194442 | Ahmed b. Hanbel ö.855 | "Ahmad (1.)" ö.1545 | 690 |
| Q8474 | Kanuni Süleyman ö.1566 | "Sulaymān (2.)" ö.1016 | 550 |
| Q31066 | Ebû Ca'fer el-Mansûr ö.775 | "al-Mansūr" ö.1045 | 270 |
| Q214559 | Şah İsmail ö.1524 | "Ismā'īl I" ö.1325 | 199 |
| Q168776 | İbrahim ö.1648 | "Ibrāhīm I" | 836 |
| Q2651897 | Mirza Elekber Sâbir ö.1911 | "Sābir" ö.1022 | 889 |
| … (11 toplam) | | | |

Çoğu açık FP: bir Wikidata QID'i (Hz. Ali'nin, Peygamber'in, Kanuni'nin) tamamen
farklı dönemli bir store kişisine yapışmış — display-gate'in ARDINDA temizlenmeyi
bekleyen tam da bu sınıf.

## GENİŞLETME: bir QID birden çok FP-taşıyıcıda

İlk audit QID başına yalnız İLK store kaydını taradı → eksikti. Canlı test bunu
yakaladı: Q39619 (Halife Ali) **6 farklı** store kişisinde (966/982/1121/1482/
1485/1732 — hiçbiri ~661 değil), Q9458 (Muhammed) benzer. Audit store-taraflı
iterasyona çevrildi (`alatli_qid_audit.py`): HER taşıyıcı ayrı denetlenir.
**Ad-eşleşmesi güvenilir DEĞİL** — store "'Alī" ö.1121 + Ali QID = ad aynı ama
FARKLI Ali (yaygın ad). Δ≥100 tek ayraç: hiçbir ömür 100+y değil → aynı kişi
imkânsız, ad ne olursa olsun. Cerrahi kanıt: Q8011'de "Al-Razi ö.925" FP çıktı,
"İbn Sînâ ö.1037" DOĞRU korundu. **Toplam 34 FP-QID temizlendi** (8+26),
qid_quarantine 387→421. Q39619/Q9458 artık 0 taşıyıcı.

## Temizlik uygulandı — Δ≥100 quarantine, Δ<100 tarihçide

`h25_001_alatli_qid_quarantine.py` (h11_001 deseni; SİLME DEĞİL taşıma, geri
alınabilir): **Δ≥100 yıl** olanları quarantine etti — hiçbir ömür 100+ yıl
olmadığından (doğum/ölüm ekseni karışması dahil) aynı kişi imkânsız → kesin FP.

- **8 quarantine** (Δ 199–889): Q39619/Q9458/Q194442/Q8474/Q31066/Q214559/
  Q168776/Q2651897. Örnek doğrulama: Q39619 store "Abū 'l-Hasan 'Alī (1.)"
  ö.1482 = bosworth 15.yy hükümdarı, Halife Ali (ö.661) DEĞİL; xref
  `openrefine_v3` conf 0.83, note'u zaten "Manual review recommended" diyordu.
  → `data/_state/qid_quarantine.json` (387→395), record_history'de kanıt.
- **3 tarihçide (Δ<100)**: Abdülhak Hâmid Tarhan Δ85 (store etiketi Alatlı ile
  BİREBİR → 1852 doğum/1937 ölüm, aynı kişi eksen-karışması, **FP DEĞİL** — dry-run
  bunu yakaladı, eşiği 80→100 yükseltti), Ahmed Rasim Δ67, İbn Yûnus Δ51.
- Ayrıca `alatli-qid-conflicts.jsonl` (2 augment-anı: Gazzâlî Q9546≠store Q320324,
  Cüveynî) tarihçide — store'un QID'i mi FP yoksa adaş mı, isim-eşleşmeli.

Yeniden üret: `alatli_qid_audit.py` → `h25_001_alatli_qid_quarantine.py`.

## Kapsam kazancı (bonus)
Füzyon store QID'li kişi sayısını **412 → 559** çıkardı (+147: 53 mint + 98 augment
QID'i, hepsi tarih-teyitli), display-gate ardında.
