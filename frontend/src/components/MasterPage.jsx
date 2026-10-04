import { useEffect, useState } from 'react';
import API, { errMsg } from '../api';
import { useFetch } from '../hooks/useFetch';
import { Badge, Button, Card, ErrorBox, Field, Modal, PageHeader, Spinner, Table } from './ui.jsx';
import { useToast } from './Toast.jsx';

/**
 * Umumiy ma'lumotnoma sahifasi (ro'yxat + qidiruv + qo'shish/tahrirlash/faolsizlantirish).
 * fields: [{ name, label, type?, required?, placeholder?, step?, full? }]
 * columns: [{ key, header, render?, align? }]
 */
export default function MasterPage({ title, subtitle, endpoint, singular, fields, columns, rowActions, defaults = {} }) {
  const toast = useToast();
  const [search, setSearch] = useState('');
  const [showInactive, setShowInactive] = useState(false);
  const [debounced, setDebounced] = useState('');
  useEffect(() => {
    const t = setTimeout(() => setDebounced(search), 300); // har harfda emas, yozib bo'lgach qidiradi
    return () => clearTimeout(t);
  }, [search]);
  const { data, loading, error, reload } = useFetch(endpoint, { q: debounced, include_inactive: showInactive });
  const [editing, setEditing] = useState(null); // null | {} (yangi) | row
  const [form, setForm] = useState({});
  const [saving, setSaving] = useState(false);

  const openNew = () => {
    setForm({ ...Object.fromEntries(fields.map((f) => [f.name, ''])), ...defaults });
    setEditing({});
  };
  const openEdit = (row) => {
    setForm(Object.fromEntries(fields.map((f) => [f.name, row[f.name] ?? ''])));
    setEditing(row);
  };

  const submit = async (e) => {
    e.preventDefault();
    const payload = {};
    for (const f of fields) {
      const v = form[f.name];
      if (f.type === 'number') payload[f.name] = v === '' ? (f.required ? 0 : null) : Number(v);
      else payload[f.name] = typeof v === 'string' ? v.trim() || (f.required ? '' : null) : v;
    }
    setSaving(true);
    try {
      if (editing.id) await API.put(`${endpoint}/${editing.id}`, payload);
      else await API.post(endpoint, payload);
      toast.success(editing.id ? 'Saqlandi' : "Qo'shildi");
      setEditing(null);
      reload();
    } catch (err) {
      toast.error(errMsg(err));
    } finally {
      setSaving(false);
    }
  };

  const setActive = async (row, active) => {
    if (!active && !window.confirm(`"${row.name || row.brand}" faolsizlantirilsinmi? Tarixiy hujjatlar saqlanib qoladi.`)) return;
    try {
      if (active) await API.put(`${endpoint}/${row.id}`, { active: true });
      else await API.delete(`${endpoint}/${row.id}`);
      toast.success(active ? 'Faollashtirildi' : 'Faolsizlantirildi');
      reload();
    } catch (err) {
      toast.error(errMsg(err));
    }
  };

  const cols = [
    ...columns,
    {
      key: '_status', header: 'Holat',
      render: (r) => (r.active ? <Badge tone="green">Faol</Badge> : <Badge tone="gray">Nofaol</Badge>),
    },
    {
      key: '_actions', header: '', align: 'right',
      render: (r) => (
        <div className="row-actions">
          {rowActions?.(r, reload)}
          <Button variant="secondary" size="sm" onClick={() => openEdit(r)}>Tahrirlash</Button>
          {r.active
            ? <Button variant="danger" size="sm" onClick={() => setActive(r, false)}>O'chirish</Button>
            : <Button variant="secondary" size="sm" onClick={() => setActive(r, true)}>Faollashtirish</Button>}
        </div>
      ),
    },
  ];

  return (
    <>
      <PageHeader title={title} subtitle={subtitle} actions={<Button onClick={openNew}>+ Yangi {singular}</Button>} />
      <Card flush>
        <div className="filters">
          <input placeholder="Qidirish..." value={search} onChange={(e) => setSearch(e.target.value)} />
          <label className="check">
            <input type="checkbox" checked={showInactive} onChange={(e) => setShowInactive(e.target.checked)} />
            Nofaollarni ham ko'rsatish
          </label>
        </div>
        <ErrorBox message={error} />
        {loading ? <Spinner /> : <Table columns={cols} rows={data} empty={`${singular} hali qo'shilmagan`} />}
      </Card>

      {editing && (
        <Modal
          title={editing.id ? `${singular}ni tahrirlash` : `Yangi ${singular}`}
          onClose={() => setEditing(null)}
          footer={
            <>
              <Button variant="secondary" onClick={() => setEditing(null)}>Bekor qilish</Button>
              <Button type="submit" form="master-form" loading={saving}>Saqlash</Button>
            </>
          }
        >
          <form id="master-form" onSubmit={submit} className="form-grid">
            {fields.map((f) => (
              <Field key={f.name} label={f.label + (f.required ? ' *' : '')} className={f.full ? 'full' : ''}>
                <input
                  type={f.type || 'text'}
                  step={f.step}
                  min={f.type === 'number' ? 0 : undefined}
                  required={f.required}
                  placeholder={f.placeholder}
                  value={form[f.name] ?? ''}
                  onChange={(e) => setForm({ ...form, [f.name]: e.target.value })}
                />
              </Field>
            ))}
          </form>
        </Modal>
      )}
    </>
  );
}
