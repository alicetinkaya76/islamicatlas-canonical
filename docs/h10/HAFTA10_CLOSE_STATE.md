# Hafta 10 — Close state

**Date:** 2026-07-12 · **Branch:** hafta5-work-namespace
**H9 close reference:** `76c2d14`, tag `hafta9-close` · **H10 close tag:** `hafta10-close`

## H10 tek paragrafta

H10, **Tier-2 fuzzy resolver'ı** (H2'den beri stub; ADR-008 §8.2) gerçek
implementasyonla açtı ve ground-truth'la kalibre etti (person auto=0.95,
precision %99.2, 20 ms/resolve), sonra bu motorla **beş kaynağı** canonical'a
dönüştürdü — darp-islam (2.338 mint + 621 augment), scholars (46 augment),
EI1 (964 mint + 224 augment), Evliyâ (2.232 Osmanlı yerleşimi), İbn Battûta
(128 mint + 124 augment) — ve **AN Cat-B'yi** kapattı (2.261 slug bağlandı;
AP'ye hazır slug→pid haritası). Onarım koşuları el-alam'ın kayıp 21 kişisini
hedefli mint'ledi, 1.167 openiti phantom'unu kökten çözdü (repoint;
rejenerasyon dublör üretirdi), 9.330 work'ün provenance adını düzeltti ve
3.199 store-içi dublör adayını + **%33.7 QID yanlış-pozitifini** (3.073'ün
tam-evren denetimi; Safevîler→Spartacus League sınıfı) tarihçi şeridine
çıkardı. Faz 0.5'in **Typesense canlı-yolu kod-tamam** (hosting'e env-kilitli).
Kapanış öncesi 46-ajanlık final inceleme 17 bulgu verdi; 5 veri-onarımı
sınıfı (58 doğum-ölüm, 9+14 çakışma geri-alımı, 8 mükerrer yer, 469 temporal)
ve mimari düzeltmeler (decision-cache ayrımı, preserve-listesi, yer için
year-block kaldırımı) aynı hafta içinde kapatıldı. **14 stage, tamamı
push'lu, sıfır revert.**

## Sayılar (koddan; close anında)

store **52.377** = place 19.929 · person 22.931 · work 9.331 · dynasty 186
· suite **158 passed** / 2 skipped / 3 xfailed · reindex **52.377/52.377**
· phantom envanteri 1.615+8 dedup-rezervi (tümü sınıflı-belgeli)
· tarihçi şeridi: ~4.030 review + 3.199 dublör-çifti + 1.037 QID + çakışma
kuyrukları (an-cat-b-collisions 18, ei1-collisions 14) + triage havuzları.

## H10 commit zinciri

S1 resolver `0eb6a3b` → S2 darp `e3e87e8` → S3 scholars `c5d560a` → S4 ei1
`135cf69` → S5 AN `46cd14d` → S6 onarımlar `6488c84`+`df92c03` → S7 evliya
`0546d26` → S8 ibn-battuta `8000f4f` → S9 openiti-repoint `9e93819` →
S10 typesense `2b48af5` → S11 QID `44f1057` → S12+13 `daebcf5` →
S14 final-remediation `add6117` → close (bu commit).

## H11+ giriş noktası

**Karar-gerektirmeyen makine işi kalmadı.** Her şey PHASE0_CLOSEOUT'taki
Ali-kapılı kalemlerde: AP 2 kararı (kickoff hazır) · event+institution
aktivasyonu (~4.800 yapı + savaşlar + 17 sefer tek kapıda) · İSAM belge
referansı (yayının tek sert blokörü) · v1 db.json (252 yetim kart + 160
kenar) · hosting (upsert 15-dk reçeteli hazır) · frontend kapsamı · LaCie
kararı · QID temizlik oturumu · dublör-merge oturumu.
