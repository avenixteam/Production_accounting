import MasterPage from '../components/MasterPage.jsx';

export const Partners = () => (
  <MasterPage
    title="Hamkorlar"
    subtitle="Xomashyo egalari va tayyor mahsulot hisobi yuritiladigan hamkorlar"
    endpoint="/partners"
    singular="hamkor"
    fields={[
      { name: 'name', label: 'Nomi / F.I.O.', required: true },
      { name: 'phone', label: 'Telefon', placeholder: '+998 90 123 45 67' },
    ]}
    columns={[
      { key: 'name', header: 'Nomi', render: (r) => <b>{r.name}</b> },
      { key: 'phone', header: 'Telefon' },
    ]}
  />
);

export const RawMaterials = () => (
  <MasterPage
    title="Xomashyolar"
    subtitle="Ishlab chiqarishda ishlatiladigan xomashyo turlari (brend bo'yicha)"
    endpoint="/raw-materials"
    singular="xomashyo"
    defaults={{ unit: 'kg' }}
    fields={[
      { name: 'brand', label: 'Brend / marka', required: true, placeholder: 'Masalan: PE-100' },
      { name: 'name', label: 'Nomi', placeholder: 'Masalan: Polietilen granula' },
      { name: 'unit', label: "O'lchov birligi", required: true, placeholder: 'kg' },
    ]}
    columns={[
      { key: 'brand', header: 'Brend', render: (r) => <b>{r.brand}</b> },
      { key: 'name', header: 'Nomi' },
      { key: 'unit', header: "O'lchov" },
    ]}
  />
);

export const Machines = () => (
  <MasterPage
    title="Stanoklar"
    subtitle="Ishlab chiqarish uskunalari"
    endpoint="/machines"
    singular="stanok"
    fields={[{ name: 'name', label: 'Nomi', required: true, placeholder: 'Masalan: Stanok-1' }]}
    columns={[{ key: 'name', header: 'Nomi', render: (r) => <b>{r.name}</b> }]}
  />
);

export const Customers = () => (
  <MasterPage
    title="Mijozlar"
    subtitle="Mahsulot sotib oluvchilar"
    endpoint="/customers"
    singular="mijoz"
    fields={[
      { name: 'name', label: 'Nomi / F.I.O.', required: true },
      { name: 'phone', label: 'Telefon' },
      { name: 'address', label: 'Manzil', full: true },
    ]}
    columns={[
      { key: 'name', header: 'Nomi', render: (r) => <b>{r.name}</b> },
      { key: 'phone', header: 'Telefon' },
      { key: 'address', header: 'Manzil' },
    ]}
  />
);
