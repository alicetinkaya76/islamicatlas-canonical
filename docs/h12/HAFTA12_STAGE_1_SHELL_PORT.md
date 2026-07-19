# Hafta 12 · Stage 1 — v1 kabuğu v2 reposunda ÇALIŞIYOR

**Tarih:** 2026-07-14 · **Önkoşul:** H12 kickoff

- v1 React uygulaması (React 18 + Vite + Leaflet/markercluster + D3 +
  three.js; 183 dosya, 24 görünüm alanı) `web/` altına taşındı;
  node_modules/dist taşınmadı, `npm install` temiz.
- **128MB silo verisi commit edilmedi:** `web/public/data` → v1 proje
  dizinine SYMLINK (gitignored; geçiş dönemi — her silo canonical'a
  döndükçe küçülür). Kopya isteyen için: dizini symlink yerine kopyala.
- H11 S8'in yalın arayüzü (v0) `web/public/lite/` altına indi — vite
  http://localhost:3000/lite/ altında servis eder; Typesense istemcisi
  S2'de navbar aramasına taşınacak.
- Tarayıcı doğrulaması: landing (sayaç animasyonları gerçek verilerle:
  186 hanedan, 13.940 el-Aʿlâm) → Keşfet → tam harita görünümü (hanedan
  bölgeleri, ticaret rotaları, turlar, yoğunluk) — konsol hatası sıfır.
- Çalıştırma: `npm --prefix web run dev` (port 3000) + Typesense docker
  (lite + S2 araması için).

Not: package.json'daki `puppeteer` bağımlılığı v1 scripts/ kalıntısı —
S2'de üretim bağımlılıklarından çıkarılacak.
