import { Component } from 'react';
import T from '../../../data/i18n';

/**
 * bookkit/ErrorBoundary — görünüm-düzeyi hata sınırı (H17 Dalga-0).
 *
 * YaqutErrorBoundary'den genelleştirildi (görsel çıktı aynı). Repoda 6
 * görünümde aynı sınıfın kopyası var (rihla/muqaddasi/science/lestrange/
 * salibiyyat); kendi dalgalarında buraya göç ederler — Dalga-0'da yalnız
 * Yâkût geçirildi (piksel-parite kapısı tek görünümde tutulur).
 *
 * props: lang, label (console etiketi, ör. 'YaqutView').
 */
export default class ErrorBoundary extends Component {
  constructor(props) { super(props); this.state = { hasError: false, error: null }; }
  static getDerivedStateFromError(error) { return { hasError: true, error }; }
  componentDidCatch(error, info) { console.error(`${this.props.label || 'View'} error:`, error, info); }
  render() {
    if (this.state.hasError) {
      const tl = T[this.props.lang] || T.tr;
      const ty = tl.yaqut || {};
      return (
        <div style={{ padding: 40, textAlign: 'center', color: '#c4b89a' }}>
          <h3>⚠️ {ty.errorOccurred || 'Bir hata oluştu'}</h3>
          <p style={{ color: '#ef5350', fontSize: 12, fontFamily: 'monospace' }}>{String(this.state.error)}</p>
          <button onClick={() => this.setState({ hasError: false, error: null })}
            style={{ marginTop: 16, padding: '8px 16px', background: '#1a6b5a', color: '#fff', border: 'none', borderRadius: 6, cursor: 'pointer' }}>
            {ty.retry || 'Tekrar Dene'}
          </button>
        </div>
      );
    }
    return this.props.children;
  }
}
