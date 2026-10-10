import { useState } from 'react';
import { Bar, BarChart, CartesianGrid, Legend, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts';
import { Card, DateRange, ErrorBox, PageHeader, Spinner, StatCard, Table } from '../components/ui.jsx';
import { useFetch } from '../hooks/useFetch';
import { daysAgo, fmtDate, fmtMoney, fmtNum, monthStart, today } from '../utils';

const PRESETS = [
  { label: '7 kun', from: () => daysAgo(6) },
  { label: '30 kun', from: () => daysAgo(29) },
  { label: 'Joriy oy', from: monthStart },
];

const shortMoney = (v) => (Math.abs(v) >= 1e6 ? `${(v / 1e6).toFixed(1)}M` : Math.abs(v) >= 1e3 ? `${Math.round(v / 1e3)}k` : v);

export default function Dashboard() {
  const [range, setRange] = useState({ from: monthStart(), to: today() });
  const { data, loading, error } = useFetch('/reports/summary', { date_from: range.from, date_to: range.to });

  return (
    <>
      <PageHeader
        title="Boshqaruv paneli"
        subtitle="Zavod faoliyati bo'yicha asosiy ko'rsatkichlar"
        actions={
          <>
            {PRESETS.map((p) => (
              <button key={p.label} className="btn secondary sm" onClick={() => setRange({ from: p.from(), to: today() })}>{p.label}</button>
            ))}
            <DateRange from={range.from} to={range.to} onChange={setRange} />
          </>
        }
      />
      <ErrorBox message={error} />
      {loading || !data ? <Spinner /> : (
        <>
          <div className="grid cols-4">
            <StatCard label="Ishlab chiqarildi" value={fmtNum(data.production_total)} hint="dona/birlik" />
            <StatCard label="Sotuv" value={fmtMoney(data.sales_total)} tone="green" hint={`${data.sales_count} ta sotuv`} />
            <StatCard label="Xarajatlar" value={fmtMoney(data.expenses_total)} tone="amber" />
            <StatCard label="Xomashyo xaridi" value={fmtMoney(data.purchases_total)} tone="amber" hint="narxi kiritilgan kirimlar" />
            <StatCard label="Sof natija" value={fmtMoney(data.net_result)} tone={data.net_result >= 0 ? 'green' : 'red'} hint="Sotuv − xarajat − xomashyo xaridi" />
            <StatCard label="Tushgan to'lovlar" value={fmtMoney(data.payments_total)} tone="green" hint="shu davrda qabul qilingan" />
            <StatCard label="Mijozlar qarzi" value={fmtMoney(data.receivable_total)} tone={data.receivable_total > 0 ? 'red' : 'green'} hint={`${data.debtors_count} ta qarzdor, butun vaqt bo'yicha`} />
          </div>

          <div className="grid cols-2 mt">
            <Card title="Sotuv va xarajatlar (kunlik)">
              <ResponsiveContainer width="100%" height={260}>
                <BarChart data={data.daily}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#e5e7eb" />
                  <XAxis dataKey="date" tickFormatter={(d) => d.slice(5)} fontSize={12} />
                  <YAxis tickFormatter={shortMoney} fontSize={12} width={48} />
                  <Tooltip formatter={(v) => fmtMoney(v)} labelFormatter={fmtDate} />
                  <Legend />
                  <Bar dataKey="sales" name="Sotuv" fill="#16a34a" radius={[4, 4, 0, 0]} />
                  <Bar dataKey="expenses" name="Xarajat" fill="#d97706" radius={[4, 4, 0, 0]} />
                </BarChart>
              </ResponsiveContainer>
            </Card>
            <Card title="Ishlab chiqarish (kunlik)">
              <ResponsiveContainer width="100%" height={260}>
                <BarChart data={data.daily}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#e5e7eb" />
                  <XAxis dataKey="date" tickFormatter={(d) => d.slice(5)} fontSize={12} />
                  <YAxis fontSize={12} width={48} />
                  <Tooltip formatter={(v) => fmtNum(v)} labelFormatter={fmtDate} />
                  <Bar dataKey="production" name="Ishlab chiqarildi" fill="#2563eb" radius={[4, 4, 0, 0]} />
                </BarChart>
              </ResponsiveContainer>
            </Card>
          </div>

          <div className="grid cols-2 mt">
            <Card title="Top mahsulotlar (tushum bo'yicha)" flush>
              <Table
                rows={data.top_products}
                rowKey="product_id"
                empty="Sotuvlar yo'q"
                columns={[
                  { key: 'name', header: 'Mahsulot', render: (r) => <b>{r.name}</b> },
                  { key: 'quantity', header: 'Miqdor', align: 'right', render: (r) => `${fmtNum(r.quantity)} ${r.unit}` },
                  { key: 'revenue', header: 'Tushum', align: 'right', render: (r) => fmtMoney(r.revenue) },
                ]}
              />
            </Card>
            <Card title="Hamkorlar bo'yicha ishlab chiqarish" flush>
              <Table
                rows={data.by_partner}
                rowKey="partner_id"
                empty="Ma'lumot yo'q"
                columns={[
                  { key: 'partner_name', header: 'Hamkor', render: (r) => <b>{r.partner_name}</b> },
                  { key: 'production', header: 'Ishlab chiqarilgan', align: 'right', render: (r) => fmtNum(r.production) },
                ]}
              />
            </Card>
          </div>

          <Card title="Xarajatlar kategoriyalar bo'yicha" className="mt">
            {data.expense_by_category.length === 0 ? <p className="muted">Xarajatlar yo'q</p> : (
              <div className="bar-list">
                {data.expense_by_category.map((c) => (
                  <div key={c.category}>
                    <span>{c.category}</span>
                    <b>{fmtMoney(c.amount)}</b>
                    <div className="bar"><span style={{ width: `${(c.amount / data.expenses_total) * 100}%` }} /></div>
                  </div>
                ))}
              </div>
            )}
          </Card>
        </>
      )}
    </>
  );
}
