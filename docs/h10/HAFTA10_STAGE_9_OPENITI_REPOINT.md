# Hafta 10 — Stage 9: openiti phantom sınıfının kök çözümü (index repoint)

**Date:** 2026-07-10 · **Entry:** Stage 8 (`8000f4f`) üstüne.

## Teşhis (koddan; tahmin değil)

1.167 `person:openiti:*` phantom'unun TAMAMI resolution-map'te **tier=2**:
H5'in ilk geçişi her oid'e PID mint'etti; aynı koşuda Tier-2 mevcut-kişi
eşleşmesine çözülenlerin placeholder'ı hiç yazılmadı (doğru davranış), ama
index girdisi ilk-mint pid'inde kaldı. Tier-4 eksik: **0** (2.262/2.262
diskte). **9.331 work kaydının HİÇBİRİ phantom'a referans vermiyor** (tarandı)
— H5 works doğru şekilde map_pid kullanmış. Tek tutarsızlık index: gelecekte
`lookup("openiti:<oid>")` yanlış pid döndürürdü (AP author-linkage tehlikesi).

## Onarım — `h10_001_openiti_index_repoint.py`

1.167 girdi resolution-map pid'ine repoint (idempotent; doğrulama: kalan
openiti-phantom **0**; unfixable 0). pid_counter DOKUNULMADI (ordinal
delikleri belgeli). Canonical kayıt değişmedi.

## Kalan phantom envanteri (1.615) — bilinçli politika

el-alam 1.249 + dia 361 (mint-before-skip: temporal'sız atlanmış varlıkların
rezervasyonu — kaynak ileride tarih verirse idempotent mint AYNI pid'i
doldurur; bu İYİ tasarım) + darp 3 (review-rezerv) + bosworth 2. Politika:
temizlik yok; tüketiciler disk-doğrulamalı.

## Kabul
- [x] verify 0 · idempotent · make test 156.
