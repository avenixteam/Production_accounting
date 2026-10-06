import { useMemo, useState } from 'react';
import API, { errMsg } from '../api';
import { useToast } from '../components/Toast.jsx';
import { Badge, Button, Card, DateField, DateRange, ErrorBox, Field, Modal, PageHeader, Select, Spinner, Table } from '../components/ui.jsx';
import { useFetch } from '../hooks/useFetch';
import { PAYMENT_TYPES, SALE_STATUS, addMonths, fmtDate, fmtMoney, fmtNum, monthStart, today, widenRange } from '../utils';

export const StatusBadge = ({ status }) => {
  const [label, tone] = SALE_STATUS[status] || [status, 'gray'];
  return <Badge tone={tone}>{label}</Badge>;
};

/** Sotuv tafsilotlari + to'lov qabul qilish + bekor qilish. Qarzdorlik sahifasida ham ishlatiladi. */
export function SaleDetailModal({ saleId, onClose, onChanged }) {
  const toast = useToast();
  const { data: sale, loading, reload } = useFetch(`/sales/${saleId}`);
  const [amount, setAmount] = useState('');
  const [busy, setBusy] = useState(false);

  const pay = async (e) => {
    e.preventDefault();
    setBusy(true);
    try {
      await API.post(`/sales/${saleId}/payments`, { amount: Number(amount) });
      toast.success("To'lov qabul qilindi");
      setAmount('');
      reload();
      onChanged?.();
    } catch (err) {
      toast.error(errMsg(err));
    } finally {
      setBusy(false);
    }
  };

  const cancel = async () => {
    if (!window.confirm(`Sotuv #${saleId} bekor qilinsinmi? Mahsulot omborga qaytariladi.`)) return;
    try {
      await API.delete(`/sales/${saleId}`);
      toast.success('Sotuv bekor qilindi');
      onChanged?.();
      onClose();
    } catch (err) {
      toast.error(errMsg(err));
    }
  };

  return (
    <Modal title={`Sotuv #${saleId}`} onClose={onClose} wide footer={sale && <Button variant="danger" onClick={cancel}>Sotuvni bekor qilish</Button>}>
      {loading || !sale ? <Spinner /> : (
        <>
          <dl className="kv" style={{ marginBottom: 16 }}>
            <dt>Mijoz</dt><dd><b>{sale.customer_name}</b></dd>
            <dt>Sana</dt><dd>{fmtDate(sale.date)}</dd>
            <dt>To'lov turi</dt><dd>{PAYMENT_TYPES[sale.payment_type]}</dd>
            <dt>Holat</dt><dd><StatusBadge status={sale.status} /></dd>
            <dt>Izoh</dt><dd>{sale.note || '—'}</dd>
          </dl>
          <div className="preview">
            <div className="head">Mahsulotlar</div>
            <Table
              rows={sale.items}
              columns={[
                { key: 'product_name', header: 'Mahsulot', render: (i) => <b>{i.product_name}</b> },
                { key: 'partner_name', header: 'Hamkor' },
                { key: 'quantity', header: 'Miqdor', align: 'right', render: (i) => `${fmtNum(i.quantity)} ${i.unit}` },
                { key: 'unit_price', header: 'Narxi', align: 'right', render: (i) => fmtMoney(i.unit_price) },
                { key: 'total_price', header: 'Summa', align: 'right', render: (i) => fmtMoney(i.total_price) },
              ]}
            />
          </div>
          <div className="total-bar"><span>Jami</span><span>{fmtMoney(sale.total_amount)}</span></div>

          {sale.payment_type === 'installment' && (
            <>
              <div className="preview" style={{ marginTop: 16 }}>
                <div className="head">To'lov jadvali — to'langan {fmtMoney(sale.paid_amount)}, qarz <span className={sale.debt > 0 ? 'neg' : ''}>{fmtMoney(sale.debt)}</span></div>
                <Table
                  rows={sale.schedule}
                  columns={[
                    { key: 'due_date', header: 'Muddat', render: (s) => fmtDate(s.due_date) },
                    { key: 'amount', header: 'Summa', align: 'right', render: (s) => fmtMoney(s.amount) },
                    { key: 'paid_amount', header: "To'langan", align: 'right', render: (s) => fmtMoney(s.paid_amount) },
                    {
                      key: 'paid', header: 'Holat',
                      render: (s) => (s.paid ? <Badge tone="green">To'langan</Badge> : s.overdue ? <Badge tone="red">Muddati o'tgan</Badge> : <Badge tone="gray">Kutilmoqda</Badge>),
                    },
                    { key: 'note', header: 'Izoh' },
                  ]}
                />
              </div>
              {sale.debt > 0 && (
                <form onSubmit={pay} className="row gap" style={{ marginTop: 14 }}>
                  <input type="number" step="0.01" min="0.01" max={sale.debt} required placeholder="To'lov summasi" value={amount} onChange={(e) => setAmount(e.target.value)} style={{ maxWidth: 220 }} />
                  <Button type="button" variant="secondary" onClick={() => setAmount(String(sale.debt))}>Butun qarz</Button>
                  <Button type="submit" variant="success" loading={busy}>To'lovni qabul qilish</Button>
                </form>
              )}
            </>
          )}
        </>
      )}
    </Modal>
  );
}

const emptyLine = () => ({ product_id: '', partner_id: '', quantity: '', unit_price: '' });

function SaleForm({ onClose, onSaved }) {
  const toast = useToast();
  const { data: customers } = useFetch('/customers');
  const { data: products } = useFetch('/products');
  const { data: stock } = useFetch('/inventory/finished-products');
  const [head, setHead] = useState({ customer_id: '', date: today(), payment_type: 'cash', note: '' });
  const [lines, setLines] = useState([emptyLine()]);
  const [inst, setInst] = useState([]);
  const [gen, setGen] = useState({ count: 3, first: addMonths(today(), 1) });
  const [saving, setSaving] = useState(false);

  const productMap = useMemo(() => Object.fromEntries((products || []).map((p) => [String(p.id), p])), [products]);
  const update = (i, patch) => setLines(lines.map((l, idx) => (idx === i ? { ...l, ...patch } : l)));

  const total = lines.reduce((s, l) => s + (Number(l.quantity) || 0) * (Number(l.unit_price) || 0), 0);
  const instSum = inst.reduce((s, x) => s + (Number(x.amount) || 0), 0);
  const stockFor = (productId) => (stock || []).filter((s) => String(s.product_id) === String(productId) && s.balance > 0);
  const available = (l) => (stock || []).find((s) => String(s.product_id) === String(l.product_id) && String(s.partner_id) === String(l.partner_id))?.balance ?? 0;

  const generate = () => {
    const n = Math.max(1, Number(gen.count) || 1);
    const base = Math.floor((total / n) * 100) / 100;
    const rows = Array.from({ length: n }, (_, i) => ({
      due_date: addMonths(gen.first, i),
      amount: i === n - 1 ? (Math.round((total - base * (n - 1)) * 100) / 100).toString() : base.toString(),
      note: '',
    }));
    setInst(rows);
  };

  const filled = lines.filter((l) => l.product_id && l.partner_id && Number(l.quantity) > 0);
  const installmentOk = head.payment_type !== 'installment' || (inst.length > 0 && Math.abs(instSum - total) < 0.005);

  const save = async (e) => {
    e.preventDefault();
    setSaving(true);
    try {
      await API.post('/sales', {
        customer_id: Number(head.customer_id),
        date: head.date,
        payment_type: head.payment_type,
        note: head.note.trim() || null,
        items: filled.map((l) => ({
          product_id: Number(l.product_id), partner_id: Number(l.partner_id),
          quantity: Number(l.quantity), unit_price: Number(l.unit_price || 0),
        })),
        installments: head.payment_type === 'installment'
          ? inst.map((x) => ({ due_date: x.due_date, amount: Number(x.amount), note: x.note?.trim() || null }))
          : [],
      });
      toast.success('Sotuv saqlandi');
      onSaved(head.date);
    } catch (err) {
      toast.error(errMsg(err));
    } finally {
      setSaving(false);
    }
  };

  return (
    <Modal
      wide
      title="Yangi sotuv"
      onClose={onClose}
      footer={
        <>
          <Button variant="secondary" onClick={onClose}>Bekor qilish</Button>
          <Button type="submit" form="sale-form" loading={saving} disabled={!filled.length || !installmentOk}>Saqlash</Button>
        </>
      }
    >
      <form id="sale-form" onSubmit={save}>
        <div className="form-grid" style={{ gridTemplateColumns: '2fr 1fr 1fr' }}>
          <Field label="Mijoz *">
            <Select required value={head.customer_id} onChange={(v) => setHead({ ...head, customer_id: v })} options={(customers || []).map((c) => ({ value: c.id, label: c.name }))} />
          </Field>
          <DateField label="Sana *" value={head.date} onChange={(v) => setHead({ ...head, date: v })} />
          <Field label="To'lov turi *">
            <select value={head.payment_type} onChange={(e) => setHead({ ...head, payment_type: e.target.value })}>
              {Object.entries(PAYMENT_TYPES).map(([k, v]) => <option key={k} value={k}>{v}</option>)}
            </select>
          </Field>
        </div>

        <h3 style={{ margin: '18px 0 8px' }}>Mahsulotlar</h3>
        <div className="lines">
          {lines.map((l, i) => (
            <div key={i}>
              <div className="line sale">
                <Select
                  value={l.product_id}
                  onChange={(v) => update(i, { product_id: v, partner_id: '', unit_price: productMap[v]?.price ? String(productMap[v].price) : '' })}
                  options={(products || []).map((p) => ({ value: p.id, label: p.name }))}
                  placeholder="Mahsulot"
                />
                <Select
                  value={l.partner_id}
                  onChange={(v) => update(i, { partner_id: v })}
                  options={stockFor(l.product_id).map((s) => ({ value: s.partner_id, label: `${s.partner_name} (qoldiq: ${fmtNum(s.balance)})` }))}
                  placeholder={l.product_id ? 'Hamkor (omborda bor)' : 'Avval mahsulot'}
                  disabled={!l.product_id}
                />
                <input type="number" step="any" min="0" placeholder="Miqdor" value={l.quantity} onChange={(e) => update(i, { quantity: e.target.value })} />
                <input type="number" step="0.01" min="0" placeholder="Narxi" value={l.unit_price} onChange={(e) => update(i, { unit_price: e.target.value })} />
                <div className="r num"><b>{fmtMoney((Number(l.quantity) || 0) * (Number(l.unit_price) || 0))}</b></div>
                <Button variant="danger" size="sm" type="button" disabled={lines.length === 1} onClick={() => setLines(lines.filter((_, idx) => idx !== i))}>×</Button>
              </div>
              {l.partner_id && Number(l.quantity) > available(l) && <div className="alert warn" style={{ marginTop: 6 }}>Omborda faqat {fmtNum(available(l))} mavjud</div>}
            </div>
          ))}
          <div><Button variant="secondary" size="sm" type="button" onClick={() => setLines([...lines, emptyLine()])}>+ Qator qo'shish</Button></div>
        </div>

        <div className="total-bar"><span>Jami summa</span><span>{fmtMoney(total)}</span></div>

        {head.payment_type === 'installment' && (
          <div className="preview">
            <div className="head">To'lov jadvali (muddatli to'lov)</div>
            <div style={{ padding: 14 }}>
              <div className="row gap wrap" style={{ marginBottom: 12 }}>
                <span className="muted">Teng bo'lib:</span>
                <input type="number" min="1" max="36" style={{ width: 80 }} value={gen.count} onChange={(e) => setGen({ ...gen, count: e.target.value })} />
                <span className="muted">oy, birinchi to'lov:</span>
                <input type="date" style={{ width: 160 }} value={gen.first} onChange={(e) => setGen({ ...gen, first: e.target.value })} />
                <Button type="button" variant="secondary" size="sm" onClick={generate} disabled={total <= 0}>Hisoblash</Button>
              </div>
              <div className="lines">
                {inst.map((x, i) => (
                  <div className="line inst" key={i}>
                    <input type="date" value={x.due_date} onChange={(e) => setInst(inst.map((r, idx) => (idx === i ? { ...r, due_date: e.target.value } : r)))} />
                    <input type="number" step="0.01" min="0" value={x.amount} onChange={(e) => setInst(inst.map((r, idx) => (idx === i ? { ...r, amount: e.target.value } : r)))} />
                    <input placeholder="Izoh" value={x.note} onChange={(e) => setInst(inst.map((r, idx) => (idx === i ? { ...r, note: e.target.value } : r)))} />
                    <Button variant="danger" size="sm" type="button" onClick={() => setInst(inst.filter((_, idx) => idx !== i))}>×</Button>
                  </div>
                ))}
                <div><Button type="button" variant="secondary" size="sm" onClick={() => setInst([...inst, { due_date: gen.first, amount: '', note: '' }])}>+ To'lov qo'shish</Button></div>
              </div>
              {inst.length > 0 && (
                <div className={`alert ${Math.abs(instSum - total) < 0.005 ? 'ok' : 'warn'}`} style={{ marginTop: 12 }}>
                  Jadval yig'indisi: <b>{fmtMoney(instSum)}</b> / sotuv summasi: <b>{fmtMoney(total)}</b>
                  {Math.abs(instSum - total) >= 0.005 && ' — ular teng bo\'lishi kerak'}
                </div>
              )}
            </div>
          </div>
        )}

        <Field label="Izoh" className="mt"><input value={head.note} onChange={(e) => setHead({ ...head, note: e.target.value })} /></Field>
      </form>
    </Modal>
  );
}

export default function Sales() {
  const [filters, setFilters] = useState({ from: monthStart(), to: today(), customer_id: '', status: '' });
  const { data, loading, error, reload } = useFetch('/sales', { date_from: filters.from, date_to: filters.to, customer_id: filters.customer_id, status: filters.status });
  const { data: customers } = useFetch('/customers', { include_inactive: true });
  const [creating, setCreating] = useState(false);
  const [viewId, setViewId] = useState(null);

  const total = (data || []).reduce((s, r) => s + r.total_amount, 0);
  const debt = (data || []).reduce((s, r) => s + r.debt, 0);

  return (
    <>
      <PageHeader
        title="Sotuvlar"
        subtitle="Tayyor mahsulot sotuvi. Saqlanganda mahsulot ombordan chiqariladi."
        actions={<Button onClick={() => setCreating(true)}>+ Yangi sotuv</Button>}
      />
      <Card flush>
        <div className="filters">
          <DateRange from={filters.from} to={filters.to} onChange={({ from, to }) => setFilters({ ...filters, from, to })} />
          <Select value={filters.customer_id} onChange={(v) => setFilters({ ...filters, customer_id: v })} options={(customers || []).map((c) => ({ value: c.id, label: c.name }))} placeholder="Barcha mijozlar" />
          <Select value={filters.status} onChange={(v) => setFilters({ ...filters, status: v })} options={Object.entries(SALE_STATUS).map(([k, [l]]) => ({ value: k, label: l }))} placeholder="Barcha holatlar" />
          <span className="grow" />
          <span className="muted">Jami: <b>{fmtMoney(total)}</b> · Qarz: <b className={debt > 0 ? 'neg' : ''}>{fmtMoney(debt)}</b></span>
        </div>
        <ErrorBox message={error} />
        {loading ? <Spinner /> : (
          <Table
            rows={data}
            empty="Tanlangan davrda sotuv yo'q"
            onRowClick={(r) => setViewId(r.id)}
            columns={[
              { key: 'id', header: '№', width: 60 },
              { key: 'date', header: 'Sana', render: (r) => fmtDate(r.date) },
              { key: 'customer_name', header: 'Mijoz', render: (r) => <b>{r.customer_name}</b> },
              { key: 'items', header: 'Mahsulotlar', render: (r) => r.items.map((i) => `${i.product_name} × ${fmtNum(i.quantity)}`).join(', ') },
              { key: 'payment_type', header: "To'lov", render: (r) => PAYMENT_TYPES[r.payment_type] },
              { key: 'total_amount', header: 'Summa', align: 'right', render: (r) => fmtMoney(r.total_amount) },
              { key: 'debt', header: 'Qarz', align: 'right', render: (r) => (r.debt > 0 ? <span className="neg">{fmtMoney(r.debt)}</span> : '—') },
              { key: 'status', header: 'Holat', render: (r) => <StatusBadge status={r.status} /> },
            ]}
          />
        )}
      </Card>
      {creating && <SaleForm onClose={() => setCreating(false)} onSaved={(d) => { setCreating(false); setFilters((f) => widenRange(f, d)); reload(); }} />}
      {viewId && <SaleDetailModal saleId={viewId} onClose={() => setViewId(null)} onChanged={reload} />}
    </>
  );
}
