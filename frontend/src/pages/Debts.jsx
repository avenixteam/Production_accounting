import { useState } from 'react';
import { Button, Card, ErrorBox, PageHeader, Spinner, StatCard, Table } from '../components/ui.jsx';
import { useFetch } from '../hooks/useFetch';
import { fmtDate, fmtMoney } from '../utils';
import { SaleDetailModal } from './Sales.jsx';

export default function Debts() {
  const { data, loading, error, reload } = useFetch('/sales/debts');
  const [saleId, setSaleId] = useState(null);

  const total = (data || []).reduce((s, d) => s + d.debt, 0);
  const overdue = (data || []).reduce((s, d) => s + d.overdue, 0);

  return (
    <>
      <PageHeader title="Qarzdorlik" subtitle="Muddatli to'lov bo'yicha mijozlar qarzi" />
      <div className="grid cols-4" style={{ marginBottom: 16 }}>
        <StatCard label="Jami qarz" value={fmtMoney(total)} tone="amber" hint={`${data?.length || 0} ta qarzdor mijoz`} />
        <StatCard label="Muddati o'tgan" value={fmtMoney(overdue)} tone={overdue > 0 ? 'red' : 'green'} />
      </div>
      <Card flush>
        <ErrorBox message={error} />
        {loading ? <Spinner /> : (
          <Table
            rows={data}
            rowKey="customer_id"
            empty="Qarzdor mijozlar yo'q 🎉"
            columns={[
              { key: 'customer_name', header: 'Mijoz', render: (d) => <b>{d.customer_name}</b> },
              { key: 'phone', header: 'Telefon' },
              { key: 'debt', header: 'Qarz', align: 'right', render: (d) => fmtMoney(d.debt) },
              { key: 'overdue', header: "Muddati o'tgan", align: 'right', render: (d) => (d.overdue > 0 ? <span className="neg">{fmtMoney(d.overdue)}</span> : '—') },
              { key: 'next_due_date', header: 'Eng yaqin muddat', render: (d) => fmtDate(d.next_due_date) },
              {
                key: 'sales', header: 'Sotuvlar',
                render: (d) => (
                  <div className="row gap wrap">
                    {d.sale_ids.map((id) => (
                      <Button key={id} size="sm" variant="secondary" onClick={() => setSaleId(id)}>#{id}</Button>
                    ))}
                  </div>
                ),
              },
            ]}
          />
        )}
      </Card>
      {saleId && <SaleDetailModal saleId={saleId} onClose={() => setSaleId(null)} onChanged={reload} />}
    </>
  );
}
