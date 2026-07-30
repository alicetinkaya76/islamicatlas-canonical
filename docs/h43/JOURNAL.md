# H43 — `#scholars?q=Muhammed` neden hiçbir yere gitmiyordu

**Tarih:** 2026-07-30
**Durum:** kapandı
**Tetikleyen:** Ali: *"bize kısmında mesela tıklayınca şöyle bir link yapıyor
buda hiç anlamlı bir yere gitmiyor `http://localhost:3000/#scholars?q=Muhammed`"*

## Üç ayrı kusur üst üste binmişti

**1. Parametre bileşene hiç ulaşmıyordu.** `App.jsx`:

```jsx
tab === 'scholars' ? <ScholarView lang={lang} t={t} /> :
```

`hashParams` vardı, `parseHash` `?q=`'yu doğru ayrıştırıyordu — ama ScholarView'a
**hiçbir parametre geçirilmiyordu**. Yani `#scholars?q=…` baştan beri sessizce
yok sayılıyordu; başka görünümlerin (`alam`, `dia`, `ei1`…) hepsinde bu bağlantı
kuruluydu, yalnız `scholars` atlanmış.

**2. Bağ ADA göre kuruluyordu.** Kayıtta `pid` varken (`iac:person-00005687`)
link `?q=<ad>` üretiyordu. "Muhammed" gibi bir adla arama zaten anlamsız sonuç
verir. Artık `?pid=` üretiliyor; **231 pid'in 231'i havuzda karşılık buluyor**
(ölçüldü). Havuz kimliği sayıdır (`_pid_format: "iac:person-%08d"`), pid'in
sayısal kuyruğu ile çözülüyor.

**3. Doğru ekrana gitse bile yanlış modda açılıyordu.** ScholarView varsayılan
olarak v1'in 450'lik `network` görünümünü açıyor; aranan kişi orada zaten yok.
Pid ile gelindiğinde doğrudan **🕌 Havuz** modu açılıyor ve kayıt seçiliyor.

## Ölçüm sırasında çıkan iki incelik

**`useState` başlangıç değeri yetmez.** Önce `useState(initialPid ? 'pool' :
'network')` yazdım. Sekme **zaten açıkken** hash değişirse bileşen yeniden mount
olmaz ve başlangıç değeri bir daha okunmaz — senkronik şeritten gelen bağ tam
olarak böyle çalışıyor. Ölçüldü: mod "Hoca-Öğrenci Ağı"nda kalıyordu.
`useEffect(..., [initialPid])` ile prop'a tepki verecek hale getirildi.

**Sağ panel doğru, liste yanlış yerdeydi.** Kayıt seçiliyor ve sağ panelde
açılıyordu, ama 22.824 kayıtlık sanal liste Abū Bakr'dan başlıyordu. Arama
kutusu seçilen kişinin adıyla dolduruluyor → liste `1 / 22.824`'e iniyor.
(Sanal listede kaydırma hilesine gerek kalmadı.)

## Yan bulgu — 14 pid↔ad uyuşmazlığı insan kuyruğunda

231 pid bağının **217'sinde** Alatlı adı ile havuz adı örtüşüyor; **14'ünde
örtüşmüyor**. Çoğu aynı kişinin farklı yazımı ve sorun değil:
`Ömer b. Abdülaziz → 'Umar II`, `Hz. Ali → Haydar`, `Şah İsmail → Ismā'īl I`,
`el-Fâiz → al-Fā'iz`.

Ama bir kısmı gerçekten şüpheli — özellikle **`Muhammed → Ahmad`** ve
**`Ahmed b. Hanbel → Ahmad (1.)`**: ikisi de havuzda `roles: ["ruler"]` ile
işaretli, yani bir hükümdar kaydına bağlanmış görünüyorlar.

Otomatik çözülmedi (doktrin: borderline → insan kuyruğu). Liste:
`data/review_queue/alatli_pid_name_mismatch.jsonl` — her satırda Alatlı adı,
pid, havuz adı/Arapçası/rolleri, iki taraftan tarihler ve varsa QID.

## Doğrulama

- Uçtan uca (SPA içi, gerçek kullanıcı akışı): Zaman Çizelgesi → Senkronik →
  Yalnız çağdaşlar → el-Muhakkık el-Hillî çubuğu → panel → **🎓 Âlimler
  havuzunda aç** → `#scholars?pid=iac%3Aperson-00003412` → **🕌 Havuz** modu,
  sağ panelde `HİLLÎ, Muhakkık · ö. 676 H / 1277 M · scholar ·
  iac:person-00003412 · Kaynak izleri: DİA →`, liste `1 / 22.824`.
- Tam sayfa yüklemesinde de aynı (derin link paylaşılabilir).
- `make test` → 178 geçti, 2 atlandı, 3 xfail. Konsol hatasız.

## Ders

Derin link üç halkanın hepsinde çalışmak zorundadır: **(1)** parametre
bileşene geçmeli, **(2)** kimlik ADRESLENEBİLİR olmalı (ad değil pid),
**(3)** hedef ekran doğru MODDA açılmalı. Üçünden biri eksikse bağ "çalışıyor"
görünür ama kullanıcıyı boş bir ekrana bırakır — burada üçü birden eksikti.
