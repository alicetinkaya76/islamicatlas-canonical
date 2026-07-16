export const meta = {
  name: 'extract-ibn-jubayr-stops',
  description: 'Ibn Jubayr Rihla: extract dated travel stops per section (Ibn Battuta layer shape)',
  phases: [{ title: 'Extract', detail: '25 agents, 3 sections each' }],
}

const RD = '/Users/alicetinkaya/Desktop/islamicatlas_canonical/web/public/reading/00002694'
const N_SECTIONS = 75
const PER_AGENT = 3

const SCHEMA = {
  type: 'object',
  required: ['stops'],
  properties: {
    stops: {
      type: 'array',
      items: {
        type: 'object',
        required: ['name_ar', 'name_tr', 'sec', 'confidence', 'stay_summary_tr'],
        properties: {
          name_ar: { type: 'string', description: 'yer adı Arapça (metindeki biçim)' },
          name_tr: { type: 'string', description: 'Türkçe yaygın ad (İskenderiye, Mekke...)' },
          name_en: { type: 'string' },
          type: { type: 'string', enum: ['city', 'town', 'port', 'island', 'shrine', 'mountain', 'waypoint', 'sea_passage'], description: 'durak tipi' },
          arrival_text: { type: 'string', description: 'metindeki varış tarihi İFADESİ aynen (ör: "في الثامن عشر من ذي الحجة") — yoksa boş' },
          arrival_h: { type: 'string', description: 'hicri tarih normalize (YYYY-MM-DD ya da YYYY-MM; yıl bölümde yoksa bağlamdan 578-581 aralığında TAHMİN ETME, boş bırak)' },
          departure_text: { type: 'string' },
          stay_summary_tr: { type: 'string', description: 'bu duraktaki anlatının 2-3 cümlelik TR özeti (kendi cümlelerin)' },
          quote_ar: { type: 'string', description: 'duraktan BİREBİR kısa Arapça pasaj (<=300 karakter, metinden aynen kopyala)' },
          page: { type: 'string', description: 'pasajın sayfa çapası (paras[].p alanından, ör V01P045)' },
          sec: { type: 'number', description: 'bölüm indeksi' },
          people: { type: 'array', items: { type: 'object', properties: { name: { type: 'string' }, role: { type: 'string' } } }, description: 'durakta anılan kişiler + rolleri (vali, kadı, şerif...)' },
          is_stay: { type: 'boolean', description: 'true=konakladı, false=geçti/andı' },
          confidence: { type: 'string', enum: ['high', 'medium', 'low'] },
          notes: { type: 'string', description: 'belirsizlik/ihtilaf notu' },
        },
      },
    },
  },
}

const batches = []
for (let s = 0; s < N_SECTIONS; s += PER_AGENT) {
  batches.push(Array.from({ length: Math.min(PER_AGENT, N_SECTIONS - s) }, (_, k) => s + k))
}

phase('Extract')
const results = await parallel(batches.map(secs => () =>
  agent(`Sen İbn Cübeyr'in er-Rihle'sinden (1183-85 hac yolculuğu: Gırnata→Sebte→İskenderiye→Kahire→Yukarı Mısır→Kızıldeniz→Cidde→Mekke[uzun ikamet]→Medine→Irak(Kûfe,Bağdat,Musul)→Suriye(Halep,Şam)→Akkâ→deniz→Sicilya→dönüş) YAPILANDIRILMIŞ SEYAHAT DURAĞI çıkaran bir uzmansın.

Şu bölüm dosyalarını oku (her biri JSON; paras[].t metin, paras[].p sayfa çapası):
${secs.map(i => `${RD}/sec_${String(i).padStart(4, '0')}.json`).join('\n')}

KURALLAR (ihlal = işe yaramaz çıktı):
- SADECE metinde geçeni çıkar; tarih metinde yoksa arrival_h BOŞ kalır — bağlamdan tahmin YASAK (arrival_text'e metindeki ifadeyi aynen koy, ay/gün varsa arrival_h'e normalize et; yıl SADECE metinde açıkça yazıyorsa).
- quote_ar METİNDEN BİREBİR kopya (<=300 karakter) ve page o pasajın p değeri.
- Yalnız İbn Cübeyr'in BİZZAT bulunduğu/geçtiği yerler durak olur (is_stay=true konaklama, false geçiş); sadece SÖZÜ EDİLEN uzak yerler (kıble yönü, başka ülke anılması) DURAK DEĞİLDİR.
- Aynı yerde devam eden anlatı = TEK durak (bölüm başına tekrar açma; sec = anlatının başladığı bölüm).
- Mekke ikameti gibi uzun kalışlarda tek durak + zengin özet.
- Kişiler: metinde adı+rolü geçenler (vali, kadı, hatip, şerif, gemi reisi...).
- confidence: tarih+yer net=high; yer net tarih yok=medium; yer okunuşu şüpheli=low.
- Bu bölümlerde durak yoksa stops=[] döndür (giriş/dua/genel bölümler olabilir).

Return ONLY structured output.`,
    { label: `sec ${secs[0]}-${secs[secs.length - 1]}`, schema: SCHEMA, effort: 'medium' })))

const all = results.filter(Boolean).flatMap(r => r.stops || [])
log(`toplam ham durak: ${all.length}`)
return { total: all.length, stops: all }