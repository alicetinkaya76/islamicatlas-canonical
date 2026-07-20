import { useState, useCallback, useRef, useEffect } from 'react';

/**
 * bookkit/VirtualList — jenerik sanal liste (H17 Dalga-0).
 *
 * YaqutSidebar'ın gömülü sanal listesinden çıkarıldı; satır çizimi
 * renderItem prop'una alındı ki 13k'lık Yâkût listesi ile ileride
 * raf/madde listeleri aynı motoru kullanabilsin. DOM çıktısı Yâkût
 * kullanımıyla bire bir aynıdır (piksel-parite).
 */
export default function VirtualList({
  items,
  itemHeight = 68,
  overscan = 5,
  className = '',
  getKey = (item) => item.id,
  renderItem,
}) {
  const containerRef = useRef(null);
  const [scrollTop, setScrollTop] = useState(0);
  const [containerHeight, setContainerHeight] = useState(400);

  useEffect(() => {
    const el = containerRef.current;
    if (!el) return;
    const obs = new ResizeObserver(entries => {
      for (const e of entries) setContainerHeight(e.contentRect.height);
    });
    obs.observe(el);
    return () => obs.disconnect();
  }, []);

  const handleScroll = useCallback((e) => {
    setScrollTop(e.target.scrollTop);
  }, []);

  const startIdx = Math.max(0, Math.floor(scrollTop / itemHeight) - overscan);
  const endIdx = Math.min(items.length, Math.ceil((scrollTop + containerHeight) / itemHeight) + overscan);
  const totalHeight = items.length * itemHeight;
  const offsetY = startIdx * itemHeight;
  const visible = items.slice(startIdx, endIdx);

  return (
    <div ref={containerRef} className={className} onScroll={handleScroll}>
      <div style={{ height: totalHeight, position: 'relative' }}>
        <div style={{ position: 'absolute', top: offsetY, left: 0, right: 0 }}>
          {visible.map(item => renderItem(item, getKey(item)))}
        </div>
      </div>
    </div>
  );
}
