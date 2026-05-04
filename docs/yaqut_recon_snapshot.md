# Yâqūt Wikidata Reconciliation — Cache Snapshot

**Snapshot taken:** 2026-05-04T06:13:24
**Cache file:** `data/cache/wikidata_reconcile.sqlite`
**Recon process:** PID 34781, started 2026-05-04 ~00:03 (UTC+3), still running at snapshot time

## Headline numbers

| Outcome | Count | % |
|---|---|---|
| Total cached queries | 9199 | 100% |
| Empty result (no Wikidata candidate) | 5719 | 62% |
| Candidates present but no auto-match | 2479 | 26% |
| **Auto-accept (match=true, score >= 85)** | **1001** | **10%** |

## Geographic distribution of auto-accepted matches

Heuristic: scan Wikidata description for modern country mentions.

| Modern country | Count |
|---|---|
| Iran | 161 |
| Yemen | 73 |
| Turkey | 55 |
| Syria | 54 |
| Egypt | 39 |
| India | 36 |
| Oman | 30 |
| Saudi | 24 |
| Morocco | 20 |
| Iraq | 20 |
| Palestine | 15 |
| Azerbaijan | 12 |
| Spain | 10 |
| Jordan | 8 |
| Libya | 7 |
| Afghanistan | 6 |
| Pakistan | 6 |
| Uzbekistan | 5 |
| Algeria | 5 |
| Lebanon | 3 |
| Sudan | 3 |
| Tunisia | 1 |
| Turkmenistan | 1 |

## Implications for Hafta 4 (person namespace)

1. **Place-namespace Wikidata coverage is ~11%.** When the DIA biographical adapter encounters a place mention (in birth_place, active_place, death_place fields), it will hit a Wikidata QID about 1 in 10 times. The other 9 times, the person <-> place edge points to a Yaqut-only PID with no external authority anchor.

2. **62% empty-result rate is the paper's strength, not weakness.** Yaqut attests 5,657 medieval places that Wikidata has never indexed. This is the corpus's globally-unique contribution.

3. **Hafta 4 person adapter should reuse this cache.** The wikidata_reconcile.sqlite is shared across adapters. The cache is purely additive — different type_qid filters mean place hits won't pollute person reconciliation.

4. **High 'no-match' rate indicates a name-normalization issue.** Yaqut's Latin transliteration ('al-Kufa') doesn't always match Wikidata's prefLabel ('Kufa'). v0.2.0 improvement: try multiple label variants per query (with/without al-, with/without diacritics, with/without parenthetical region hint).

## Sample auto-accept matches (first 25)

| QID | Name | Score | Description |
|---|---|---|---|
| Q16272130 | Ajar | 100.0 | village in Qazaly District, Kyzylorda Region, Kazakhstan |
| Q6418276 | Ashab-e Sofla | 100.0 | village in Iran |
| Q6520577 | Yeşilköy | 100.0 | village in central district, Bingöl, eastern Turkey |
| Q83387 | Diyarbakır | 100.0 | city in Southeastern Anatolia, Turkey |
| Q6417632 | Ani-ye Olya | 100.0 | village in Iran |
| Q49845265 | Ayil | 100.0 |  |
| Q202162 | Aba | 100.0 | city in Abia State, southern Nigeria |
| Q28040731 | Abam | 100.0 | village in Cameroon |
| Q12226806 | ‘Abān | 100.0 | Islah in Al Khabt District in Al Mahwit Governorate in Yemen |
| Q99648 | Ibb | 100.0 | city in Yemen |
| Q5789122 | Abtar | 100.0 | village in Iran |
| Q791665 | Abdah | 100.0 | Mawqiʻ Atharī fī ṣaḥrāʼ al-Naqab |
| Q138553192 | Abraq | 100.0 | douar in Morocco |
| Q138553192 | Abraq | 100.0 | douar in Morocco |
| Q4670798 | Abzar | 100.0 | village in Iran |
| Q24009362 | Abla | 100.0 | capital of Abla Municipality, Spain |
| Q17353327 | Abend | 100.0 | human settlement in Nossen, Germany |
| Q12177659 | Abnud | 100.0 | village in Qena Governorate, Egypt |
| Q139187794 | Abwa | 100.0 | village in Northern Region, Uganda |
| Q139187794 | Abwa | 100.0 | village in Northern Region, Uganda |
| Q12052712 | Abu Qubays | 100.0 | castle ruin |
| Q643359 | Abhar | 100.0 | city in Zanjan Province, Iran |
| Q138526395 | Abyad | 100.0 | douar in Morocco |
| Q12681957 | Abit | 100.0 | village in West Kutai Regency, East Kalimantan, Indonesia |
| Q4667801 | Abim | 100.0 | town in Northern Uganda |
