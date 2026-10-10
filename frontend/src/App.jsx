import { lazy } from 'react';
import { Navigate, Route, Routes } from 'react-router-dom';
import { useAuth } from './components/Auth.jsx';
import Layout from './components/Layout.jsx';
import { Spinner } from './components/ui.jsx';
import Login from './pages/Login.jsx';

// Har bir sahifa alohida fayl bo'lib, kerak bo'lganda yuklanadi (birinchi yuklanish tezroq).
const Dashboard = lazy(() => import('./pages/Dashboard.jsx'));
const Receipts = lazy(() => import('./pages/Receipts.jsx'));
const Production = lazy(() => import('./pages/Production.jsx'));
const Reports = lazy(() => import('./pages/Reports.jsx'));
const Sales = lazy(() => import('./pages/Sales.jsx'));
const Debts = lazy(() => import('./pages/Debts.jsx'));
const Expenses = lazy(() => import('./pages/Expenses.jsx'));
const Products = lazy(() => import('./pages/Products.jsx'));
const Users = lazy(() => import('./pages/Users.jsx'));
const Partners = lazy(() => import('./pages/Masters.jsx').then((m) => ({ default: m.Partners })));
const RawMaterials = lazy(() => import('./pages/Masters.jsx').then((m) => ({ default: m.RawMaterials })));
const Machines = lazy(() => import('./pages/Masters.jsx').then((m) => ({ default: m.Machines })));
const Customers = lazy(() => import('./pages/Masters.jsx').then((m) => ({ default: m.Customers })));

export default function App() {
  const { user, ready } = useAuth();
  if (!ready) return <Spinner />;
  if (!user) return <Login />;

  return (
    <Routes>
      <Route element={<Layout />}>
        <Route index element={<Dashboard />} />
        <Route path="receipts" element={<Receipts />} />
        <Route path="production" element={<Production />} />
        <Route path="sales" element={<Sales />} />
        <Route path="debts" element={<Debts />} />
        <Route path="expenses" element={<Expenses />} />
        <Route path="reports" element={<Reports />} />
        <Route path="products" element={<Products />} />
        <Route path="raw-materials" element={<RawMaterials />} />
        <Route path="partners" element={<Partners />} />
        <Route path="machines" element={<Machines />} />
        <Route path="customers" element={<Customers />} />
        {user.role === 'admin' && <Route path="users" element={<Users />} />}
        <Route path="*" element={<Navigate to="/" replace />} />
      </Route>
    </Routes>
  );
}
