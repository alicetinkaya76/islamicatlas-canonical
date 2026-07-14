# Hafta 12 Kickoff — Sofistike UI: v1 kabuğu → v2 önyüzü

**Tarih:** 2026-07-14 · **Kullanıcı direktifi:** "şuan live sitenin arayüzü
çok beğeniliyordu... version 2'de böyle sofistike bir UI ile devam etmek
istiyoruz."

## Karar (strangler deseni)

v1 React uygulaması (React 18 + Vite, Leaflet+markercluster, D3 ağ/sankey,
24 görünüm alanı, koyu-altın tema) v2'nin ÖNYÜZÜ olarak forklanır; veri
borusu kademeli olarak statik JSON silolarından canonical mağaza +
Typesense'e döner. H11 S8'deki yalın web/ (v0) referans olarak
web/public/lite/ altına iner; Typesense istemcisi + TR facet etiketleri
v0'dan taşınır.

Gerekçe: ADR-004 zaten "mevcut harita/zaman/ağ görselleştirmeleri facet ve
çapraz-referans olarak yeniden çerçevelenir" diyordu — sevilen görsel dil
korunup altı değiştirilir; sıfırdan UI riskli ve gereksiz.

## Aşamalar

1. **S1 taşıma:** src + public(−data) + vite config → web/; public/data
   (128MB silo JSON'ları) gitignore + `scripts/sync_v1_data.sh` (geçiş
   dönemi; her silo canonical'a döndükçe küçülür).
2. **S2 birleşik arama:** navbar'a Typesense araması (57,177 varlık);
   sonuç → tür'e göre derin-bağ (yer→#map, kişi→dia/alam kartı,
   yapı→CityAtlas/harita, olay→battles/salibiyyat).
3. **S3 varlık sayfası:** #entity?id=iac:... route'u v1 görsel dilinde;
   kalıcı kimlik + üç dil + provenance izi.
4. **S4 harita:** ana harita canonical _geo'dan (build-time
   canonical_geo.json emit — "canonical upstream" korunur).
5. **S5 ağ:** DiaNetwork canonical teachers/students kenarlarından —
   v1'in ters-yön hatası (H11 S11 bulgusu) kullanıcı-görünür düzelir.
6. **S6+:** silolar teker teker canonical'a; her aşama kapı+journal+commit.

## Ali-kapılı

- Hosting: statik Vite build (Vercel/Netlify/Pages) + Typesense (Cloud ya
  da VPS docker). İSAM yazısı yayın öncesi şart (ADR-014).
- v1 GitHub repo'sunun geleceği (öneri: arşiv etiketi + README yönlendirme).
