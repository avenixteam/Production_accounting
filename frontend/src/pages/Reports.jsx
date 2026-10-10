import { useMemo, useState } from 'react';
import { Link } from 'react-router-dom';
import { Card, ErrorBox, PageHeader, Spinner, StatCard, Table } from '../components/ui.jsx';
import { useFetch } from '../hooks/useFetch';
import { fmtDate, fmtMoney, fmtNum, toISO, today } from '../utils';

/** Joriy oy boshidan `back` oy orqaga: 1 oy = shu oy, 3 oy = oxirgi 3 oy (shu oy bilan). */
const fromMonths = (back) => {
  const d = new Date();
  return toISO(new Date(d.getFullYear(), d.getMonth() - (back - 1), 1));
};

const PERIODS = [
  { key: 'm1', label: 'Oylik', months: 1 },
  { key: 'm3', label: '3 oylik', months: 3 },
  { key: 'm6', label: '6 oylik', months: 6 },
  { key: 'y1', label: 'Yillik', months: 12 },
];

const MONTHS = ['yanvar', 'fevral', 'mart', 'aprel', 'may', 'iyun', 'iyul', 'avgust', 'sentabr', 'oktabr', 'noyabr', 'dekabr'];
const monthLabel = (ym) => { const [y, m] = ym.split('-'); return `${MONTHS[Number(m) - 1]} ${y}`; };

export default function Reports() {
  const [period, setPeriod] = useState('m1');
  const months = PERIODS.find((p) => p.key === period).months;
  const from = useMemo(() => fromMonths(months), [months]);
  const { data, loading, error } = useFetch('/reports/summary', { date_from: from, date_to: today() });
  const { data: debts } = useFetch('/sales/debts');

  const sum = (k) => (data?.monthly || []).reduce((s, r) => s + r[k], 0);

  return (
    <>
      <PageHeader
        title="Hisobotlar"
        subtitle={`${fmtDate(from)} — ${fmtDate(today())}`}
        actions={PERIODS.map((p) => (
          <button key={p.key} className={`btn ${period === p.key ? '' : 'secondary'} sm`} onClick={() => setPeriod(p.key)}>{p.label}</button>
        ))}
      />
      <ErrorBox message={error} />
      {loading || !data ? <Spinner /> : (
        <>
          <div className="grid cols-4">
            <StatCard label="Sotuv" value={fmtMoney(data.sales_total)} tone="green" hint={`${data.sales_count} ta sotuv`} />
            <StatCard label="Tushgan to'lovlar" value={fmtMoney(data.payments_total)} tone="green" />
            <StatCard label="Xarajatlar" value={fmtMoney(data.expenses_total)} tone="amber" />
            <StatCard label="Xomashyo xaridi" value={fmtMoney(data.purchases_total)} tone="amber" />
            <StatCard label="Sof natija" value={fmtMoney(data.net_result)} tone={data.net_result >= 0 ? 'green' : 'red'} hint="Sotuv − xarajat − xomashyo xaridi" />
            <StatCard label="Ishlab chiqarildi" value={fmtNum(data.production_total)} />
          </div>

          <Card title="Oylar bo'yicha" flush className="mt">
            <Table
              rows={data.monthly}
              rowKey="month"
              columns={[
                {
                  key: 'month', header: 'Oy',
                  render: (r) => (
                    <>
                      <b>{monthLabel(r.month)}</b>
                      <div className="muted" style={{ fontSize: 12 }}>ishlab chiqarildi: {fmtNum(r.production)}</div>
                    </>
                  ),
                },
                {
                  key: 'sales', header: 'Sotuv', align: 'right',
                  render: (r) => (
                    <>
                      {fmtMoney(r.sales)}
                      <div className="muted" style={{ fontSize: 12 }}>to'langan: {fmtMoney(r.payments)}</div>
                    </>
                  ),
                },
                {
                  key: 'expenses', header: 'Xarajat', align: 'right',
                  render: (r) => (
                    <>
                      {fmtMoney(r.expenses)}
                      <div className="muted" style={{ fontSize: 12 }}>xomashyo: {fmtMoney(r.purchases)}</div>
                    </>
                  ),
                },
                { key: 'net', header: 'Natija', align: 'right', render: (r) => <b className={r.net < 0 ? 'neg' : ''}>{fmtMoney(r.net)}</b> },
              ]}
            />
            {data.monthly.length > 1 && (
              <div className="total-bar" style={{ borderRadius: 0, marginTop: 0, fontSize: 14 }}>
                <span>Jami ({data.monthly.length} oy)</span>
                <span>Sotuv {fmtMoney(sum('sales'))} · Xarajat {fmtMoney(sum('expenses'))} · Natija {fmtMoney(sum('net'))}</span>
              </div>
            )}
          </Card>

          <div className="grid cols-2 mt">
            <Card title="Xarajatlar kategoriyalar bo'yicha">
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
            <Card title="Top mahsulotlar (tushum bo'yicha)" flush>
              <Table
                rows={data.top_products}
                rowKey="product_id"
                empty="Sotuvlar yo'q"
                columns={[
                  {
                    key: 'name', header: 'Mahsulot',
                    render: (r) => (
                      <>
                        <b>{r.name}</b>
                        <div className="muted" style={{ fontSize: 12 }}>{fmtNum(r.quantity)} {r.unit}</div>
                      </>
                    ),
                  },
                  { key: 'revenue', header: 'Tushum', align: 'right', render: (r) => fmtMoney(r.revenue) },
                ]}
              />
            </Card>
          </div>
        </>
      )}

      <Card
        title="Qarzdorlar (hozirgi holat)"
        actions={<Link to="/debts">To'lov qabul qilish →</Link>}
        flush
        className="mt"
      >
        <Table
          rows={debts || []}
          rowKey="customer_id"
          empty="Qarzdorlar yo'q 🎉"
          columns={[
            {
              key: 'customer_name', header: 'Mijoz',
              render: (d) => (
                <>
                  <b>{d.customer_name}</b>
                  <div className="muted" style={{ fontSize: 12 }}>
                    {d.phone ? `${d.phone} · ` : ''}{d.sales.length} ta sotuv, eng eskisi {fmtDate(d.oldest_date)}
                  </div>
                </>
              ),
            },
            { key: 'debt', header: 'Qarz', align: 'right', render: (d) => <b className="neg">{fmtMoney(d.debt)}</b> },
          ]}
        />
        {debts?.length > 0 && (
          <div className="total-bar" style={{ borderRadius: 0, marginTop: 0, fontSize: 14 }}>
            <span>Jami qarz</span><span>{fmtMoney(debts.reduce((s, d) => s + d.debt, 0))}</span>
          </div>
        )}
      </Card>
    </>
  );
}
