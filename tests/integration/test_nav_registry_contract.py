"""H33 guard — navigasyon kaydı ↔ uygulama sözleşmesi.

H27 denetimi: aynı sekme listesi BEŞ yerde tekrarlanıyordu; biri unutulunca
SESSİZ kırılıyordu (#visits mobilde erişilemiyordu). H33'te tek kaynak kuruldu:
`web/src/config/navRegistry.js`. Bu test o tekliği kilitler.

Kilitlenenler:
  1) App.jsx sekme listelerini registry'den TÜRETİR (elle dizi geri gelmesin).
  2) BottomTabBar da registry'den beslenir (elle PRIMARY/SECONDARY dizisi yok).
  3) Registry'deki her id App.jsx render dispatch'inde KARŞILANIR
     (sekme menüde var ama ekranı yok → sessiz kırık). Bu, refactor edilmeyen
     ternary zinciriyle registry arasındaki tek gerçek bağdır.
"""
import pathlib
import re

REPO = pathlib.Path(__file__).resolve().parents[2]
APP = REPO / "web" / "src" / "App.jsx"
BTB = REPO / "web" / "src" / "components" / "shared" / "BottomTabBar.jsx"
REG = REPO / "web" / "src" / "config" / "navRegistry.js"


def _registry_ids() -> list[str]:
    src = REG.read_text(encoding="utf-8")
    # NAV_ITEMS içindeki `id: '<x>'` alanları (yardımcı fonksiyonlardaki
    # `it.id` kullanımları eşleşmez, tırnak zorunlu).
    return re.findall(r"\{\s*id:\s*'([a-z0-9]+)'", src)


def test_registry_is_not_empty_and_unique():
    ids = _registry_ids()
    assert len(ids) >= 15, f"registry beklenenden küçük: {len(ids)}"
    assert len(ids) == len(set(ids)), "registry'de yinelenen id var"


def test_app_derives_tab_lists_from_registry():
    """VALID_TABS ve SWIPE_TAB_ORDER elle dizi OLMAMALI."""
    src = APP.read_text(encoding="utf-8")
    assert "navRegistry" in src, "App.jsx registry'yi import etmiyor"
    m = re.search(r"const VALID_TABS = (.+?);", src)
    assert m and "[" not in m.group(1), (
        f"VALID_TABS elle diziye dönmüş: {m.group(1) if m else '?'} — registry'den türetin")
    m2 = re.search(r"const SWIPE_TAB_ORDER = (.+?);", src)
    assert m2 and "[" not in m2.group(1), (
        f"SWIPE_TAB_ORDER elle diziye dönmüş: {m2.group(1) if m2 else '?'}")


def test_bottom_tab_bar_uses_registry():
    src = BTB.read_text(encoding="utf-8")
    assert "navRegistry" in src, "BottomTabBar registry'yi import etmiyor"
    for name in ("PRIMARY_TABS", "SECONDARY_TABS"):
        m = re.search(rf"const {name} = (.{{0,40}})", src, re.S)
        assert m and "itemsFor" in m.group(1), (
            f"{name} elle listeye dönmüş — registry'den türetin")


def _dispatch_block(app: str) -> str:
    """Render dispatch'i (Suspense içindeki ternary zinciri) izole eder.

    H38: bu izolasyon ŞART. Önceki sürüm `tab === '<id>'` ifadesini TÜM dosyada
    arıyordu — nav butonlarının `className={...tab === 'links'...}` ifadeleri de
    eşleştiği için test, render dalı OLMAYAN 'links'i geçirmişti (ölçüldü).
    Yanlış ölçen guard, guard olmamaktan beterdir: yeşil yanar ve korur sanılır.
    """
    start = app.index("<Suspense fallback={<LazyLoader />}>")
    return app[start:app.index("</Suspense>", start)]


def test_every_registry_tab_has_a_render_branch():
    """Menüde olup ekranı olmayan sekme = sessiz kırık."""
    block = _dispatch_block(APP.read_text(encoding="utf-8"))
    # 'admin' dispatch'ten ÖNCE, kendi erken-return'ünde ele alınır.
    missing = [tid for tid in _registry_ids()
               if tid != "admin" and f"tab === '{tid}'" not in block]
    assert not missing, (
        f"registry'de olup App.jsx render dispatch'inde karşılığı olmayan sekme: {missing}")


def test_dispatch_fallback_is_not_a_real_view():
    """Zincirin sonundaki yakalayıcı, dalı unutulan sekmeyi GİZLEMEMELİ.

    H38 ölçümü: yakalayıcı `<CausalView>` idi → dalı yazılmayan her yeni sekme
    sessizce Nedensellik ekranını gösteriyordu. Yakalayıcı haritadır; harita
    zaten `tab === 'map'` dalına da sahip olduğu için ayırt edici bilgi taşımaz
    ve guard testi asıl kilit olarak kalır.
    """
    block = _dispatch_block(APP.read_text(encoding="utf-8"))
    tail = block[block.rindex(" :") :]
    assert "MapView" in tail, f"dispatch yakalayıcısı haritadan başka bir görünüm: {tail[:120]}"


def test_mobile_drawer_derives_from_registry():
    """H38: mobil çekmece elle buton listesine dönmemeli.

    Ölçüldü: registry 22 öğe derken çekmecede 21 elle yazılmış buton vardı ve
    yeni eklenen sekme mobilde hiç görünmüyordu — H27'de kapatılan
    'mobilde erişilemeyen sekme' kusurunun aynısı geri gelmişti.
    """
    app = APP.read_text(encoding="utf-8")
    m = re.search(r'<div className="tabs" role="tablist".*?</div>', app, re.S)
    assert m, "mobil çekmecenin sekme bloğu bulunamadı"
    drawer = m.group(0)
    assert "itemsFor('drawer')" in drawer, "çekmece registry'den türetmiyor"
    elle = drawer.count("selectTab('")
    assert elle == 0, f"çekmecede {elle} elle yazılmış sekme butonu kaldı"


def test_library_curated_shelf_comes_from_registry():
    """H35: Kütüphane'nin 'Kürasyonlu Atlas Görünümleri' rafı elle dizi OLMAMALI.

    Eskiden 7 öğelik sabit diziydi → yeni bir eser-türevi görünüm eklenince raf
    güncellenmiyordu (oto-uyum boşluğu). Artık registry'deki `curated` alanından
    türer; bu test sabit dizinin geri gelmesini engeller."""
    lib = (REPO / "web" / "src" / "components" / "library" / "LibraryView.jsx").read_text(encoding="utf-8")
    assert "curatedItems" in lib, "LibraryView rafı registry'den türetmiyor"
    m = re.search(r"const curated = (.{0,30})", lib, re.S)
    assert m and "[" not in m.group(1), (
        f"curated elle diziye dönmüş: {m.group(1) if m else '?'} — registry'den türetin")
    reg = REG.read_text(encoding="utf-8")
    assert reg.count("curated: {") >= 5, "registry'de kürasyon meta'sı beklenenden az"
