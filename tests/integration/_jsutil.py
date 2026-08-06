"""JS/JSX kaynağından yorumları söken ortak yardımcı (H56).

NEDEN ORTAK: bu oturumda ÜÇ kez aynı tuzağa düşüldü — bir kapı, kusuru
AÇIKLAYAN yorumu kusurun kendisi sandı ya da (tersi) yorumdaki kelime
sayesinde kaldırılmış bir kodu hâlâ duruyor sandı:

  H55  evliya/index.js JSDoc'undaki örnek `import` gerçek import sanıldı.
  H56  MapView'da onarımı anlatan yorumdaki '5.618' onarılmamış kod sanıldı.
  H56  EvliyaDetail'de `category_confidence` YORUMDA geçtiği için, kod
       tarafından kaldırıldığında bile test yeşil kaldı (yanlış NEGATİF).

İlk ikisi yanlış alarm, üçüncüsü daha kötüsü: sessiz bir yanlış negatif.
Kusurun ADI kusurun KENDİSİ değildir — her iki yönde de.
"""

import re

_BLOK = re.compile(r"/\*.*?\*/", re.S)


def yorumsuz(metin: str) -> str:
    metin = _BLOK.sub("", metin)
    return "\n".join(
        "" if satir.lstrip().startswith(("//", "*")) else satir
        for satir in metin.split("\n")
    )
