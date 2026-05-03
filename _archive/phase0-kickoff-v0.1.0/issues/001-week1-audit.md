---
title: "[Phase 0 — Week 1] Week 1 audit — local run and initial findings"
labels: ["phase0-w1", "type:audit", "good-first-issue"]
milestone: "Week 1: Audit & Inventory"
assignees: ["<fatima-github-username>"]
---

## Hedef

`scripts/week1_audit.py`'yı kendi makinende koş, çıktıyı incele, 3-5 ilgi çekici bulgu veya anormallik bu issue'ya yorum olarak yaz.

## Arka plan

Repo'daki `audit_output_example/` klasörü scriptin bir koşturulmuş örnek çıktısını içeriyor (47 katman, ~105.802 kayıt). Senin kendi makinende koşturarak:
- Aracın senin ortamında da doğru çalıştığını doğrulamak
- Mevcut ham veri yapısını ilk elden görmek
- Phase 0'ın geri kalanı için intuition oluşturmak

## Adımlar

- [ ] Repo'yu klonla:
  ```bash
  git clone git@github.com:alicetinkaya76/islamicatlas-canonical.git
  cd islamicatlas-canonical
  ```
- [ ] Python ortamını kur:
  ```bash
  python3 -m venv .venv
  source .venv/bin/activate
  pip install -r scripts/requirements.txt
  ```
- [ ] Ana atlas repo'sunu yanına klonla (Ali sana yolu verecek)
- [ ] Audit'i koş:
  ```bash
  python3 scripts/week1_audit.py \
      --data-dir ../islamicatlas/public/data \
      --csv-dir  ../islamicatlas/data \
      --extra    ../islamicatlas/public/data/city-atlas \
      --out      ./audit_output
  ```
- [ ] `audit_output/summary.md`'yi oku — toplam özet tablosu + kritik bulgular
- [ ] `audit_output_example/summary.md` ile karşılaştır — aynı mı çıktı? (Aynı olmalı; farklıysa repo/veri drift var demektir)
- [ ] En az 3 katmanın detay raporunu incele (öneri: `yaqut_lite.md`, `alam_lite.md`, `konya.md`)
- [ ] `cross_reference.md` ve `duplicates.md`'yi oku

## Senin yorumunda olması beklenen

- **3-5 bulgu** — dikkatini çeken şeyler. Örnek soru tipleri:
  - Hangi katman en "kirli" (çok null, tipler karışık, sürpriz alanlar)?
  - Hangi şema tekilliği sorunlu (`lat/lng/latitude` gibi)?
  - Hangi katmanda tarih formatı beklemediğin bir şey?
  - Koordinat out-of-range'ler var mı, hangi katmanda?
  - Yinelenen ID raporlarından hangisi gerçek bir sorun, hangisi FK false-positive (scriptin bilinen sınırı)?
  
- **1-2 soru** — scriptin raporladığı ama anlam veremediğin şey
- **1 öneri** — "scripte şunu ekleyebilirdik, şöyle ilginç olur" tarzı

## Definition of done

- [ ] Audit lokal ortamında çalıştı
- [ ] Bulgular bu issue'da yorum olarak yayınlandı
- [ ] Ali 👍 verdi veya takip soruları sordu
- [ ] Çıkan bulgulardan gerekirse yeni issue(lar) açıldı

## İlgili

- Master plan: `docs/phase0-canonical-data-foundation.md` §4 Week 1
- Script dokümantasyonu: `scripts/README.md`
- Örnek çıktı: `audit_output_example/`
