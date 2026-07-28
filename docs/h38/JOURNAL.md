# H38 — Oto-uyum vaadinin iki deliği ve yanlış ölçen guard

**Tarih:** 2026-07-28
**Durum:** kapandı

## Nasıl bulundu

H37'de yeni sekmeyi eklerken "registry'ye 1 satır yeter" vaadinin tuttuğunu
ölçtüm ve **kısmen yanlış rapor ettim**: masaüstü açılırını DOM'dan doğrulamış,
mobil çekmece için registry'nin kendi alanını okumakla yetinmiştim. Sonraki
turda dispatch'i incelerken çekmecenin hâlâ elle yazılı olduğu görüldü.

Ders, teknik olandan önce yöntemsel: **kaynağın ne dediğini okumak, arayüzün ne
yaptığını ölçmek değildir.**

## Bulgu 1 — mobil çekmece registry'den türemiyordu (ölçüldü: 22 ↔ 21)

H33 registry'yi tek kaynak olarak kurmuştu; masaüstü açılırları, alt sekme
çubuğu ve `VALID_TAB_IDS` ondan besleniyordu. Ama mobil çekmece bloğu (21 elle
yazılmış `<button>`) hiç dönüştürülmemişti. Sonuç: H37'nin yeni sekmesi
**mobilde hiç erişilemiyordu** — H27'de kapattığımız kusurun aynısı
(o zaman `#visits` mobilde yoktu).

Çekmece artık `itemsFor('drawer')` üzerinden türüyor; etiket `navLabel()` ile
i18n önceliğini koruyor, `preload` alanı kayıtsız aktarılıyor.

Doğrulama: çekmece 22 buton, registry 22 öğe, `⚖️ Nedensellik Onayı` listede.

## Bulgu 2 — dispatch'in yakalayıcısı gerçek bir görünümdü

Ternary zincirinin sonu `<CausalView>` idi ve `tab === 'links'` için **açık bir
dal yoktu**; links yalnızca "zincirin sonuna düştüğü için" çalışıyordu. Bunun
anlamı: dalı yazılmayan **her** yeni sekme sessizce Nedensellik ekranını
gösterir. Görünürde çalışan, aslında yanlış ekran.

`links` açık dal oldu; yakalayıcı haritaya alındı. Harita zaten kendi dalına
sahip olduğu için yakalayıcı artık ayırt edici bilgi taşımıyor — yani hatayı
gizleyemiyor, guard'a bırakıyor.

## Bulgu 3 — guard testi yanlış ölçüyordu (yeşil yanan koruma)

`test_every_registry_tab_has_a_render_branch` `tab === '<id>'` ifadesini **tüm
dosyada** arıyordu. Nav butonlarının `className={...tab === 'links'...}`
ifadeleri de eşleştiği için, render dalı olmayan `links` testten geçmişti.

> Yanlış ölçen guard, guard olmamaktan beterdir: yeşil yanar ve korunduğunuzu
> sanırsınız.

Test artık dispatch bloğunu izole ediyor (`<Suspense>`…`</Suspense>`) ve yalnız
orada arıyor. İki guard daha eklendi: yakalayıcının gerçek görünüm olmaması,
çekmecenin elle listeye dönmemesi.

## Guard'lar mutasyonla sınandı

Yeni testlerin gerçekten koruduğunu varsaymak yerine ölçtüm — her kusur tek tek
geri konup test kırmızıya döndürüldü, sonra geri alındı:

| Mutasyon | Sonuç |
|---|---|
| `links` dalını sil | ✗ `karşılığı olmayan sekme: ['links']` |
| Çekmeceye 1 elle buton koy | ✗ `çekmecede 1 elle yazılmış sekme butonu kaldı` |
| Yakalayıcıyı `CausalView`e döndür | ✗ `yakalayıcısı haritadan başka bir görünüm` |
| (hepsi geri alındı) | ✓ 7 test yeşil |

## Doğrulama

- `make test` → **177 geçti**, 2 atlandı, 3 xfail.
- Mobil: çekmece 22 = registry 22; alt çubuk "Daha" paneli 18 = 18, ⚖️ orada.
- Masaüstü: 12 sekme tek tek gezildi, hepsi dolu içerik döndürdü, konsol hatasız.
  (Pano'nun "0" sayaçları bilinen CountUp/rAF ölçüm artefaktı, kusur değil.)
- `#links` açık dalla çalışıyor: "Nedensellik Ağı 200 / 200 bağlantı".

## Geriye kalan

`App.jsx`'in ternary dispatch'i hâlâ elle (20 dal). H33'te bilerek
dokunulmamıştı; bu turda da dokunulmadı — çünkü artık **üç guard** onu registry
ile hizada tutuyor ve refactor'ün getireceği risk, kalan faydadan büyük.
Kararı Ali verir.
