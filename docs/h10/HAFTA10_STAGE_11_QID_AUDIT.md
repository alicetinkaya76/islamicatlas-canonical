# Hafta 10 — Stage 11: Wikidata QID denetimi — TAM EVREN (3.073)

**Date:** 2026-07-10 · **Entry:** Stage 10 (`2b48af5`) üstüne.
H7 close'un H8'e vaat edip hiç yapılmadığı iş; yayının veri-kalite kapısı.

## Yöntem

Önce 375'lik katmanlı örneklem; alarm verince TAM EVREN (3.073 QID, 62 batch,
canlı wbgetentities, tanımlayıcı UA, 1 sn/batch). Kurallar: person isim≥85
VEYA ölüm ±3 · place koordinat ≤25 km VEYA isim≥85 · dynasty isim≥85.
Rapor: `data/_state/qid_audit_report.json` (mismatch listesi kanıtlarıyla).

## Sonuç — ADR-002 ≤%5 hedefi KATASTROFİK ihlalde

| ns | evren | OK | MISMATCH | oran |
|---|---:|---:|---:|---:|
| dynasty | 25 | 1 | **24** | **%96** |
| person | 451 | 374 | 76 | %16.9 |
| place | 2.597 | 1.659 | **937** | %36.1 |
| **TOPLAM** | **3.073** | 2.034 | **1.037** | **%33.7** |

Şüpheye yer bırakmayan örnekler: Safevîler→**Spartacus League**, Bûyîler→
futbolcu Ledley King, Eyyûbîler→"calendar date", el-Mutîʿ→şef Riccardo Muti,
Abdurrahman es-Sûfî→aktris Géraldine Pailhas; place'lerde 3.900-13.900 km
sapmalar. Kural-gürültüsü payı var (75-84 sim bandındaki sınır vakalar
gerçek olabilir) — ama baskın sınıf tartışmasız çöp.

## Dürüstlük notu (metodoloji dersi)

H9 incelemesinin "OpenITI seed 8/15 halüsinasyon QID" bulgusu refuter'larca
elenmişti — bu tam-evren ölçümü AYNI hata sınıfının store genelinde gerçek
olduğunu kanıtlıyor: refuter'lar orada fazla-çürütmüş. Adversarial doğrulama
tek yönlü hata da yapabilir; popülasyon ölçümü nihai hakemdir.

## Politika (bu stage NE YAPMAZ)

Store'a DOKUNULMADI (North Star): 1.037 mismatch silinmedi/işaretlenmedi —
temizlik, kademeli kurallı ayrı journal'lı oturum (aşikâr-çöp purge +
sınır-vaka review; Ali onayı). **H7 display-gate'i KALICI** (zaten
confidence<0.85/unreviewed'ı gizliyor — bu denetim gate'in ne kadar isabetli
olduğunun kanıtı). QID'ler temizlenmeden yayınlanmaz.

## Kabul
- [x] Tam evren ölçüldü (örneklem değil); rapor kanıt-listeli; politika net.
