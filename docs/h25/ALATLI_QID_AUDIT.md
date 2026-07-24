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

## Nasıl kullanılır
- Worklist: `data/review_queue/alatli-qid-audit.jsonl` (11 çelişki) +
  `alatli-qid-conflicts.jsonl` (2 augment-anı, Gazzâlî Q9546≠store, Cüveynî).
- QID-temizlik oturumunda (Ali-kapılı) her satır: store xref FP mi, store tarih
  hatası mı, yoksa adaş mı → tarihçi karar. Alatlı tarafı date-corroborated.
- Yeniden üret: `python3 pipelines/integrity/alatli_qid_audit.py`.

## Kapsam kazancı (bonus)
Füzyon store QID'li kişi sayısını **412 → 559** çıkardı (+147: 53 mint + 98 augment
QID'i, hepsi tarih-teyitli), display-gate ardında.
