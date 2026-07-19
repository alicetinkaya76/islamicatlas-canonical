export const meta = {
  name: 'extract-batch2-layers',
  description: 'Batch-2: chronicle events (Kamil/Suluk/Tabari/Muruj) + Yaqubi routes + AbuFida coords + Asakir Damascus structures',
  phases: [{ title: 'Kamil' }, { title: 'Suluk' }, { title: 'Tabari' }, { title: 'Muruj' }, { title: 'Yaqubi' }, { title: 'AbuFida' }, { title: 'Asakir' }],
}
const RD = '/Users/alicetinkaya/Desktop/islamicatlas_canonical/web/public/reading'
const RULES = `KURALLAR: SADECE metinde geçeni çıkar; tarih/mesafe/koordinat ifadeleri AYNEN; quote_ar metinden BİREBİR (<=250) ve page o pasajın p değeri; ilgili içerik yoksa boş dizi. Return ONLY structured output.`

const EVENT_SCHEMA = {
  type: 'object', required: ['events'],
  properties: { events: { type: 'array', items: { type: 'object',
    required: ['title_tr', 'place_ar', 'event_type', 'sec', 'confidence', 'summary_tr'],
    properties: {
      title_ar: { type: 'string' }, title_tr: { type: 'string' },
      place_ar: { type: 'string' }, place_tr: { type: 'string' },
      event_type: { type: 'string', enum: ['battle', 'conquest', 'siege', 'treaty', 'founding', 'revolt', 'raid', 'disaster', 'death', 'administration', 'other'] },
      date_text: { type: 'string', description: 'metindeki tarih ifadesi AYNEN (yıl başlıkları: "ثم دخلت سنة كذا")' },
      date_h: { type: 'string', description: 'hicri yıl; kronikte yıl başlığı altındaki olaylar o yıla aittir' },
      leader_ar: { type: 'string' },
      summary_tr: { type: 'string' }, quote_ar: { type: 'string' },
      page: { type: 'string' }, sec: { type: 'number' },
      confidence: { type: 'string', enum: ['high', 'medium', 'low'] },
    } } } },
}
const ROUTE_SCHEMA = {
  type: 'object', required: ['routes'],
  properties: { routes: { type: 'array', items: { type: 'object',
    required: ['from_ar', 'to_ar', 'sec', 'confidence'],
    properties: {
      from_ar: { type: 'string' }, to_ar: { type: 'string' },
      from_tr: { type: 'string' }, to_tr: { type: 'string' },
      distance_text: { type: 'string' }, region_ar: { type: 'string' },
      quote_ar: { type: 'string' }, page: { type: 'string' }, sec: { type: 'number' },
      confidence: { type: 'string', enum: ['high', 'medium', 'low'] },
    } } } },
}
const COORD_SCHEMA = {
  type: 'object', required: ['places'],
  properties: { places: { type: 'array', items: { type: 'object',
    required: ['name_ar', 'sec', 'confidence'],
    properties: {
      name_ar: { type: 'string' }, name_tr: { type: 'string' },
      longitude_text: { type: 'string', description: 'الطول değeri AYNEN' },
      latitude_text: { type: 'string', description: 'العرض değeri AYNEN' },
      clime_text: { type: 'string', description: 'الإقليم' },
      summary_tr: { type: 'string' }, quote_ar: { type: 'string' },
      page: { type: 'string' }, sec: { type: 'number' },
      confidence: { type: 'string', enum: ['high', 'medium', 'low'] },
    } } } },
}
const STRUCT_SCHEMA = {
  type: 'object', required: ['structures'],
  properties: { structures: { type: 'array', items: { type: 'object',
    required: ['name_ar', 'type', 'sec', 'confidence', 'summary_tr'],
    properties: {
      name_ar: { type: 'string' }, name_tr: { type: 'string' },
      type: { type: 'string', enum: ['gate', 'quarter', 'market', 'bridge', 'canal', 'palace', 'mosque', 'church', 'cemetery', 'street', 'bath', 'wall', 'river', 'village', 'other'] },
      builder_ar: { type: 'string' }, date_text: { type: 'string' },
      summary_tr: { type: 'string' }, quote_ar: { type: 'string' },
      page: { type: 'string' }, sec: { type: 'number' },
      confidence: { type: 'string', enum: ['high', 'medium', 'low'] },
    } } } },
}
function batches(n, per, offset = 0) {
  const out = []
  for (let s = offset; s < n; s += per) out.push(Array.from({ length: Math.min(per, n - s) }, (_, k) => s + k))
  return out
}
function chunk(arr, per) {
  const out = []
  for (let i = 0; i < arr.length; i += per) out.push(arr.slice(i, i + per))
  return out
}
const files = (pid, secs) => secs.map(i => `${RD}/${pid}/sec_${String(i).padStart(4, '0')}.json`).join('\n')

phase('Kamil')
const kamil = await parallel(batches(3859, 40).map(secs => () =>
  agent(`İbn el-Esîr'in el-Kâmil fi't-Târîh'inden (yıl yıl evrensel tarih) TARİHSEL OLAY kayıtları çıkar. Bölüm dosyaları:\n${files('00000331', secs)}\n\nKronikte olaylar YIL BAŞLIKLARI altında toplanır ("ثم دخلت سنة ..."): bölümdeki yıl başlığını date_h'ye yaz. Her savaş/fetih/kuşatma/isyan/antlaşma/afet bir kayıt; yer adı zorunlu. Nesep/şiir/genel mülahaza bölümlerini ATLA. ${RULES}`,
    { label: `kamil ${secs[0]}`, phase: 'Kamil', schema: EVENT_SCHEMA, effort: 'low' })))

phase('Suluk')
const suluk = await parallel(batches(553, 12).map(secs => () =>
  agent(`Makrîzî'nin es-Sülûk'ünden (Eyyûbî-Memlük yıl yıl kroniği) TARİHSEL OLAY kayıtları çıkar. Bölüm dosyaları:\n${files('00000508', secs)}\n\nYıl başlıkları date_h'ye. Haçlı seferleri, Moğol akınları, Memlük iç siyaseti; yer adı zorunlu. ${RULES}`,
    { label: `suluk ${secs[0]}`, phase: 'Suluk', schema: EVENT_SCHEMA, effort: 'low' })))

phase('Tabari')
const tabari = await parallel(batches(2487, 40).map(secs => () =>
  agent(`Taberî'nin Târîhu'r-Rusül ve'l-Mülûk'ünden TARİHSEL OLAY kayıtları çıkar. Bölüm dosyaları:\n${files('00000338', secs)}\n\nYıl başlıkları ("ثم دخلت سنة ...") date_h'ye. Her somut olay (savaş, fetih, isyan, vali tayini, ölüm) bir kayıt; yer adı zorunlu. İsnad zincirlerini ve şiiri KAYIT YAPMA. ${RULES}`,
    { label: `tabari ${secs[0]}`, phase: 'Tabari', schema: EVENT_SCHEMA, effort: 'low' })))

phase('Muruj')
const muruj = await parallel(batches(1607, 30).map(secs => () =>
  agent(`Mes'ûdî'nin Mürûcü'z-Zeheb'inden TARİHSEL OLAY kayıtları çıkar. Bölüm dosyaları:\n${files('00000880', secs)}\n\nTarih+coğrafya karışıktır: yalnız somut olayları (savaş, fetih, hânedan değişimi, afet) al; saf coğrafya/âdet tasvirlerini ATLA. Yer adı zorunlu. ${RULES}`,
    { label: `muruj ${secs[0]}`, phase: 'Muruj', schema: EVENT_SCHEMA, effort: 'low' })))

phase('Yaqubi')
const yaqubi = await parallel(batches(102, 5).map(secs => () =>
  agent(`Ya'kûbî'nin Kitâbü'l-Büldân'ından YOL/MESAFE kayıtları çıkar (idari coğrafya: şehirler, yollar, menziller). Bölüm dosyaları:\n${files('00002947', secs)}\n\nHer 'A'dan B'ye şu kadar merhale/fersah' ifadesi bir kayıt. ${RULES}`,
    { label: `yaqubi ${secs[0]}`, phase: 'Yaqubi', schema: ROUTE_SCHEMA, effort: 'medium' })))

phase('AbuFida')
const abufida = await parallel(batches(872, 15).map(secs => () =>
  agent(`Ebü'l-Fidâ'nın Takvîmü'l-Büldân'ından KOORDİNATLI YER kayıtları çıkar (iklim tablolarında şehirlerin boylam الطول ve enlem العرض değerleri verilir). Bölüm dosyaları:\n${files('00002611', secs)}\n\nHer şehir/yer bir kayıt; longitude_text ve latitude_text metindeki değerlerle (derece-dakika, ebced harfleriyle olabilir) AYNEN. ${RULES}`,
    { label: `abufida ${secs[0]}`, phase: 'AbuFida', schema: COORD_SCHEMA, effort: 'medium' })))

phase('Asakir')
const scope = JSON.parse('[1,2,3,4,5,6,7,8,9,10,11,12,13,14,15,16,17,18,19,20,21,22,23,24,25,26,27,28,29,30,31,32,33,34,35,36,37,38,39,40,41,42,43,44,45,46,47,48,49,50,51,52,53,54,55,56,57,58,59,60,63,64,65,66,67,68,69,70,71,72,73,74,75,76,77,78,79,80,81,82,83,84,85,87,88,89,90,92,94,95,96,97,98,99,100,101,102,103,104,105,106,107,108,109,110,115,117,119,123,125,128,129,130,131,132,139,141,142,145,149,150,151,152,153,154,155,156,161,162,168,176,185,186,187,189,191,192,194,195,196,197,198,199]')
const asakir = await parallel(chunk(scope, 6).map(secs => () =>
  agent(`İbn Asâkir'in Târîhu Medîneti Dımaşk'ının TOPOGRAFİK giriş bölümlerinden DIMAŞK YAPILARI çıkar (şehrin surları, kapıları, mahalleleri, Emeviyye Camii, nehirleri, çarşıları, kiliseleri, köyleri). Bölüm dosyaları:\n${files('00000228', secs)}\n\nHer somut Dımaşk yapısı/mekânı bir kayıt; biyografi/hadis içeriğinde yapı yoksa boş dön. ${RULES}`,
    { label: `asakir ${secs[0]}`, phase: 'Asakir', schema: STRUCT_SCHEMA, effort: 'medium' })))

const r = {
  kamil: kamil.filter(Boolean).flatMap(x => x.events || []),
  suluk: suluk.filter(Boolean).flatMap(x => x.events || []),
  tabari: tabari.filter(Boolean).flatMap(x => x.events || []),
  muruj: muruj.filter(Boolean).flatMap(x => x.events || []),
  yaqubi: yaqubi.filter(Boolean).flatMap(x => x.routes || []),
  abufida: abufida.filter(Boolean).flatMap(x => x.places || []),
  asakir: asakir.filter(Boolean).flatMap(x => x.structures || []),
}
log(`kamil:${r.kamil.length} suluk:${r.suluk.length} tabari:${r.tabari.length} muruj:${r.muruj.length} yaqubi:${r.yaqubi.length} abufida:${r.abufida.length} asakir:${r.asakir.length}`)
return r