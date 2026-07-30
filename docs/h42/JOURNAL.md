# H42 — Senkronik şerit okunur hale geldi

**Tarih:** 2026-07-30
**Durum:** kapandı
**Tetikleyen:** Ali: *"Alatlı çıkar Senkronik (Doğu↔Batı) kalsın — ekran çok
anlaşılmaz sadece flu mavi kırmızı bir yapı var hiçbir şey anlaşılmıyor mesela
doğudaki alime tıklayınca scholar gidiyor ama nereye gittiği ne gösterdiği
belirsiz."*

## Üç kusur, üçü de haklı

1. **Etiket** — H41'de "⇄ Senkronik — Alatlı (670)" yapmıştım. Ali kaynağın
   adını düğmede istemedi; geri alındı: **"⇄ Senkronik (Doğu↔Batı)"**.
   (Alatlı kaydı ekran altındaki kaynak satırında duruyor.)
2. **Okunmuyordu** — 670 çubuk, `LH = 4` piksel, hiçbirinde ad yok. Ekran
   gerçekten "flu renkli çizgiler"den ibaretti.
3. **Tıklama kaçırıyordu** — `onClick` doğrudan `#scholars?q=…`'ye atıyordu.
   Kullanıcı hangi kişiye tıkladığını, nereye gittiğini ve orada ne göreceğini
   bilmiyordu.

## Yapılanlar

**🔎 "Yalnız çağdaşlar (adlarıyla)" kipi.** Asıl anahtar bu. Kapalıyken 670
isimsiz çubuk; açıkken yalnız seçili yılda yaşayanlar kalıyor, satır yüksekliği
4 → 13 piksele çıkıyor ve **her çubuğun yanına adı yazılıyor**. 1300 yılında
ekran şuna dönüşüyor: BİZE tarafında el-Muhakkık el-Hillî, Kādî Beyzâvî,
en-Nesefî, Reşidüddin Fazlullah, Kemâlüddin el-Fârisî, Âşık Paşa, Dâvûd
el-Kayserî, Ahmed Eflâkî; BATIYA tarafında Duns Scotus, Jean de Joinville,
**Dante Alighieri**, Marsilius. Senkronik bakışın vaadi ancak burada görünür
oluyor.

**Seçili kayıt paneli.** Tıklama artık **yönlendirmiyor** (ölçüldü: hash
değişmiyor). Kimliği açıyor: ad, tarihler, yer, hangi kanonda, 📖 cilt·sayfa ve
alıntı metni. Gidilecek yer **açık düğmeyle** soruluyor:
`🎓 Âlimler havuzunda aç` (yalnız merkezî defterde karşılığı varsa) ve
`↗ Wikidata (Qxxxx)`. Karşılığı yoksa bunu düz yazıyla söylüyor:
*"Merkezî defterde karşılığı yok — yalnız antolojide."*

## Kendi dersimi ihlal ettim

`aliveIdx` haritasını **`useMemo` ile ve erken `return`'lerin ardında** yazdım.
Bu, H17'de AlamView'ı soğuk açılışta çökerten hatanın aynısı: koşullu hook →
render'lar arasında hook sayısı değişir. Düz hesaba çevrildi (670 kayıt için
maliyet ihmal edilebilir), yorumla birlikte.

## Doğrulama

- Tarayıcı: etiket `⇄ Senkronik (Doğu↔Batı)`; kip açıkken SVG'de gerçek adlar
  (`en-Nesefî`, `Dante Alighieri`, …); tıklamada `location.hash` **değişmiyor**;
  panelde `🎓 Âlimler havuzunda aç` + `↗ Wikidata (Q12223449)`; konsol hatasız.
- `make test` → 178 geçti.

## Not — "Doğu↔Batı" etiketi ile verinin gerilimi

Düğme yeniden "Doğu↔Batı" diyor, şeritler ise "BİZE / BATIYA". Bu bilinçli bir
tercih değil, **Ali'nin kararı**: kaynak notu açıkça *"canon = Alatlı'nın
EDİTÖRYEL çerçevesi, coğrafya DEĞİL"* diyor ve ekran altındaki uyarı bunu
yazmaya devam ediyor. Etiket ile içerik arasındaki bu fark kayda geçirildi;
ileride biri "Doğu = coğrafya" diye okursa kaynak burasıdır.
