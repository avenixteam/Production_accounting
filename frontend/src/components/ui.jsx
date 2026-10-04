import { useEffect } from 'react';

export function PageHeader({ title, subtitle, actions }) {
  return (
    <div className="page-header">
      <div>
        <h1>{title}</h1>
        {subtitle && <p className="muted">{subtitle}</p>}
      </div>
      <div className="row gap">{actions}</div>
    </div>
  );
}

export function Card({ title, actions, children, className = '', flush = false }) {
  return (
    <section className={`card ${className}`}>
      {(title || actions) && (
        <div className="card-head">
          <h3>{title}</h3>
          <div className="row gap">{actions}</div>
        </div>
      )}
      <div className={flush ? '' : 'card-body'}>{children}</div>
    </section>
  );
}

export function StatCard({ label, value, hint, tone = '' }) {
  return (
    <div className={`stat ${tone}`}>
      <div className="stat-label">{label}</div>
      <div className="stat-value">{value}</div>
      {hint && <div className="stat-hint">{hint}</div>}
    </div>
  );
}

export function Badge({ tone = 'gray', children }) {
  return <span className={`badge ${tone}`}>{children}</span>;
}

export function Spinner() {
  return <div className="spinner-wrap"><div className="spinner" /></div>;
}

export function EmptyState({ text = "Ma'lumot topilmadi" }) {
  return <div className="empty">{text}</div>;
}

export function ErrorBox({ message }) {
  return message ? <div className="alert error">{message}</div> : null;
}

export function Modal({ title, onClose, children, footer, wide = false }) {
  useEffect(() => {
    const onKey = (e) => e.key === 'Escape' && onClose();
    document.addEventListener('keydown', onKey);
    return () => document.removeEventListener('keydown', onKey);
  }, [onClose]);

  return (
    <div className="modal-overlay" onMouseDown={(e) => e.target === e.currentTarget && onClose()}>
      <div className={`modal ${wide ? 'wide' : ''}`} role="dialog" aria-modal="true">
        <div className="modal-head">
          <h3>{title}</h3>
          <button className="icon-btn" onClick={onClose} aria-label="Yopish">×</button>
        </div>
        <div className="modal-body">{children}</div>
        {footer && <div className="modal-foot">{footer}</div>}
      </div>
    </div>
  );
}

export function Field({ label, hint, children, className = '' }) {
  return (
    <label className={`field ${className}`}>
      <span className="field-label">{label}</span>
      {children}
      {hint && <span className="field-hint">{hint}</span>}
    </label>
  );
}

/** options: [{value, label}] */
export function Select({ value, onChange, options, placeholder = 'Tanlang...', ...rest }) {
  return (
    <select value={value ?? ''} onChange={(e) => onChange(e.target.value)} {...rest}>
      <option value="">{placeholder}</option>
      {options.map((o) => (
        <option key={o.value} value={o.value}>{o.label}</option>
      ))}
    </select>
  );
}

export function Button({ variant = 'primary', size, loading, children, ...rest }) {
  return (
    <button className={`btn ${variant} ${size || ''}`} disabled={loading || rest.disabled} {...rest}>
      {loading ? '...' : children}
    </button>
  );
}

export function DateRange({ from, to, onChange }) {
  return (
    <div className="row gap">
      <input type="date" value={from} onChange={(e) => onChange({ from: e.target.value, to })} />
      <span className="muted">—</span>
      <input type="date" value={to} onChange={(e) => onChange({ from, to: e.target.value })} />
    </div>
  );
}

export function Table({ columns, rows, rowKey = 'id', empty, onRowClick }) {
  if (!rows?.length) return <EmptyState text={empty} />;
  return (
    <div className="table-wrap">
      <table>
        <thead>
          <tr>
            {columns.map((c) => (
              <th key={c.key} className={c.align === 'right' ? 'r' : ''} style={c.width ? { width: c.width } : undefined}>
                {c.header}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {rows.map((row) => (
            <tr key={row[rowKey]} onClick={onRowClick ? () => onRowClick(row) : undefined} className={onRowClick ? 'clickable' : ''}>
              {columns.map((c) => (
                <td key={c.key} className={c.align === 'right' ? 'r' : ''}>
                  {c.render ? c.render(row) : row[c.key] ?? '—'}
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
