import { useState } from 'react';
import { Button, Card, ErrorBox, PageHeader, Spinner, StatCard, Table } from '../components/ui.jsx';
import { useFetch } from '../hooks/useFetch';
import { fmtDate, fmtMoney } from '../utils';
import { SaleDetailModal } from './Sales.jsx';

export default function Debts() {
  const { data, loading, error, reload } = useFetch('/sales/debts');
  const [saleId, setSaleId] = useState(null);

  const total = (data || []).reduce((s, d) => s + d.debt, 0);

  return (
    <>
      <PageHeader title="Qarzdorlik" subtitle="Kimda qancha qarz bor: hamma qarzdorlar va ularning sotuvlari" />
      <div className="grid cols-4" style={{ marginBottom: 16 }}>
        <StatCard label="Jami qarz" value={fmtMoney(total)} tone={total > 0 ? 'amber' : 'green'} hint={`${data?.length || 0} ta qarzdor`} />
      </div>
      <ErrorBox message={error} />
      {loading ? <Spinner /> : !data?.length ? (
        <Card><p className="muted">Qarzdorlar yo'q 🎉</p></Card>
      ) : (
        data.map((d) => (
          <Card
            key={d.customer_id}
            flush
            className="mt"
            title={`${d.customer_name}${d.phone ? ` · ${d.phone}` : ''}`}
            actions={<b className="neg">{fmtMoney(d.debt)}</b>}
          >
            <Table
              rows={d.sales}
              columns={[
                {
                  key: 'id', header: 'Sotuv',
                  render: (s) => (
                    <>
                      <b>#{s.id}</b> · {fmtDate(s.date)}
                      <div className="muted" style={{ fontSize: 12 }}>Summa {fmtMoney(s.total)}, to'langan {fmtMoney(s.paid)}</div>
                    </>
                  ),
                },
                { key: 'debt', header: 'Qarz', align: 'right', render: (s) => <b className="neg">{fmtMoney(s.debt)}</b> },
                {
                  key: 'a', header: '', align: 'right',
                  render: (s) => <Button size="sm" variant="success" onClick={() => setSaleId(s.id)}>To'lov</Button>,
                },
              ]}
            />
          </Card>
        ))
      )}
      {saleId && <SaleDetailModal saleId={saleId} onClose={() => setSaleId(null)} onChanged={reload} />}
    </>
  );
}
