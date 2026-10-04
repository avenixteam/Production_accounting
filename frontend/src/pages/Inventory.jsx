import { useState } from 'react';
import API, { errMsg } from '../api';
import { useToast } from '../components/Toast.jsx';
import { Badge, Button, Card, ErrorBox, Field, Modal, PageHeader, Select, Spinner, Table } from '../components/ui.jsx';
import { useFetch } from '../hooks/useFetch';
import { MOVEMENT_TYPES, fmtDate, fmtMoney, fmtNum, today } from '../utils';

function AdjustModal({ kind, row, onClose, onSaved }) {
  const toast = useToast();
  const [form, setForm] = useState({ quantity: '', date: today(), note: '' });
  const [saving, setSaving] = useState(false);
  const isRaw = kind === 'raw';
  const label = isRaw ? row.brand : row.product_name;

  const save = async (e) => {
    e.preventDefault();
    setSaving(true);
    try {
      await API.post(isRaw ? '/inventory/raw-materials/adjust' : '/inventory/finished-products/adjust', {
        partner_id: row.partner_id,
        [isRaw ? 'raw_material_id' : 'product_id']: isRaw ? row.raw_material_id : row.product_id,
        quantity: Number(form.quantity),
        date: form.date,
        note: form.note.trim() || null,
      });
      toast.success('Qoldiq tuzatildi');
      onSaved();
    } catch (err) {
      toast.error(errMsg(err));
    } finally {
      setSaving(false);
    }
  };

  return (
    <Modal
      title={`Qoldiqni tuzatish: ${label}`}
      onClose={onClose}
      footer={
        <>
          <Button variant="secondary" onClick={onClose}>Bekor qilish</Button>
          <Button type="submit" form="adj-form" loading={saving}>Saqlash</Button>
        </>
      }
    >
      <p className="muted" style={{ marginBottom: 12 }}>
        {row.partner_name} · hozirgi qoldiq: <b>{fmtNum(row.balance)} {row.unit}</b>. Inventarizatsiya, brak yoki yo'qotish uchun.
        Kamaytirish uchun manfiy son kiriting (masalan, -5).
      </p>
      <form id="adj-form" onSubmit={save} className="form-grid">
        <Field label="Miqdor (+/−) *"><input type="number" step="any" required value={form.quantity} onChange={(e) => setForm({ ...form, quantity: e.target.value })} /></Field>
        <Field label="Sana *"><input type="date" required value={form.date} onChange={(e) => setForm({ ...form, date: e.target.value })} /></Field>
        <Field label="Sabab / izoh" className="full"><input value={form.note} onChange={(e) => setForm({ ...form, note: e.target.value })} /></Field>
      </form>
    </Modal>
  );
}

function Balances({ kind, partnerId }) {
  const isRaw = kind === 'raw';
  const { data, loading, error, reload } = useFetch(isRaw ? '/inventory/raw-materials' : '/inventory/finished-products', { partner_id: partnerId });
  const [adjust, setAdjust] = useState(null);

  const columns = isRaw
    ? [
        { key: 'partner_name', header: 'Hamkor' },
        { key: 'brand', header: 'Xomashyo', render: (r) => <b>{r.brand}</b> },
        { key: 'name', header: 'Nomi' },
      ]
    : [
        { key: 'partner_name', header: 'Hamkor' },
        { key: 'product_name', header: 'Mahsulot', render: (r) => <b>{r.product_name}</b> },
        { key: 'code', header: 'Artikul' },
      ];
  columns.push({
    key: 'balance', header: 'Qoldiq', align: 'right',
    render: (r) => <b className={r.balance < 0 ? 'neg' : ''}>{fmtNum(r.balance)} {r.unit}</b>,
  });
  if (!isRaw) columns.push({ key: 'value', header: 'Qiymati (narx bo\'yicha)', align: 'right', render: (r) => fmtMoney(r.balance * r.price) });
  columns.push({
    key: 'a', header: '', align: 'right',
    render: (r) => <Button variant="secondary" size="sm" onClick={() => setAdjust(r)}>Tuzatish</Button>,
  });

  const rows = (data || []).map((r) => ({ ...r, id: `${r.partner_id}-${r.raw_material_id ?? r.product_id}` }));

  return (
    <>
      <ErrorBox message={error} />
      {loading ? <Spinner /> : <Table columns={columns} rows={rows} empty="Omborda qoldiq yo'q" />}
      {adjust && <AdjustModal kind={kind} row={adjust} onClose={() => setAdjust(null)} onSaved={() => { setAdjust(null); reload(); }} />}
    </>
  );
}

function Journal({ kind, partnerId }) {
  const isRaw = kind === 'raw';
  const { data, loading, error } = useFetch(isRaw ? '/inventory/raw-materials/movements' : '/inventory/finished-products/movements', { partner_id: partnerId, limit: 300 });

  const columns = [
    { key: 'date', header: 'Sana', render: (r) => fmtDate(r.date) },
    { key: 'partner_name', header: 'Hamkor' },
    isRaw
      ? { key: 'brand', header: 'Xomashyo', render: (r) => <b>{r.brand}</b> }
      : { key: 'product_name', header: 'Mahsulot', render: (r) => <b>{r.product_name}</b> },
    {
      key: 'movement_type', header: 'Turi',
      render: (r) => { const [l, t] = MOVEMENT_TYPES[r.movement_type] || [r.movement_type, 'gray']; return <Badge tone={t}>{l}</Badge>; },
    },
    { key: 'quantity', header: 'Miqdor', align: 'right', render: (r) => `${fmtNum(r.quantity)} ${r.unit}` },
    { key: 'note', header: 'Izoh' },
  ];
  return (
    <>
      <ErrorBox message={error} />
      {loading ? <Spinner /> : <Table columns={columns} rows={data} empty="Harakatlar yo'q" />}
    </>
  );
}

export default function Inventory() {
  const [tab, setTab] = useState('raw');
  const [journal, setJournal] = useState(false);
  const [partnerId, setPartnerId] = useState('');
  const { data: partners } = useFetch('/partners');

  return (
    <>
      <PageHeader title="Ombor" subtitle="Hamkorlar kesimida xomashyo va tayyor mahsulot qoldig'i" />
      <div className="tabs">
        <button className={`tab ${tab === 'raw' ? 'active' : ''}`} onClick={() => setTab('raw')}>Xomashyo</button>
        <button className={`tab ${tab === 'finished' ? 'active' : ''}`} onClick={() => setTab('finished')}>Tayyor mahsulot</button>
      </div>
      <Card flush>
        <div className="filters">
          <Select value={partnerId} onChange={setPartnerId} options={(partners || []).map((p) => ({ value: p.id, label: p.name }))} placeholder="Barcha hamkorlar" />
          <label className="check">
            <input type="checkbox" checked={journal} onChange={(e) => setJournal(e.target.checked)} />
            Harakatlar jurnalini ko'rsatish
          </label>
        </div>
        {journal ? <Journal key={tab} kind={tab} partnerId={partnerId} /> : <Balances key={tab} kind={tab} partnerId={partnerId} />}
      </Card>
    </>
  );
}
