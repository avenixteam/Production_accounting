import { useState } from 'react';
import API, { errMsg } from '../api';
import MasterPage from '../components/MasterPage.jsx';
import { useToast } from '../components/Toast.jsx';
import { Button, Modal, Select, Spinner } from '../components/ui.jsx';
import { useFetch } from '../hooks/useFetch';
import { fmtMoney, rmLabel } from '../utils';

function RecipeModal({ product, onClose }) {
  const toast = useToast();
  const { data: materials } = useFetch('/raw-materials');
  const { data: recipe, loading } = useFetch(`/products/${product.id}/recipe`);
  const [lines, setLines] = useState(null);
  const [saving, setSaving] = useState(false);

  // Retsept yuklangach, bir marta tahrirlanadigan holatga ko'chiramiz
  if (recipe && lines === null) {
    setLines(recipe.map((r) => ({ raw_material_id: String(r.raw_material_id), quantity: String(r.quantity) })));
  }

  const update = (i, patch) => setLines(lines.map((l, idx) => (idx === i ? { ...l, ...patch } : l)));

  const save = async () => {
    const items = lines.filter((l) => l.raw_material_id && l.quantity !== '');
    setSaving(true);
    try {
      await API.put(`/products/${product.id}/recipe`, {
        items: items.map((l) => ({ raw_material_id: Number(l.raw_material_id), quantity: Number(l.quantity) })),
      });
      toast.success('Retsept saqlandi');
      onClose();
    } catch (err) {
      toast.error(errMsg(err));
    } finally {
      setSaving(false);
    }
  };

  const options = (materials || []).map((m) => ({ value: m.id, label: `${rmLabel(m)} (${m.unit})` }));

  return (
    <Modal
      title={`Retsept: ${product.name}`}
      onClose={onClose}
      footer={
        <>
          <Button variant="secondary" onClick={onClose}>Bekor qilish</Button>
          <Button onClick={save} loading={saving} disabled={lines === null}>Saqlash</Button>
        </>
      }
    >
      <p className="muted" style={{ marginBottom: 12 }}>
        1 {product.unit} mahsulot ishlab chiqarish uchun qancha xomashyo sarflanishini kiriting.
        Ishlab chiqarish hisobotida xomashyo shu retsept bo'yicha avtomatik hisoblanadi.
      </p>
      {loading || lines === null ? (
        <Spinner />
      ) : (
        <div className="lines">
          {lines.map((l, i) => (
            <div className="line recipe" key={i}>
              <Select value={l.raw_material_id} onChange={(v) => update(i, { raw_material_id: v })} options={options} placeholder="Xomashyo" />
              <input type="number" step="any" min="0" placeholder="Miqdor" value={l.quantity} onChange={(e) => update(i, { quantity: e.target.value })} />
              <Button variant="danger" size="sm" onClick={() => setLines(lines.filter((_, idx) => idx !== i))}>×</Button>
            </div>
          ))}
          <div>
            <Button variant="secondary" size="sm" onClick={() => setLines([...lines, { raw_material_id: '', quantity: '' }])}>
              + Xomashyo qo'shish
            </Button>
          </div>
        </div>
      )}
    </Modal>
  );
}

export default function Products() {
  const [recipeFor, setRecipeFor] = useState(null);
  return (
    <>
      <MasterPage
        title="Mahsulotlar"
        subtitle="Tayyor mahsulotlar va ularning retseptlari"
        endpoint="/products"
        singular="mahsulot"
        defaults={{ unit: 'dona', price: 0 }}
        fields={[
          { name: 'name', label: 'Nomi', required: true },
          { name: 'code', label: 'Artikul (kod)', placeholder: 'Ixtiyoriy, noyob' },
          { name: 'unit', label: "O'lchov birligi", required: true, placeholder: 'dona' },
          { name: 'price', label: "Sotuv narxi (so'm)", type: 'number', step: '0.01', required: true },
        ]}
        columns={[
          { key: 'name', header: 'Nomi', render: (r) => <b>{r.name}</b> },
          { key: 'code', header: 'Artikul' },
          { key: 'unit', header: "O'lchov" },
          { key: 'price', header: 'Narxi', align: 'right', render: (r) => fmtMoney(r.price) },
        ]}
        rowActions={(r) => (
          <Button variant="secondary" size="sm" onClick={() => setRecipeFor(r)}>Retsept</Button>
        )}
      />
      {recipeFor && <RecipeModal product={recipeFor} onClose={() => setRecipeFor(null)} />}
    </>
  );
}
