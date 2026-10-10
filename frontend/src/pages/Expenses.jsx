import { useState } from 'react';
import API, { errMsg } from '../api';
import { useToast } from '../components/Toast.jsx';
import { Button, Card, DateField, DateRange, ErrorBox, Field, Modal, PageHeader, Select, Spinner, StatCard, Table } from '../components/ui.jsx';
import { useFetch } from '../hooks/useFetch';
import { fmtDate, fmtMoney, monthStart, today, widenRange } from '../utils';

const empty = (category = '') => ({ category, amount: '', date: today(), description: '' });

function CategoriesModal({ categories, onClose, onChanged }) {
  const toast = useToast();
  const [name, setName] = useState('');
  const [busy, setBusy] = useState(false);

  const run = async (fn, okMsg) => {
    setBusy(true);
    try {
      await fn();
      if (okMsg) toast.success(okMsg);
      onChanged();
      return true;
    } catch (err) {
      toast.error(errMsg(err));
      return false;
    } finally {
      setBusy(false);
    }
  };

  const add = (e) => {
    e.preventDefault();
    run(() => API.post('/expenses/categories', { name: name.trim() }), "Kategoriya qo'shildi").then((ok) => ok && setName(''));
  };
  const rename = (c) => {
    const v = window.prompt('Yangi nom:', c.name);
    if (v && v.trim() && v.trim() !== c.name) run(() => API.put(`/expenses/categories/${c.id}`, { name: v.trim() }), "Nomi o'zgartirildi");
  };
  const remove = (c) => {
    if (window.confirm(`"${c.name}" kategoriyasi o'chirilsinmi?`)) run(() => API.delete(`/expenses/categories/${c.id}`), "O'chirildi");
  };

  return (
    <Modal title="Xarajat kategoriyalari" onClose={onClose} footer={<Button variant="secondary" onClick={onClose}>Yopish</Button>}>
      <form onSubmit={add} className="row gap" style={{ marginBottom: 14 }}>
        <input required placeholder="Yangi kategoriya (masalan: Oshxona)" value={name} onChange={(e) => setName(e.target.value)} />
        <Button type="submit" loading={busy}>Qo'shish</Button>
      </form>
      <Table
        rows={categories || []}
        empty="Hali kategoriya yo'q. Yuqorida yarating."
        columns={[
          { key: 'name', header: 'Kategoriya', render: (c) => <b>{c.name}</b> },
          { key: 'count', header: 'Yozuvlar', align: 'right' },
          { key: 'total', header: 'Jami', align: 'right', render: (c) => fmtMoney(c.total) },
          {
            key: 'a', header: '', align: 'right',
            render: (c) => (
              <div className="row-actions">
                <Button variant="secondary" size="sm" onClick={() => rename(c)}>Nomi</Button>
                <Button variant="danger" size="sm" onClick={() => remove(c)}>O'chirish</Button>
              </div>
            ),
          },
        ]}
      />
    </Modal>
  );
}

export default function Expenses() {
  const toast = useToast();
  const [filters, setFilters] = useState({ from: monthStart(), to: today(), category: '' });
  const params = { date_from: filters.from, date_to: filters.to };
  const { data, loading, error, reload } = useFetch('/expenses', { ...params, category: filters.category });
  const { data: summary, reload: reloadSummary } = useFetch('/expenses/summary', params);
  const { data: categories, reload: reloadCats } = useFetch('/expenses/categories');
  const [form, setForm] = useState(null);
  const [catsOpen, setCatsOpen] = useState(false);
  const [saving, setSaving] = useState(false);

  const refresh = () => { reload(); reloadSummary(); reloadCats(); };
  const total = (summary || []).reduce((s, x) => s + x.amount, 0);

  const save = async (e) => {
    e.preventDefault();
    setSaving(true);
    const payload = { category: form.category, amount: Number(form.amount), date: form.date, description: form.description.trim() || null };
    try {
      if (form.id) await API.put(`/expenses/${form.id}`, payload);
      else await API.post('/expenses', payload);
      toast.success('Saqlandi');
      setFilters((f) => widenRange(f, form.date));
      setForm(null);
      refresh();
    } catch (err) {
      toast.error(errMsg(err));
    } finally {
      setSaving(false);
    }
  };

  const remove = async (r) => {
    if (!window.confirm("Xarajat o'chirilsinmi?")) return;
    try {
      await API.delete(`/expenses/${r.id}`);
      toast.success("O'chirildi");
      refresh();
    } catch (err) {
      toast.error(errMsg(err));
    }
  };

  const catOptions = (categories || []).map((c) => ({ value: c.name, label: c.name }));
  const noCats = categories && categories.length === 0;

  return (
    <>
      <PageHeader
        title="Xarajatlar"
        subtitle="Kategoriya yarating (masalan Oshxona), keyin shu kategoriya ichiga xarajat yozing (kartoshka — 30 000)"
        actions={
          <>
            <Button variant="secondary" onClick={() => setCatsOpen(true)}>Kategoriyalar</Button>
            <Button onClick={() => (noCats ? setCatsOpen(true) : setForm(empty(filters.category)))}>+ Yangi xarajat</Button>
          </>
        }
      />
      {noCats && <div className="alert warn" style={{ marginBottom: 16 }}>Avval "Kategoriyalar" tugmasi orqali kategoriya yarating (masalan: Oshxona, Elektr).</div>}
      <div className="grid cols-4" style={{ marginBottom: 16 }}>
        <StatCard label="Davr bo'yicha jami" value={fmtMoney(total)} tone="red" />
        {(summary || []).slice(0, 3).map((s) => <StatCard key={s.category} label={s.category} value={fmtMoney(s.amount)} hint={`${s.count} ta yozuv`} />)}
      </div>
      <Card flush>
        <div className="filters">
          <DateRange from={filters.from} to={filters.to} onChange={({ from, to }) => setFilters({ ...filters, from, to })} />
          <Select value={filters.category} onChange={(v) => setFilters({ ...filters, category: v })} options={catOptions} placeholder="Barcha kategoriyalar" />
        </div>
        <ErrorBox message={error} />
        {loading ? <Spinner /> : (
          <Table
            rows={data}
            empty="Tanlangan davrda xarajat yo'q"
            columns={[
              { key: 'date', header: 'Sana', render: (r) => fmtDate(r.date) },
              { key: 'category', header: 'Kategoriya', render: (r) => <b>{r.category}</b> },
              { key: 'description', header: 'Nima uchun' },
              { key: 'amount', header: 'Summa', align: 'right', render: (r) => fmtMoney(r.amount) },
              {
                key: 'a', header: '', align: 'right',
                render: (r) => (
                  <div className="row-actions">
                    <Button variant="secondary" size="sm" onClick={() => setForm({ ...r, amount: String(r.amount), description: r.description || '' })}>Tahrirlash</Button>
                    <Button variant="danger" size="sm" onClick={() => remove(r)}>O'chirish</Button>
                  </div>
                ),
              },
            ]}
          />
        )}
      </Card>

      {form && (
        <Modal
          title={form.id ? 'Xarajatni tahrirlash' : 'Yangi xarajat'}
          onClose={() => setForm(null)}
          footer={<><Button variant="secondary" onClick={() => setForm(null)}>Bekor qilish</Button><Button type="submit" form="exp-form" loading={saving}>Saqlash</Button></>}
        >
          <form id="exp-form" onSubmit={save} className="form-grid">
            <Field label="Kategoriya *"><Select required value={form.category} onChange={(v) => setForm({ ...form, category: v })} options={catOptions} /></Field>
            <DateField label="Sana *" value={form.date} onChange={(v) => setForm({ ...form, date: v })} />
            <Field label="Nima uchun" className="full"><input placeholder="Masalan: kartoshka" value={form.description} onChange={(e) => setForm({ ...form, description: e.target.value })} /></Field>
            <Field label="Summa (so'm) *" className="full"><input type="number" step="0.01" min="0.01" required value={form.amount} onChange={(e) => setForm({ ...form, amount: e.target.value })} /></Field>
          </form>
        </Modal>
      )}
      {catsOpen && <CategoriesModal categories={categories} onClose={() => setCatsOpen(false)} onChanged={refresh} />}
    </>
  );
}
