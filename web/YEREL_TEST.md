# İslam Atlası v2 — yerel test

## Tek komut

```bash
bash scripts/start_local.sh
```

Sonra tarayıcıda: **http://localhost:3000**

Script sırasıyla: Typesense'i (arama motoru) başlatır → veriyi kontrol/
yükler → web arayüzünü açar. Durdurmak için `Ctrl+C`.

## Elle (script çalışmazsa)

```bash
# 1) arama motoru
docker start islamicatlas-typesense

# 2) web arayüzü
cd /Users/alicetinkaya/Desktop/islamicatlas_canonical/web
npm run dev -- --port 3000
```

## Ne göreceksin

- **Landing** → Keşfet → tam **harita** (v1 arayüzü, tüm katmanlar)
- **📚 Kütüphane** (üst menü): Çekirdek Külliyat — 10 kitap
  - Her kitapta: tam metin okuyucu (RTL, sayfa atıflı)
  - Kitap Haritası, Rota/Olaylar/Yapılar/Yollar/Bölgeler/Maddeler katmanı
  - Müellif kartı (DİA/el-Aʿlâm bağlantılı)
- Arama, facet'ler, varlık sayfaları

## Notlar

- İlk `npm run dev` biraz yavaş (Vite ön-derleme); sonra anında.
- Onboarding açılırsa "Atla" de.
- Sorun olursa: `docker ps` ile Typesense'in "Up" olduğunu doğrula.
