/**
 * bookkit/openiti — OpenITI külliyat URI'sinden depo adresi (H55).
 *
 * bookkit anayasası: bir parça ancak İKİNCİ tüketici de isteyince buraya
 * terfi eder. Bu fonksiyon LibraryView'da doğdu; H55'te Ulema Havuzu'nun
 * eser listesi ikinci tüketici oldu ve buraya taşındı.
 *
 * URI biçimi: `<ölüm_yılı_H><MüellifSlug>.<EserSlug>` — ör.
 * `0279Baladhuri.FutuhBuldan`. OpenITI depoları 25 yıllık kovalara bölünmüş
 * (`0275AH`, `0300AH`…); kova, ölüm yılının 25'e yukarı yuvarlanmışıdır.
 *
 * DİKKAT: baştaki dört hane MÜELLİFİN ÖLÜM YILIDIR, eserin telif yılı değil.
 * Aynı sayı `composition_temporal.start_ah` alanına da `approximation:
 * "before"` ile yazılmıştır (ölçüldü: 9.385 kaydın 9.158'i). Arayüzde çıplak
 * yıl olarak gösterilmemelidir.
 */
export function openitiRepoUrl(uri) {
  const m = String(uri || '').match(/^(\d{4})/);
  if (!m) return null;                       // biçimi tutmayan uri → bağ YOK
  const death = parseInt(m[1], 10);
  const bucket = String(Math.ceil(death / 25) * 25).padStart(4, '0') + 'AH';
  const author = String(uri).split('.')[0];
  return `https://github.com/OpenITI/${bucket}/tree/master/data/${author}/${uri}`;
}

export default openitiRepoUrl;
