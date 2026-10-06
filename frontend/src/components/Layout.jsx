import { Suspense, useEffect, useState } from 'react';
import { NavLink, Outlet, useLocation } from 'react-router-dom';
import { useAuth } from './Auth.jsx';
import ChangePassword from './ChangePassword.jsx';
import { Spinner } from './ui.jsx';

const NAV = [
  { title: 'Asosiy', items: [{ to: '/', label: 'Boshqaruv paneli', icon: '📊' }] },
  {
    title: 'Ishlab chiqarish',
    items: [
      { to: '/receipts', label: 'Xomashyo kirimi', icon: '📥' },
      { to: '/production', label: 'Ishlab chiqarish', icon: '🏭' },
      { to: '/inventory', label: 'Ombor', icon: '📦' },
    ],
  },
  {
    title: 'Savdo',
    items: [
      { to: '/sales', label: 'Sotuvlar', icon: '🧾' },
      { to: '/debts', label: 'Qarzdorlik', icon: '💳' },
    ],
  },
  { title: 'Moliya', items: [{ to: '/expenses', label: 'Xarajatlar', icon: '💸' }] },
  {
    title: "Ma'lumotnomalar",
    items: [
      { to: '/products', label: 'Mahsulotlar', icon: '🧱' },
      { to: '/raw-materials', label: 'Xomashyolar', icon: '🧪' },
      { to: '/partners', label: 'Hamkorlar', icon: '🤝' },
      { to: '/machines', label: 'Stanoklar', icon: '⚙️' },
      { to: '/customers', label: 'Mijozlar', icon: '👥' },
    ],
  },
];

const ADMIN_NAV = {
  title: 'Tizim',
  items: [{ to: '/users', label: 'Foydalanuvchilar', icon: '🔐' }],
};

export default function Layout() {
  const [open, setOpen] = useState(false);
  const [pwOpen, setPwOpen] = useState(false);
  const { user, logout } = useAuth();
  const location = useLocation();
  const [lastPath, setLastPath] = useState(location.pathname);
  if (lastPath !== location.pathname) {
    setLastPath(location.pathname);
    setOpen(false);
  }

  // Menyu ochiq: Escape bilan yopiladi, orqadagi sahifa aylanmaydi
  useEffect(() => {
    if (!open) return undefined;
    const onKey = (e) => e.key === 'Escape' && setOpen(false);
    document.addEventListener('keydown', onKey);
    document.body.classList.add('no-scroll');
    return () => {
      document.removeEventListener('keydown', onKey);
      document.body.classList.remove('no-scroll');
    };
  }, [open]);

  return (
    <div className="shell">
      {open && <div className="backdrop" onClick={() => setOpen(false)} aria-hidden="true" />}
      <aside className={`sidebar ${open ? 'open' : ''}`}>
        <div className="brand">
          <div className="brand-logo">🏭</div>
          <div className="grow">Zavod hisobi</div>
          <button className="sidebar-close" onClick={() => setOpen(false)} aria-label="Menyuni yopish">×</button>
        </div>
        {(user?.role === 'admin' ? [...NAV, ADMIN_NAV] : NAV).map((g) => (
          <div className="nav-group" key={g.title}>
            <div className="nav-title">{g.title}</div>
            {g.items.map((i) => (
              <NavLink key={i.to} to={i.to} end={i.to === '/'} className={({ isActive }) => `nav-link ${isActive ? 'active' : ''}`}>
                <span>{i.icon}</span>
                {i.label}
              </NavLink>
            ))}
          </div>
        ))}
        <div className="sidebar-user">
          <div className="sidebar-user-name">{user?.full_name || user?.username}</div>
          <div className="row gap">
            <button className="link-btn" onClick={() => setPwOpen(true)}>Parol</button>
            <button className="link-btn" onClick={logout}>Chiqish</button>
          </div>
        </div>
      </aside>
      <main className="main">
        <div className="topbar-mobile">
          <button className="btn secondary sm" onClick={() => setOpen(true)} aria-expanded={open}>☰ Menyu</button>
          <span>Zavod hisobi</span>
        </div>
        <Suspense fallback={<Spinner />}>
          <Outlet />
        </Suspense>
        {pwOpen && <ChangePassword onClose={() => setPwOpen(false)} />}
      </main>
    </div>
  );
}
