import { useState } from 'react';
import { canShareFile, errMsg, fetchDailyReport, isIOS, reportFilename, saveBlob, shareFile } from '../api';
import { useFetch } from '../hooks/useFetch';
import { fmtNum } from '../utils';
import { useToast } from './Toast.jsx';
import { Button, DateField, Modal } from './ui.jsx';

/** Kunlik hisobotni Excel qilib olish oynasi. `saved` - hisobot hozirgina saqlangan bo'lsa. */
export default function DailyReportModal({ initialDate, saved = false, onClose }) {
  const toast = useToast();
  const [date, setDate] = useState(initialDate);
  const [busy, setBusy] = useState(false);
  const [ready, setReady] = useState(null); // iPhone: tayyor fayl, "Ulashish" tugmasi bosilishini kutyapti
  const { data } = useFetch('/production', { date_from: date, date_to: date });

  const count = data?.length ?? 0;
  const total = (data || []).reduce((s, r) => s + r.total_quantity, 0);
  const filename = reportFilename(date);

  const share = async (blob) => {
    try {
      await shareFile(blob, filename);
      setReady(null);
    } catch (err) {
      if (err?.name === 'AbortError') return; // foydalanuvchi oynani yopdi
      if (err?.name === 'NotAllowedError') {
        // iOS: tarmoq kutilgach "bosish" muddati o'tgan. Fayl tayyor, yana bir marta bossa bo'ldi
        setReady(blob);
        return;
      }
      saveBlob(blob, filename);
    }
  };

  const run = async () => {
    setBusy(true);
    setReady(null);
    try {
      const blob = await fetchDailyReport(date);
      if (isIOS() && canShareFile(blob, filename)) await share(blob);
      else {
        saveBlob(blob, filename);
        toast.success('Hisobot yuklab olindi');
      }
    } catch (err) {
      toast.error(errMsg(err));
    } finally {
      setBusy(false);
    }
  };

  const ios = isIOS();
  return (
    <Modal
      title={saved ? 'Hisobot saqlandi' : 'Kunlik hisobot (Excel)'}
      onClose={onClose}
      footer={
        <>
          <Button variant="secondary" onClick={onClose}>Yopish</Button>
          {ready ? (
            <Button onClick={() => share(ready)}>📤 Ulashish / saqlash</Button>
          ) : (
            <Button loading={busy} disabled={!date} onClick={run}>{ios ? '📤 Excel faylni olish' : '📥 Excelda yuklab olish'}</Button>
          )}
        </>
      }
    >
      {saved && <p className="muted" style={{ marginBottom: 12 }}>Yozuv saqlandi. Shu kunning hisobotini hozir olishingiz mumkin.</p>}
      <DateField label="Hisobot sanasi" value={date} onChange={(v) => { setDate(v); setReady(null); }} />
      <p className="muted" style={{ marginTop: 12 }}>
        {count > 0
          ? <>Shu kunda <b>{count}</b> ta ishlab chiqarish hisoboti, jami <b>{fmtNum(total)}</b>.</>
          : "Shu kunda ishlab chiqarish hisoboti yo'q. Fayl baribir yaratiladi (ombor, kirim, sotuv va xarajatlar bilan)."}
      </p>
      <p className="muted" style={{ marginTop: 8 }}>Faylda 4 ta varaq: ishlab chiqarish, xomashyo, tayyor mahsulot, moliya.</p>
      {ios && <p className="muted" style={{ marginTop: 8 }}>iPhone: tugmani bossangiz "Ulashish" oynasi ochiladi. U yerdan "Fayllarga saqlash", Telegram yoki Excel'ni tanlang.</p>}
      {ready && <p className="muted" style={{ marginTop: 8 }}><b>Fayl tayyor.</b> "Ulashish / saqlash" tugmasini bosing.</p>}
    </Modal>
  );
}
