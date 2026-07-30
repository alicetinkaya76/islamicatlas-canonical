/**
 * PoolLink — kaynak kartlarından Ulema Havuzu'na DÖNÜŞ bağı (H45).
 *
 * SORUN (denetim, docs/h44): havuza dışarıdan pid ile giren yalnız iki rota
 * vardı (senkronik şerit 231 kişi, isnâd ağı 3.393 düğüm). Kullanıcı bir kaynak
 * maddesine (el-Aʿlâm / DİA / EI-1) gidiyor ve ORADA KALIYOR — aynı kişinin
 * öbür kaynaklardaki izlerine, hocasına, yerine dönemiyordu. Kartlar terminal
 * birer siloydu.
 *
 * ÇÖZÜM: üç kartın ortak kullandığı tek düğme. Ölçüldü — lite dosyalarında pid
 * ZATEN var ve havuzda %100 karşılık buluyor:
 *     el-Aʿlâm 12.476/13.844 kayıt · DİA 7.346/8.491 · EI-1 1.144/7.538
 * (pid taşımayan kayıtlarda düğme HİÇ çıkmaz — sahte tıklanabilirlik yok.)
 *
 * Hook KULLANMAZ: erken return'lü kartlarda güvenle çağrılabilir (H42'de
 * koşullu-hook hatası bu depoda bir kez daha ölçülmüştü).
 */

const GOLD = '#c9a84c';

export default function PoolLink({ pid, lang = 'tr', style }) {
  if (!pid) return null;          // kaydın canonical karşılığı yok → düğme yok
  const tr = lang !== 'en';
  return (
    <a href={`#scholars?pid=${encodeURIComponent(pid)}`}
      title={tr ? 'Bu kişinin merkezî defterdeki kaydı: kaynak izleri, hocaları, yerleri'
                : 'This person in the canonical store: source traces, teachers, places'}
      style={{
        display: 'inline-block', padding: '4px 10px', borderRadius: 7,
        border: `1px solid ${GOLD}`, color: GOLD, textDecoration: 'none',
        fontSize: 11.5, cursor: 'pointer', ...style,
      }}>
      🕌 {tr ? 'Âlimler havuzunda' : 'in scholar pool'} →
    </a>
  );
}
