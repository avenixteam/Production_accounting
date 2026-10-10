import MasterPage from '../components/MasterPage.jsx';
import { fmtMoney } from '../utils';

export default function Products() {
  return (
    <>
      <MasterPage
        title="Mahsulotlar"
        subtitle="Sotiladigan tayyor mahsulotlar va narxlari"
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
      />
    </>
  );
}
