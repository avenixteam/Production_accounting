import { useEffect, useState } from 'react';
import API, { errMsg } from '../api';
import { useToast } from '../components/Toast.jsx';
import DailyReportModal from '../components/DailyReport.jsx';
import { Badge, Button, Card, DateField, DateRange, ErrorBox, Field, Modal, PageHeader, Select, Spinner, Table } from '../components/ui.jsx';
import { useFetch } from '../hooks/useFetch';
import { fmtDate, fmtNum, monthStart, rmLabel, today, widenRange } from '../utils';

const emptyLine = () => ({ product_id: '', partner_id: '', quantity: '' });

function MaterialsPreview({ lines }) {
  const [state, setState] = useState({ loading: false, data: null, error: null });
  const valid = lines
    .filter((l) => l.product_id && l.partner_id && Number(l.quantity) > 0)
    .map((l) => ({ product_id: Number(l.product_id), partner_id: Number(l.partner_id), quantity: Number(l.quantity) }));
  const key = JSON.stringify(valid);

  useEffect(() => {
    const items = JSON.parse(key);
    if (!items.length) return undefined;
    let cancelled = false;
    const timer = setTimeout(() => {
      setState((s) => ({ ...s, loading: true }));
      API.post('/production/preview', { items })
        .then((r) => !cancelled && setState({ loading: false, data: r.data, error: null }))
        .catch((e) => !cancelled && setState({ loading: false, data: null, error: errMsg(e) }));
    }, 350);
    return () => {
      cancelled = true;
      clearTimeout(timer);
    };
  }, [key]);

  if (!valid.length) return <p className="muted" style={{ marginTop: 14 }}>Mahsulot, hamkor va miqdorni kiriting — kerakli xomashyo avtomatik hisoblanadi.</p>;
  if (state.error) return <div className="alert error" style={{ marginTop: 14 }}>{state.error}</div>;
  if (!state.data) return <Spinner />;

  return (
    <div className="preview">
      <div className="head">Kerakli xomashyo (retsept bo'yicha) {state.loading && '…'}</div>
      <Table
        rows={state.data.lines.map((l, i) => ({ ...l, id: i }))}
        columns={[
          { key: 'partner_name', header: 'Hamkor' },
          { key: 'brand', header: 'Xomashyo', render: (r) => <b>{r.brand}</b> },
          { key: 'required', header: 'Kerak', align: 'right', render: (r) => `${fmtNum(r.required)} ${r.unit}` },
          { key: 'available', header: 'Mavjud', align: 'right', render: (r) => `${fmtNum(r.available)} ${r.unit}` },
          {
            key: 'ok', header: 'Holat',
            render: (r) => (r.ok ? <Badge tone="green">Yetarli</Badge> : <Badge tone="red">{fmtNum(r.shortage)} {r.unit} yetmaydi</Badge>),
          },
        ]}
      />
    </div>
  );
}

function ProductionForm({ onClose, onSaved }) {
  const toast = useToast();
  const { data: machines } = useFetch('/machines');
  const { data: products } = useFetch('/products');
  const { data: partners } = useFetch('/partners');
  const [head, setHead] = useState({ date: today(), machine_id: '', note: '' });
  const [lines, setLines] = useState([emptyLine()]);
  const [allowNegative, setAllowNegative] = useState(false);
  const [saving, setSaving] = useState(false);

  const update = (i, patch) => setLines(lines.map((l, idx) => (idx === i ? { ...l, ...patch } : l)));
  const filled = lines.filter((l) => l.product_id && l.partner_id && Number(l.quantity) > 0);

  const save = async (e) => {
    e.preventDefault();
    setSaving(true);
    try {
      await API.post('/production', {
        date: head.date,
        machine_id: Number(head.machine_id),
        note: head.note.trim() || null,
        allow_negative: allowNegative,
        items: filled.map((l) => ({ product_id: Number(l.product_id), partner_id: Number(l.partner_id), quantity: Number(l.quantity) })),
      });
      toast.success('Ishlab chiqarish hisoboti saqlandi, xomashyo ombordan yechildi');
      onSaved(head.date);
    } catch (err) {
      toast.error(errMsg(err));
    } finally {
      setSaving(false);
    }
  };

  const pr = (products || []).map((p) => ({ value: p.id, label: `${p.name} (${p.unit})` }));
  const pa = (partners || []).map((p) => ({ value: p.id, label: p.name }));

  return (
    <Modal
      wide
      title="Yangi ishlab chiqarish hisoboti"
      onClose={onClose}
      footer={
        <>
          <Button variant="secondary" onClick={onClose}>Bekor qilish</Button>
          <Button type="submit" form="prod-form" loading={saving} disabled={!filled.length}>Saqlash</Button>
        </>
      }
    >
      <form id="prod-form" onSubmit={save}>
        <div className="form-grid" style={{ gridTemplateColumns: '1fr 1fr 2fr' }}>
          <DateField label="Sana *" value={head.date} onChange={(v) => setHead({ ...head, date: v })} />
          <Field label="Stanok *">
            <Select required value={head.machine_id} onChange={(v) => setHead({ ...head, machine_id: v })} options={(machines || []).map((m) => ({ value: m.id, label: m.name }))} />
          </Field>
          <Field label="Izoh"><input value={head.note} onChange={(e) => setHead({ ...head, note: e.target.value })} /></Field>
        </div>

        <h3 style={{ margin: '18px 0 8px' }}>Ishlab chiqarilgan mahsulotlar</h3>
        <div className="lines">
          {lines.map((l, i) => (
            <div className="line prod" key={i}>
              <Select value={l.product_id} onChange={(v) => update(i, { product_id: v })} options={pr} placeholder="Mahsulot" />
              <Select value={l.partner_id} onChange={(v) => update(i, { partner_id: v })} options={pa} placeholder="Hamkor (kimning xomashyosi)" />
              <input type="number" step="any" min="0" placeholder="Miqdor" value={l.quantity} onChange={(e) => update(i, { quantity: e.target.value })} />
              <Button variant="danger" size="sm" type="button" disabled={lines.length === 1} onClick={() => setLines(lines.filter((_, idx) => idx !== i))}>×</Button>
            </div>
          ))}
          <div><Button variant="secondary" size="sm" type="button" onClick={() => setLines([...lines, emptyLine()])}>+ Qator qo'shish</Button></div>
        </div>

        <MaterialsPreview lines={lines} />

        <label className="check" style={{ marginTop: 14 }}>
          <input type="checkbox" checked={allowNegative} onChange={(e) => setAllowNegative(e.target.checked)} />
          Xomashyo yetmasa ham saqlash (qoldiq minusga tushadi)
        </label>
      </form>
    </Modal>
  );
}

function Details({ report, onClose }) {
  return (
    <Modal title={`Ishlab chiqarish #${report.id} — ${fmtDate(report.date)}`} onClose={onClose} wide>
      <dl className="kv" style={{ marginBottom: 16 }}>
        <dt>Stanok</dt><dd>{report.machine_name}</dd>
        <dt>Izoh</dt><dd>{report.note || '—'}</dd>
      </dl>
      {report.items.map((it) => (
        <div key={it.id} className="preview" style={{ marginTop: 10 }}>
          <div className="head">{it.product_name} — {fmtNum(it.quantity)} {it.unit} ({it.partner_name})</div>
          <Table
            rows={it.materials.map((m, i) => ({ ...m, id: i }))}
            columns={[
              { key: 'brand', header: 'Sarflangan xomashyo', render: (m) => rmLabel(m) },
              { key: 'quantity', header: 'Miqdor', align: 'right', render: (m) => `${fmtNum(m.quantity)} ${m.unit}` },
            ]}
          />
        </div>
      ))}
    </Modal>
  );
}

export default function Production() {
  const toast = useToast();
  const [filters, setFilters] = useState({ from: monthStart(), to: today(), machine_id: '' });
  const { data, loading, error, reload } = useFetch('/production', { date_from: filters.from, date_to: filters.to, machine_id: filters.machine_id });
  const { data: machines } = useFetch('/machines', { include_inactive: true });
  const [creating, setCreating] = useState(false);
  const [view, setView] = useState(null);
  const [daily, setDaily] = useState(null); // { date, saved }

  const remove = async (r) => {
    if (!window.confirm(`Hisobot #${r.id} bekor qilinsinmi? Xomashyo omborga qaytariladi, tayyor mahsulot ombordan chiqariladi.`)) return;
    try {
      await API.delete(`/production/${r.id}`);
      toast.success('Hisobot bekor qilindi');
      reload();
    } catch (err) {
      toast.error(errMsg(err));
    }
  };

  const total = (data || []).reduce((s, r) => s + r.total_quantity, 0);

  return (
    <>
      <PageHeader
        title="Ishlab chiqarish"
        subtitle="Kunlik hisobotlar. Saqlanganda xomashyo retsept bo'yicha ombordan yechiladi, tayyor mahsulot omborga qo'shiladi."
        actions={<><Button variant="secondary" onClick={() => setDaily({ date: today(), saved: false })}>📥 Kunlik hisobot (Excel)</Button><Button onClick={() => setCreating(true)}>+ Yangi hisobot</Button></>}
      />
      <Card flush>
        <div className="filters">
          <DateRange from={filters.from} to={filters.to} onChange={({ from, to }) => setFilters({ ...filters, from, to })} />
          <Select value={filters.machine_id} onChange={(v) => setFilters({ ...filters, machine_id: v })} options={(machines || []).map((m) => ({ value: m.id, label: m.name }))} placeholder="Barcha stanoklar" />
          <span className="grow" />
          <span className="muted">Jami ishlab chiqarilgan: <b>{fmtNum(total)}</b></span>
        </div>
        <ErrorBox message={error} />
        {loading ? <Spinner /> : (
          <Table
            rows={data}
            empty="Tanlangan davrda hisobot yo'q"
            onRowClick={setView}
            columns={[
              { key: 'id', header: '№', width: 60 },
              { key: 'date', header: 'Sana', render: (r) => fmtDate(r.date) },
              { key: 'machine_name', header: 'Stanok' },
              { key: 'items', header: 'Mahsulotlar', render: (r) => r.items.map((i) => `${i.product_name} × ${fmtNum(i.quantity)}`).join(', ') },
              { key: 'total_quantity', header: 'Jami', align: 'right', render: (r) => fmtNum(r.total_quantity) },
              {
                key: 'a', header: '', align: 'right',
                render: (r) => <Button variant="danger" size="sm" onClick={(e) => { e.stopPropagation(); remove(r); }}>Bekor qilish</Button>,
              },
            ]}
          />
        )}
      </Card>
      {creating && (
        <ProductionForm
          onClose={() => setCreating(false)}
          onSaved={(d) => { setCreating(false); setFilters((f) => widenRange(f, d)); reload(); setDaily({ date: d, saved: true }); }}
        />
      )}
      {daily && <DailyReportModal initialDate={daily.date} saved={daily.saved} onClose={() => setDaily(null)} />}
      {view && <Details report={view} onClose={() => setView(null)} />}
    </>
  );
}
