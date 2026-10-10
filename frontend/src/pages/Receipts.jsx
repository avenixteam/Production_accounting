import { useState } from 'react';
import API, { errMsg } from '../api';
import { useToast } from '../components/Toast.jsx';
import { Button, Card, DateField, DateRange, ErrorBox, Field, Modal, PageHeader, Select, Spinner, Table } from '../components/ui.jsx';
import { useFetch } from '../hooks/useFetch';
import { fmtDate, fmtMoney, fmtNum, monthStart, rmLabel, today, widenRange } from '../utils';

const empty = () => ({
  partner_id: '', raw_material_id: '', quantity: '', unit_price: '', supplier_name: '',
  payment_type: '', date: today(), note: '',
});

export default function Receipts() {
  const toast = useToast();
  const [filters, setFilters] = useState({ from: monthStart(), to: today(), partner_id: '', raw_material_id: '' });
  const { data, loading, error, reload } = useFetch('/receipts', {
    date_from: filters.from, date_to: filters.to, partner_id: filters.partner_id, raw_material_id: filters.raw_material_id,
  });
  const { data: partners } = useFetch('/partners');
  const { data: materials } = useFetch('/raw-materials');
  const [form, setForm] = useState(null);
  const [saving, setSaving] = useState(false);

  const pOpts = (partners || []).map((p) => ({ value: p.id, label: p.name }));
  const mOpts = (materials || []).map((m) => ({ value: m.id, label: `${rmLabel(m)} (${m.unit})` }));
  const selectedMaterial = (materials || []).find((m) => String(m.id) === String(form?.raw_material_id));

  const save = async (e) => {
    e.preventDefault();
    setSaving(true);
    try {
      await API.post('/receipts', {
        partner_id: Number(form.partner_id),
        raw_material_id: Number(form.raw_material_id),
        quantity: Number(form.quantity),
        unit_price: form.unit_price === '' ? null : Number(form.unit_price),
        supplier_name: form.supplier_name.trim() || null,
        payment_type: form.payment_type.trim() || null,
        date: form.date,
        note: form.note.trim() || null,
      });
      toast.success('Kirim saqlandi');
      setFilters((f) => widenRange(f, form.date));
      setForm(null);
      reload();
    } catch (err) {
      toast.error(errMsg(err));
    } finally {
      setSaving(false);
    }
  };

  const remove = async (r) => {
    if (!window.confirm(`Kirim #${r.id} o'chirilsinmi? Ombor qoldig'i kamayadi.`)) return;
    try {
      await API.delete(`/receipts/${r.id}`);
      toast.success("Kirim o'chirildi");
      reload();
    } catch (err) {
      toast.error(errMsg(err));
    }
  };

  const totalSum = (data || []).reduce((s, r) => s + (r.total || 0), 0);

  const columns = [
    { key: 'date', header: 'Sana', render: (r) => fmtDate(r.date) },
    { key: 'partner_name', header: 'Hamkor' },
    { key: 'brand', header: 'Xomashyo', render: (r) => <b>{r.brand}</b> },
    { key: 'quantity', header: 'Miqdor', align: 'right', render: (r) => `${fmtNum(r.quantity)} ${r.unit}` },
    { key: 'unit_price', header: 'Narxi', align: 'right', render: (r) => (r.unit_price != null ? fmtMoney(r.unit_price) : '—') },
    { key: 'total', header: 'Summa', align: 'right', render: (r) => (r.total != null ? fmtMoney(r.total) : '—') },
    { key: 'supplier_name', header: "Yetkazib beruvchi" },
    { key: 'payment_type', header: "To'lov turi" },
    { key: 'a', header: '', align: 'right', render: (r) => <Button variant="danger" size="sm" onClick={() => remove(r)}>O'chirish</Button> },
  ];

  return (
    <>
      <PageHeader
        title="Xomashyo kirimi"
        subtitle="Hamkorlar nomiga kelgan xomashyo. Kirim ombor qoldig'iga avtomatik qo'shiladi."
        actions={<Button onClick={() => setForm(empty())}>+ Yangi kirim</Button>}
      />
      <Card flush>
        <div className="filters">
          <DateRange from={filters.from} to={filters.to} onChange={({ from, to }) => setFilters({ ...filters, from, to })} />
          <Select value={filters.partner_id} onChange={(v) => setFilters({ ...filters, partner_id: v })} options={pOpts} placeholder="Barcha hamkorlar" />
          <Select value={filters.raw_material_id} onChange={(v) => setFilters({ ...filters, raw_material_id: v })} options={mOpts} placeholder="Barcha xomashyolar" />
          <span className="grow" />
          <span className="muted">Jami xarid: <b>{fmtMoney(totalSum)}</b></span>
        </div>
        <ErrorBox message={error} />
        {loading ? <Spinner /> : <Table columns={columns} rows={data} empty="Tanlangan davrda kirim yo'q" />}
      </Card>

      {form && (
        <Modal
          title="Yangi xomashyo kirimi"
          onClose={() => setForm(null)}
          footer={
            <>
              <Button variant="secondary" onClick={() => setForm(null)}>Bekor qilish</Button>
              <Button type="submit" form="receipt-form" loading={saving}>Saqlash</Button>
            </>
          }
        >
          <form id="receipt-form" onSubmit={save} className="form-grid">
            <Field label="Hamkor *"><Select required value={form.partner_id} onChange={(v) => setForm({ ...form, partner_id: v })} options={pOpts} /></Field>
            <DateField label="Sana *" value={form.date} onChange={(v) => setForm({ ...form, date: v })} />
            <Field label="Xomashyo *" className="full"><Select required value={form.raw_material_id} onChange={(v) => setForm({ ...form, raw_material_id: v })} options={mOpts} /></Field>
            <Field label={`Miqdor * ${selectedMaterial ? `(${selectedMaterial.unit})` : ''}`}>
              <input type="number" step="any" min="0.001" required value={form.quantity} onChange={(e) => setForm({ ...form, quantity: e.target.value })} />
            </Field>
            <Field label="Birlik narxi (so'm)" hint="Xarid tannarxi hisobotlari uchun">
              <input type="number" step="0.01" min="0" value={form.unit_price} onChange={(e) => setForm({ ...form, unit_price: e.target.value })} />
            </Field>
            <Field label="Yetkazib beruvchi"><input value={form.supplier_name} onChange={(e) => setForm({ ...form, supplier_name: e.target.value })} /></Field>
            <Field label="To'lov turi"><input placeholder="naqd / o'tkazma / nasiya" value={form.payment_type} onChange={(e) => setForm({ ...form, payment_type: e.target.value })} /></Field>
            <Field label="Izoh" className="full"><input value={form.note} onChange={(e) => setForm({ ...form, note: e.target.value })} /></Field>
          </form>
        </Modal>
      )}
    </>
  );
}
