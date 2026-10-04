import { useState } from 'react';
import API, { errMsg } from '../api';
import { useToast } from '../components/Toast.jsx';
import { Button, Card, DateRange, ErrorBox, Field, Modal, PageHeader, Select, Spinner, StatCard, Table } from '../components/ui.jsx';
import { useFetch } from '../hooks/useFetch';
import { fmtDate, fmtMoney, monthStart, today } from '../utils';

const empty = () => ({ category: '', amount: '', date: today(), description: '' });

export default function Expenses() {
  const toast = useToast();
  const [filters, setFilters] = useState({ from: monthStart(), to: today(), category: '' });
  const params = { date_from: filters.from, date_to: filters.to };
  const { data, loading, error, reload } = useFetch('/expenses', { ...params, category: filters.category });
  const { data: summary, reload: reloadSummary } = useFetch('/expenses/summary', params);
  const { data: categories, reload: reloadCats } = useFetch('/expenses/categories');
  const [form, setForm] = useState(null);
  const [saving, setSaving] = useState(false);

  const refresh = () => { reload(); reloadSummary(); reloadCats(); };
  const total = (summary || []).reduce((s, x) => s + x.amount, 0);

  const save = async (e) => {
    e.preventDefault();
    setSaving(true);
    const payload = { category: form.category.trim(), amount: Number(form.amount), date: form.date, description: form.description.trim() || null };
    try {
      if (form.id) await API.put(`/expenses/${form.id}`, payload);
      else await API.post('/expenses', payload);
      toast.success('Saqlandi');
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

  return (
    <>
      <PageHeader title="Xarajatlar" subtitle="Zavodning operatsion xarajatlari (elektr, ish haqi, ijara va h.k.)" actions={<Button onClick={() => setForm(empty())}>+ Yangi xarajat</Button>} />
      <div className="grid cols-4" style={{ marginBottom: 16 }}>
        <StatCard label="Davr bo'yicha jami" value={fmtMoney(total)} tone="red" />
        {(summary || []).slice(0, 3).map((s) => <StatCard key={s.category} label={s.category} value={fmtMoney(s.amount)} hint={`${s.count} ta yozuv`} />)}
      </div>
      <Card flush>
        <div className="filters">
          <DateRange from={filters.from} to={filters.to} onChange={({ from, to }) => setFilters({ ...filters, from, to })} />
          <Select value={filters.category} onChange={(v) => setFilters({ ...filters, category: v })} options={(categories || []).map((c) => ({ value: c, label: c }))} placeholder="Barcha kategoriyalar" />
        </div>
        <ErrorBox message={error} />
        {loading ? <Spinner /> : (
          <Table
            rows={data}
            empty="Tanlangan davrda xarajat yo'q"
            columns={[
              { key: 'date', header: 'Sana', render: (r) => fmtDate(r.date) },
              { key: 'category', header: 'Kategoriya', render: (r) => <b>{r.category}</b> },
              { key: 'description', header: 'Izoh' },
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
            <Field label="Kategoriya *">
              <input list="exp-cats" required value={form.category} onChange={(e) => setForm({ ...form, category: e.target.value })} placeholder="Elektr, ish haqi, ijara..." />
              <datalist id="exp-cats">{(categories || []).map((c) => <option key={c} value={c} />)}</datalist>
            </Field>
            <Field label="Sana *"><input type="date" required value={form.date} onChange={(e) => setForm({ ...form, date: e.target.value })} /></Field>
            <Field label="Summa (so'm) *" className="full"><input type="number" step="0.01" min="0.01" required value={form.amount} onChange={(e) => setForm({ ...form, amount: e.target.value })} /></Field>
            <Field label="Izoh" className="full"><input value={form.description} onChange={(e) => setForm({ ...form, description: e.target.value })} /></Field>
          </form>
        </Modal>
      )}
    </>
  );
}
