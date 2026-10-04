const nf = new Intl.NumberFormat('ru-RU', { maximumFractionDigits: 3 });
const nf0 = new Intl.NumberFormat('ru-RU', { maximumFractionDigits: 0 });

export const fmtNum = (n) => (n === null || n === undefined || n === '' ? '—' : nf.format(Number(n)));
export const fmtMoney = (n) => (n === null || n === undefined ? '—' : `${nf0.format(Math.round(Number(n)))} so'm`);
export const fmtDate = (d) => {
  if (!d) return '—';
  const [y, m, day] = String(d).slice(0, 10).split('-');
  return `${day}.${m}.${y}`;
};

const pad = (n) => String(n).padStart(2, '0');
export const toISO = (d) => `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}`;
export const today = () => toISO(new Date());
export const monthStart = () => {
  const d = new Date();
  return toISO(new Date(d.getFullYear(), d.getMonth(), 1));
};
export const daysAgo = (n) => {
  const d = new Date();
  d.setDate(d.getDate() - n);
  return toISO(d);
};
export const addMonths = (iso, n) => {
  const [y, m, d] = iso.split('-').map(Number);
  const dt = new Date(y, m - 1 + n, 1);
  const last = new Date(dt.getFullYear(), dt.getMonth() + 1, 0).getDate();
  return toISO(new Date(dt.getFullYear(), dt.getMonth(), Math.min(d, last)));
};

export const PAYMENT_TYPES = {
  cash: 'Naqd',
  card: 'Karta',
  transfer: "O'tkazma",
  installment: 'Muddatli',
};

export const SALE_STATUS = {
  paid: ["To'langan", 'green'],
  partial: ['Qisman', 'amber'],
  unpaid: ["To'lanmagan", 'gray'],
  overdue: ["Muddati o'tgan", 'red'],
};

export const MOVEMENT_TYPES = {
  receipt: ['Kirim', 'green'],
  usage: ['Ishlatildi', 'amber'],
  production: ['Ishlab chiqarildi', 'green'],
  sale: ['Sotildi', 'blue'],
  adjustment: ['Tuzatish', 'gray'],
};

export const rmLabel = (r) => (r?.name ? `${r.brand} — ${r.name}` : r?.brand || '');
