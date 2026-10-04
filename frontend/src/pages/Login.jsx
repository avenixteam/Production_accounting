import { useState } from 'react';
import { errMsg } from '../api';
import { useAuth } from '../components/Auth.jsx';
import { Button, ErrorBox, Field } from '../components/ui.jsx';

export default function Login() {
  const { login } = useAuth();
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');

  const submit = async (e) => {
    e.preventDefault();
    setBusy(true);
    setError('');
    try {
      await login(username.trim(), password);
    } catch (err) {
      setError(errMsg(err));
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="login-wrap">
      <form className="card login-card" onSubmit={submit}>
        <div className="brand login-brand">
          <div className="brand-logo">🏭</div>
          <div>Zavod hisobi</div>
        </div>
        {error && <ErrorBox message={error} />}
        <Field label="Login">
          <input value={username} onChange={(e) => setUsername(e.target.value)} autoComplete="username" autoFocus required />
        </Field>
        <Field label="Parol">
          <input type="password" value={password} onChange={(e) => setPassword(e.target.value)} autoComplete="current-password" required />
        </Field>
        <Button type="submit" loading={busy}>Kirish</Button>
      </form>
    </div>
  );
}
