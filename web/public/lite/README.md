# İslam Atlası v2 — web arayüzü (H11 S8, v0)

Framework'süz, bağımlılıksız statik site; yerel Typesense'e **search-only**
anahtarla konuşur (admin anahtarı `.env`'de kalır, tarayıcıya gitmez).

## Çalıştırma

```bash
docker start islamicatlas-typesense           # arama motoru (port 8108)
node web/serve.mjs 8420                       # statik sunucu
# http://localhost:8420
```

`web/config.js` ÜRETİLİR ve commit edilmez: search-only anahtar
`POST /keys {"actions":["documents:search"],"collections":["iac_entities"]}`
ile üretilip yazılır (bkz. docs/h11 S8 journal).

## Sayfalar

- `index.html` — arama: yazarken-ara, facet'ler (tür / kaynak katmanı /
  alt-tür / hicrî yüzyıl, TR etiketli), vurgulama, sayfalama.
- `entity.html?id=iac:...` — varlık sayfası: üç-dilli başlık, tasvirler,
  diğer adlar, künye, Leaflet haritası (coords varsa), ilişkili varlıklar
  (located_in / patron / author zincirleri tıklanabilir).

## Bilinen sınırlar (v0)

- Leaflet + OSM karoları CDN'den (çevrimdışı değil); üretimde self-host edilecek.
- Varlık sayfası PROJEKSİYON dokümanını gösterir; tam canonical kayıt
  (provenance zinciri, notlar) Faz 2'de ayrı bir detay API'si ister.
- id filtresi tırnaksız (`id:=iac:...`) — Typesense 29.0 davranışı.
