import { useState } from 'react';
import API, { errMsg } from '../api';
import { Button, Field, Modal } from './ui.jsx';
import { useToast } from './Toast.jsx';

export default function ChangePassword({ onClose }) {
  const toast = useToast();
  const [oldPw, setOldPw] = useState('');
  const [newPw, setNewPw] = useState('');
  const [busy, setBusy] = useState(false);

  const submit = async (e) => {
    e.preventDefault();
    setBusy(true);
    try {
      await API.post('/auth/change-password', { old_password: oldPw, new_password: newPw });
      toast.success("Parol o'zgartirildi");
      onClose();
    } catch (err) {
      toast.error(errMsg(err));
    } finally {
      setBusy(false);
    }
  };

  return (
    <Modal
      title="Parolni o'zgartirish"
      onClose={onClose}
      footer={<Button type="submit" form="pw-form" loading={busy}>Saqlash</Button>}
    >
      <form id="pw-form" onSubmit={submit} className="stack">
        <Field label="Eski parol">
          <input type="password" value={oldPw} onChange={(e) => setOldPw(e.target.value)} autoComplete="current-password" required />
        </Field>
        <Field label="Yangi parol" hint="Kamida 8 belgi">
          <input type="password" value={newPw} onChange={(e) => setNewPw(e.target.value)} minLength={8} autoComplete="new-password" required />
        </Field>
      </form>
    </Modal>
  );
}
