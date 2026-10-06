import { useState } from 'react';
import API, { errMsg } from '../api';
import { useFetch } from '../hooks/useFetch';
import { Badge, Button, Card, ErrorBox, Field, Modal, PageHeader, Spinner, Table } from '../components/ui.jsx';
import { useToast } from '../components/Toast.jsx';
import { useAuth } from '../components/Auth.jsx';

const EMPTY = { username: '', full_name: '', password: '', role: 'staff' };

export default function Users() {
  const toast = useToast();
  const { user: me } = useAuth();
  const { data, loading, error, reload } = useFetch('/auth/users');
  const [form, setForm] = useState(null);
  const [saving, setSaving] = useState(false);

  const create = async (e) => {
    e.preventDefault();
    setSaving(true);
    try {
      await API.post('/auth/users', { ...form, full_name: form.full_name.trim() || null });
      toast.success("Foydalanuvchi qo'shildi");
      setForm(null);
      reload();
    } catch (err) {
      toast.error(errMsg(err));
    } finally {
      setSaving(false);
    }
  };

  const update = async (u, patch, okMsg) => {
    try {
      await API.put(`/auth/users/${u.id}`, patch);
      toast.success(okMsg);
      reload();
    } catch (err) {
      toast.error(errMsg(err));
    }
  };

  const resetPassword = (u) => {
    const pw = window.prompt(`'${u.username}' uchun yangi parol (kamida 8 belgi):`);
    if (pw) update(u, { password: pw }, 'Parol yangilandi');
  };

  const remove = async (u) => {
    const role = u.role === 'admin' ? 'Admin' : 'Xodim';
    if (!window.confirm(`${role} "${u.username}" butunlay o'chirilsinmi? Bu qaytarilmaydi.`)) return;
    try {
      await API.delete(`/auth/users/${u.id}`);
      toast.success("Foydalanuvchi o'chirildi");
      reload();
    } catch (err) {
      toast.error(errMsg(err));
    }
  };

  const columns = [
    {
      key: 'username',
      header: 'Login',
      render: (u) => (
        <>
          <b>{u.username}</b>
          {u.full_name && <div className="muted" style={{ fontSize: 12 }}>{u.full_name}</div>}
        </>
      ),
    },
    {
      key: 'role',
      header: 'Holat',
      render: (u) => (
        <div className="stack" style={{ gap: 4, alignItems: 'flex-start' }}>
          <Badge tone={u.role === 'admin' ? 'blue' : 'gray'}>{u.role === 'admin' ? 'Admin' : 'Xodim'}</Badge>
          <Badge tone={u.active ? 'green' : 'red'}>{u.active ? 'Faol' : 'Bloklangan'}</Badge>
        </div>
      ),
    },
    {
      key: 'actions',
      header: '',
      align: 'right',
      render: (u) => (
        <div className="stack" style={{ gap: 6, alignItems: 'stretch', minWidth: 96, marginLeft: 'auto', width: 'max-content' }}>
          <Button variant="secondary" size="sm" onClick={() => resetPassword(u)}>Parol</Button>
          {u.id !== me?.id && (
            <>
              <Button
                variant={u.active ? 'danger' : 'secondary'}
                size="sm"
                onClick={() => update(u, { active: !u.active }, u.active ? 'Bloklandi' : 'Faollashtirildi')}
              >
                {u.active ? 'Bloklash' : 'Faollashtirish'}
              </Button>
              <Button variant="danger" size="sm" onClick={() => remove(u)}>O'chirish</Button>
            </>
          )}
        </div>
      ),
    },
  ];

  return (
    <>
      <PageHeader
        title="Foydalanuvchilar"
        subtitle="Admin hamma narsani qila oladi; xodim hujjatlarni bekor qila olmaydi. O'chirilgan foydalanuvchi qayta tiklanmaydi"
        actions={<Button onClick={() => setForm({ ...EMPTY })}>+ Foydalanuvchi</Button>}
      />
      {error && <ErrorBox message={error} />}
      <Card flush>{loading ? <Spinner /> : <Table columns={columns} rows={data} empty="Foydalanuvchi yo'q" />}</Card>

      {form && (
        <Modal
          title="Yangi foydalanuvchi"
          onClose={() => setForm(null)}
          footer={<Button type="submit" form="user-form" loading={saving}>Saqlash</Button>}
        >
          <form id="user-form" onSubmit={create} className="stack">
            <Field label="Login" hint="Lotin harf, raqam, _ . -">
              <input value={form.username} onChange={(e) => setForm({ ...form, username: e.target.value })} minLength={3} required />
            </Field>
            <Field label="Ism">
              <input value={form.full_name} onChange={(e) => setForm({ ...form, full_name: e.target.value })} />
            </Field>
            <Field label="Parol" hint="Kamida 8 belgi">
              <input type="password" value={form.password} onChange={(e) => setForm({ ...form, password: e.target.value })} minLength={8} required />
            </Field>
            <Field label="Rol">
              <select value={form.role} onChange={(e) => setForm({ ...form, role: e.target.value })}>
                <option value="staff">Xodim</option>
                <option value="admin">Admin</option>
              </select>
            </Field>
          </form>
        </Modal>
      )}
    </>
  );
}
