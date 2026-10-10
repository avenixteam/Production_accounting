import { useMemo, useState } from 'react';
import API, { errMsg } from '../api';
import { useToast } from '../components/Toast.jsx';
import { Badge, Button, Card, DateField, DateRange, ErrorBox, Field, Modal, PageHeader, Select, Spinner, Table } from '../components/ui.jsx';
import { useFetch } from '../hooks/useFetch';
import { PAYMENT_TYPES, SALE_STATUS, fmtDate, fmtMoney, fmtNum, monthStart, today, widenRange } from '../utils';

export const StatusBadge = ({ status }) => {
  const [label, tone] = SALE_STATUS[status] || [status, 'gray'];
  return <Badge tone={tone}>{label}</Badge>;
};

/** Sotuv tafsilotlari, to'lovlar tarixi, qarz to'lash va bekor qilish. Qarzdorlik sahifasida ham ishlatiladi. */
export function SaleDetailModal({ saleId, onClose, onChanged }) {
  const toast = useToast();
  const { data: sale, loading, reload } = useFetch(`/sales/${saleId}`);
  const [pay, setPay] = useState({ amount: '', date: today(), note: '' });
  const [busy, setBusy] = useState(false);

  const submit = async (e) => {
    e.preventDefault();
    setBusy(true);
    try {
      await API.post(`/sales/${saleId}/payments`, { amount: Number(pay.amount), date: pay.date, note: pay.note.trim() || null });
      toast.success("To'lov qabul qilindi, qarzdan ayrildi");
      setPay({ amount: '', date: today(), note: '' });
      reload();
      onChanged?.();
    } catch (err) {
      toast.error(errMsg(err));
    } finally {
      setBusy(false);
    }
  };

  const cancel = async () => {
    if (!window.confirm(`Sotuv #${saleId} butunlay o'chirilsinmi? To'lovlari ham o'chadi.`)) return;
    try {
      await API.delete(`/sales/${saleId}`);
      toast.success("Sotuv o'chirildi");
      onChanged?.();
      onClose();
    } catch (err) {
      toast.error(errMsg(err));
    }
  };

  return (
    <Modal title={`Sotuv #${saleId}`} onClose={onClose} wide footer={sale && <Button variant="danger" onClick={cancel}>Sotuvni o'chirish</Button>}>
      {loading || !sale ? <Spinner /> : (
        <>
          <dl className="kv" style={{ marginBottom: 16 }}>
            <dt>Mijoz</dt><dd><b>{sale.customer_name}</b></dd>
            <dt>Sana</dt><dd>{fmtDate(sale.date)}</dd>
            <dt>Holat</dt><dd><StatusBadge status={sale.status} /></dd>
            <dt>Izoh</dt><dd>{sale.note || '—'}</dd>
          </dl>
          <div className="preview">
            <div className="head">Mahsulotlar</div>
            <Table
              rows={sale.items}
              columns={[
                { key: 'product_name', header: 'Mahsulot', render: (i) => <b>{i.product_name}</b> },
                { key: 'quantity', header: 'Miqdor', align: 'right', render: (i) => `${fmtNum(i.quantity)} ${i.unit}` },
                { key: 'unit_price', header: 'Narxi', align: 'right', render: (i) => fmtMoney(i.unit_price) },
                { key: 'total_price', header: 'Summa', align: 'right', render: (i) => fmtMoney(i.total_price) },
              ]}
            />
          </div>
          <div className="total-bar"><span>Jami</span><span>{fmtMoney(sale.total_amount)}</span></div>
          <div className="grid cols-4" style={{ marginTop: 12 }}>
            <div className="alert ok">To'langan: <b>{fmtMoney(sale.paid_amount)}</b></div>
            <div className={`alert ${sale.debt > 0 ? 'error' : 'ok'}`}>Qarz: <b>{fmtMoney(sale.debt)}</b></div>
          </div>

          <div className="preview">
            <div className="head">To'lovlar tarixi</div>
            <Table
              rows={sale.payments}
              empty="Hali to'lov qilinmagan"
              columns={[
                { key: 'date', header: 'Sana', render: (p) => fmtDate(p.date) },
                { key: 'amount', header: 'Summa', align: 'right', render: (p) => fmtMoney(p.amount) },
                { key: 'note', header: 'Izoh' },
              ]}
            />
          </div>

          {sale.debt > 0 && (
            <form onSubmit={submit} className="preview" style={{ padding: 14 }}>
              <b>Qarz to'lovi qabul qilish</b>
              <div className="form-grid" style={{ marginTop: 10 }}>
                <Field label="Summa (so'm) *" hint={`Qarz: ${fmtMoney(sale.debt)}`}>
                  <input type="number" step="0.01" min="0.01" max={sale.debt} required value={pay.amount} onChange={(e) => setPay({ ...pay, amount: e.target.value })} />
                </Field>
                <DateField label="Sana *" value={pay.date} onChange={(v) => setPay({ ...pay, date: v })} />
                <Field label="Izoh" className="full"><input value={pay.note} onChange={(e) => setPay({ ...pay, note: e.target.value })} /></Field>
              </div>
              <div className="row gap" style={{ marginTop: 10 }}>
                <Button type="button" variant="secondary" onClick={() => setPay({ ...pay, amount: String(sale.debt) })}>Butun qarz</Button>
                <Button type="submit" variant="success" loading={busy}>To'lovni qabul qilish</Button>
              </div>
            </form>
          )}
        </>
      )}
    </Modal>
  );
}

const emptyLine = () => ({ product_id: '', quantity: '', unit_price: '' });

function SaleForm({ onClose, onSaved }) {
  const toast = useToast();
  const { data: customers } = useFetch('/customers');
  const { data: products } = useFetch('/products');
  const [head, setHead] = useState({ customer_id: '', date: today(), payment_type: 'full', paid_amount: '', note: '' });
  const [lines, setLines] = useState([emptyLine()]);
  const [saving, setSaving] = useState(false);

  const productMap = useMemo(() => Object.fromEntries((products || []).map((p) => [String(p.id), p])), [products]);
  const update = (i, patch) => setLines(lines.map((l, idx) => (idx === i ? { ...l, ...patch } : l)));

  const total = lines.reduce((s, l) => s + (Number(l.quantity) || 0) * (Number(l.unit_price) || 0), 0);
  const filled = lines.filter((l) => l.product_id && Number(l.quantity) > 0);
  const paid = head.payment_type === 'full' ? total : head.payment_type === 'partial' ? Number(head.paid_amount) || 0 : 0;
  const debt = Math.max(total - paid, 0);
  const partialOk = head.payment_type !== 'partial' || (paid > 0 && paid < total);

  const save = async (e) => {
    e.preventDefault();
    setSaving(true);
    try {
      await API.post('/sales', {
        customer_id: Number(head.customer_id),
        date: head.date,
        payment_type: head.payment_type,
        paid_amount: head.payment_type === 'partial' ? Number(head.paid_amount) : null,
        note: head.note.trim() || null,
        items: filled.map((l) => ({ product_id: Number(l.product_id), quantity: Number(l.quantity), unit_price: Number(l.unit_price || 0) })),
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
          <Button type="submit" form="sale-form" loading={saving} disabled={!filled.length || !partialOk}>Saqlash</Button>
        </>
      }
    >
      <form id="sale-form" onSubmit={save}>
        <div className="form-grid three" style={{ gridTemplateColumns: '2fr 1fr 1fr' }}>
          <Field label="Kimga (mijoz) *">
            <Select required value={head.customer_id} onChange={(v) => setHead({ ...head, customer_id: v })} options={(customers || []).map((c) => ({ value: c.id, label: c.name }))} />
          </Field>
          <DateField label="Sana *" value={head.date} onChange={(v) => setHead({ ...head, date: v })} />
          <Field label="To'lov *">
            <select value={head.payment_type} onChange={(e) => setHead({ ...head, payment_type: e.target.value, paid_amount: '' })}>
              {Object.entries(PAYMENT_TYPES).map(([k, v]) => <option key={k} value={k}>{v}</option>)}
            </select>
          </Field>
        </div>

        <h3 style={{ margin: '18px 0 8px' }}>Mahsulotlar</h3>
        <div className="lines">
          {lines.map((l, i) => (
            <div className="line sale" key={i}>
              <Select
                value={l.product_id}
                onChange={(v) => update(i, { product_id: v, unit_price: productMap[v]?.price ? String(productMap[v].price) : l.unit_price })}
                options={(products || []).map((p) => ({ value: p.id, label: `${p.name} (${p.unit})` }))}
                placeholder="Mahsulot"
              />
              <input type="number" step="any" min="0" placeholder="Miqdor" value={l.quantity} onChange={(e) => update(i, { quantity: e.target.value })} />
              <input type="number" step="0.01" min="0" placeholder="Narxi" value={l.unit_price} onChange={(e) => update(i, { unit_price: e.target.value })} />
              <div className="r num"><b>{fmtMoney((Number(l.quantity) || 0) * (Number(l.unit_price) || 0))}</b></div>
              <Button variant="danger" size="sm" type="button" disabled={lines.length === 1} onClick={() => setLines(lines.filter((_, idx) => idx !== i))}>×</Button>
            </div>
          ))}
          <div><Button variant="secondary" size="sm" type="button" onClick={() => setLines([...lines, emptyLine()])}>+ Qator qo'shish</Button></div>
        </div>

        <div className="total-bar"><span>Jami summa</span><span>{fmtMoney(total)}</span></div>

        {head.payment_type === 'partial' && (
          <Field label="Hozir qancha to'ladi (so'm) *" className="mt" hint="Qolgani qarz bo'lib yoziladi. Keyin yana bersa, qarzdan ayrib boriladi.">
            <input type="number" step="0.01" min="0.01" required value={head.paid_amount} onChange={(e) => setHead({ ...head, paid_amount: e.target.value })} />
          </Field>
        )}
        {head.payment_type !== 'full' && total > 0 && (
          <div className={`alert ${partialOk ? 'warn' : 'error'}`} style={{ marginTop: 12 }}>
            {partialOk
              ? <>To'lanadi: <b>{fmtMoney(paid)}</b> · Qarz bo'ladi: <b>{fmtMoney(debt)}</b></>
              : "Qisman to'lov 0 dan katta va jami summadan kam bo'lishi kerak"}
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
  const paid = (data || []).reduce((s, r) => s + r.paid_amount, 0);
  const debt = (data || []).reduce((s, r) => s + r.debt, 0);

  return (
    <>
      <PageHeader
        title="Sotuvlar"
        subtitle="Nima, qancha, kimga va qachon sotilgani. To'lov: to'liq, qisman yoki nasiya."
        actions={<Button onClick={() => setCreating(true)}>+ Yangi sotuv</Button>}
      />
      <Card flush>
        <div className="filters">
          <DateRange from={filters.from} to={filters.to} onChange={({ from, to }) => setFilters({ ...filters, from, to })} />
          <Select value={filters.customer_id} onChange={(v) => setFilters({ ...filters, customer_id: v })} options={(customers || []).map((c) => ({ value: c.id, label: c.name }))} placeholder="Barcha mijozlar" />
          <Select value={filters.status} onChange={(v) => setFilters({ ...filters, status: v })} options={Object.entries(SALE_STATUS).map(([k, [l]]) => ({ value: k, label: l }))} placeholder="Barcha holatlar" />
          <span className="grow" />
          <span className="muted">Jami: <b>{fmtMoney(total)}</b> · To'langan: <b>{fmtMoney(paid)}</b> · Qarz: <b className={debt > 0 ? 'neg' : ''}>{fmtMoney(debt)}</b></span>
        </div>
        <ErrorBox message={error} />
        {loading ? <Spinner /> : (
          <Table
            rows={data}
            empty="Tanlangan davrda sotuv yo'q"
            onRowClick={(r) => setViewId(r.id)}
            columns={[
              { key: 'date', header: 'Sana', render: (r) => fmtDate(r.date) },
              {
                key: 'customer_name', header: 'Kimga / mahsulot (nechta)',
                render: (r) => (
                  <>
                    <b>{r.customer_name}</b>
                    <div className="muted" style={{ fontSize: 12 }}>{r.items.map((i) => `${i.product_name} × ${fmtNum(i.quantity)} ${i.unit}`).join(', ')}</div>
                  </>
                ),
              },
              {
                key: 'total_amount', header: 'Summa', align: 'right',
                render: (r) => (
                  <>
                    {fmtMoney(r.total_amount)}
                    {r.debt > 0 && <div className="neg" style={{ fontSize: 12 }}>qarz {fmtMoney(r.debt)}</div>}
                  </>
                ),
              },
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
