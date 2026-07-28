# Hafta 34 — Âlimler görünümüne canonical isnâd ağı (Analiz'in son adası)

## Ölçüm önce
| | v1 (db.json) | canonical mağaza |
|---|---|---|
| Âlim | 450 | **3.393** (bağı olan) |
| Hoca–talebe bağı | 155 (H24'te 8 hayalet elenmişti) | **7.869** |

Kaynak: DİA ilişkileri (H11 S11). **Yön H11 S11'de veriyle düzeltilmişti**
(pozisyon-0 TALEBE; v1 sitesi ters gösteriyormuş) — bu ağ o düzeltilmiş yönü
kullanır: kenar **hoca → talebe**.

## Yapılan
`build_scholar_network.py` → `view-data/scholar_network.json`:
- Kenarlar **tekilleştirilir** (A.teachers=[B] ile B.students=[A] aynı kenar).
- Emekli kayıt ve **mağazada karşılığı olmayan uç ATILIR** — 107 hayalet uç
  düşürüldü (H24'te v1 ağında yaşanan hatanın tekrarı önlendi), sayı raporlanır.
- Her düğüme derece yazılır; UI eşik süzgeci uygular.

`CanonicalIsnadNetwork.jsx` — Âlimler görünümüne **5. mod: "🔗 Canonical Ağ"**.
v1'in "Hoca-Öğrenci Ağı" modu **hiç değişmedi** (H26/H28 ek-katman deseni).
D3 kuvvet yerleşimi, zoom/pan, düğüm tıklaması → künye + "Havuzda ara".

## Ölçek dürüstlüğü (ekranda)
3.393 düğüm kuvvet-yerleşiminde ağırdır → **derece eşiği** (varsayılan 8).
Ekranda: *"574 âlim · 2.868 bağ (eşik altında 2.819 âlim gizli)"*.
Kaydırıcı yalnız **görünürlüğü** süzer, veriyi değiştirmez — "az veri var"
izlenimi verilmez.

## Doğrulama
- En bağlantılılar tarihsel olarak **doğru**: Süfyân b. Uyeyne (78),
  Süfyân es-Sevrî (68), Mâlik b. Enes (63), Şa‘bî (61), Ahmed b. Hanbel (54).
- Görsel: altın (ö. < 1000) çekirdek merkezde yoğun, camgöbeği (sonrası) çeperde
  — isnâd ağının beklenen şekli.
- 574 düğüm / 2.868 kenar çizildi, **0 konsol hatası**. Gate 167.

## CausalView neden canonical'a bağlanmadı (dürüst gerekçe)
Canonical mağazada **nedensellik (causal) verisi YOK** — arandı, bulunamadı.
`CausalView`'in db.json'daki 200 nedensel bağda kalması bu yüzden **meşrudur**;
bu bir kaynaşma eksikliği değil, veri yokluğudur. Nedensellik katmanı üretmek
ayrı bir çıkarım işidir (tarihçi onaylı olmalı).

## Değişen dosyalar
- `pipelines/frontend/build_scholar_network.py` (yeni)
- `web/src/components/scholars/CanonicalIsnadNetwork.jsx` (yeni)
- `web/src/components/scholars/ScholarView.jsx` (5. mod düğmesi + render dalı)
- `Makefile`, `scripts/start_local.sh` (üretici build zincirine)
