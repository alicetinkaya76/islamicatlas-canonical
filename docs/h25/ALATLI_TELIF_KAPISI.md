# H25 — Alatlı füzyonu: telif / yayın-kapısı

İSAM/DİA deseninin (docs/h22/DIS_BAGIMLILIK_HAZIRLIK.md §C1) Alatlı kaynağına
uygulanışı. Karar verildi; uygulama = yayın anına ertelendi. **Atıf KALIR** —
kaldırmak intihal olur ve riski azaltmaz, artırır.

*Not: hukuki tavsiye değil. Kamuya açık yeniden dağıtım (CC-BY-SA dump) kararı
için derleme-telifi sorusu İSAM izni gibi ayrıca değerlendirilmeli.*

---

## Karar

**Alatlı-türevli kayıtlar yayın-kapısı arkasında tutulur** (kişisel/araştırma
sürümünde kalır; kamuya açık CC-BY-SA dump'a İZİN/karar gelene kadar girmez).
Handle: `source_layer = alatli` (projector `_d_source_layers` prefix_map +
facets'te kayıtlı). Dump B-planı bunu tıpkı `dia` gibi filtreler.

## Neden DİA'dan DAHA AZ hassas

| | DİA | Alatlı |
|---|---|---|
| Store'da telifli **düzyazı/tam-metin** | VAR (dia_chunks 19.742) — asıl risk | **YOK** — hiç pasaj alınmadı |
| Olgular (ad/tarih/koordinat) | pid/ad/tarih bizim | **Wikidata (CC0) + TDV'den** — Alatlı'nın ifadesi değil |
| Telif-hassas kalan | madde tam metni | yalnız **SEÇİM** (hangi kişiler) = ince derleme-telifi |

Yani Alatlı'da "çıkarılacak telifli metin" yok; tek konu editöryel **seçim**.

## Etkilenen veri envanteri (ölçüldü)

| Kalem | Kayıt | Alatlı-bağımlı mı | Yayın durumu |
|---|---|---|---|
| İslami-yeni mint (`iac:person-*`, source_layer=alatli) | **53** | SEÇİM türevli | **kapı arkasında** — izin/karar gelene kadar dump dışı |
| Augment (mevcut store kişilerine) | 183 | HAYIR — kişiler zaten DİA/EI-1/el-Aʿlâm'dan var | eklenen QID/tarih = olgu (Wikidata/TDV) → yayınlanabilir; "Alatlı andı" = atıf |
| Western-held (yan-tablo, MINT DEĞİL) | 280 | evet | zaten canonical değil; dump'a hiç girmez |
| Review kuyruğu | 159 | — | store'da değil |

**Sonuç:** kapı arkasındaki gerçek küme = **53 sadece-Alatlı mint**. 183 augment'in
verisi olgusaldır (Wikidata CC0 + TDV) ve kişiler zaten kamu-malı kaynaklardan
store'da mevcuttur → yayına engel değil.

## Uygulama (yayın anında, İSAM ile birlikte)

Dump B-planı filtresine tek satır: `exclude if source_layer in {dia_fulltext, alatli}`
— VEYA olgu-yalnız sürümde: 53 mint kişisi başka public kaynaktan da varsa kalsın,
yoksa çıkar. Şu an publication İSAM-bloke olduğu için filtre henüz kodda değil;
bu doküman, dia ile aynı "izne-bağlı kaynaklar" kümesine Alatlı'yı ekler.

## Atıf (değişmez)
Her Alatlı kaydında `provenance.derived_from.source_id = "alatli:*"` +
`note`'ta "Alatlı, Tarihe Yön Veren Metinler (Kapadokya Üniversitesi Yayınları)".
Atıf koruyucudur; asla kaldırılmaz.
