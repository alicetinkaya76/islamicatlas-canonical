"""H47 guard — kişi kümesi sözleşmesi.

Bu katman VERİ-YIKICI OLABİLECEK tek yerdir: yanlış birleştirme iki farklı
tarihsel şahsı tek kayda indirger ve geri alması zordur. Bu yüzden sözleşme
sıkı tutulur:

  1) Küme dosyası hiçbir pid'i SİLMEZ/BİRLEŞTİRMEZ — yalnız gruplar.
  2) "zayıf" katman arayüzde GÖSTERİLMEZ. Ölçüldü: 30 zayıf kümenin 15'i
     gerçekte AYRI kişiydi (ör. "b. Artuk" ↔ "el-Kutbî" — aynı yıl ölmüş iki
     ayrı hanedan mensubu). Yarısı yanlış olan uyarı, kullanıcıyı yanlış
     birleştirmeye teşvik eder.
  3) Yargı "hayır" demiş küme dosyada KALMAZ.
  4) Ölüm yılı FARKLI olan çift küme YAPMAZ.
"""
import json
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[2]
CLUSTERS = REPO / "web" / "public" / "view-data" / "person_clusters.json"
JUDGE = REPO / "data" / "_state" / "person_cluster_judgments.json"
POOL = REPO / "web" / "public" / "books" / "ulema_pool.json"
UI = REPO / "web" / "src" / "components" / "scholars" / "UlemaPool.jsx"

pytestmark = pytest.mark.skipif(not CLUSTERS.is_file(), reason="kümeler üretilmemiş")


@pytest.fixture(scope="module")
def doc():
    return json.loads(CLUSTERS.read_text(encoding="utf-8"))


def test_hicbir_kayit_birlestirilmemis(doc):
    """Küme üyelerinin HEPSİ havuzda ayrı kayıt olarak durmalı."""
    if not POOL.is_file():
        pytest.skip("havuz yok")
    havuz = {r["id"] for r in json.loads(POOL.read_text(encoding="utf-8"))["kisiler"]}
    kayip = {u for v in doc["clusters"].values() for u in v["uyeler"] if u not in havuz}
    assert not kayip, f"küme üyesi havuzdan kaybolmuş (birleştirme yapılmış?): {sorted(kayip)[:5]}"


def test_zayif_katman_gosterilmiyor(doc):
    kacak = [k for k, v in doc["clusters"].items() if v["guven"] == "zayif" and v.get("goster")]
    assert not kacak, f"zayıf küme arayüzde gösteriliyor: {kacak[:5]}"


def test_ui_goster_bayragina_uyuyor():
    src = UI.read_text(encoding="utf-8")
    assert "goster === false" in src, "UI `goster` bayrağını dikkate almıyor — zayıf kümeler sızar"


@pytest.mark.skipif(not JUDGE.is_file(), reason="yargı yok")
def test_ayri_kisi_denen_kume_cikarilmis(doc):
    yargi = json.loads(JUDGE.read_text(encoding="utf-8"))["kararlar"]
    red = {k for k, v in yargi.items() if v["karar"] == "hayir"}
    mevcut = {"-".join(map(str, v["uyeler"])) for v in doc["clusters"].values()}
    kacak = red & mevcut
    assert not kacak, f"yargı AYRI kişi dedi ama küme duruyor: {sorted(kacak)[:5]}"


def test_olum_yili_farkli_kume_yok(doc):
    """Ölçüt: tarih farklıysa küme kurulmaz — gerekçe alanı bunu ele verir."""
    kacak = [k for k, v in doc["clusters"].items()
             if any("farklı" in g for g in v.get("gerekce", []))]
    assert not kacak, f"ölüm yılı farklı olan küme: {kacak[:5]}"


def test_yargi_kalibrasyonu_kayitli():
    """Kalibrasyon ölçümü kaybolmasın — güven eşiğinin gerekçesi budur."""
    if not JUDGE.is_file():
        pytest.skip("yargı yok")
    d = json.loads(JUDGE.read_text(encoding="utf-8"))
    g = d.get("guven_isabeti", {})
    assert g.get("kesin", {}).get("hayir", 1) == 0, \
        "'kesin' katmanda yanlış küme çıkmış — eşik yeniden kalibre edilmeli"
