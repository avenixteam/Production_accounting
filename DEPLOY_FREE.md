# Bepul 24/7 joylashtirish: Oracle Cloud "Always Free"

## Nega aynan Oracle?

2026-yil holatiga (manbalar: InfoQ, SnapDeploy, Public APIs sharhlari) uyg'otish kutmaydigan (sleep yo'q), haqiqiy doimiy ishlaydigan bepul server beradigan yagona yirik variant Oracle Cloud Always Free hisoblanadi. Qolganlari:

| Variant | Muammo |
|---|---|
| Render (bepul) | 15 daqiqa so'rov bo'lmasa uxlaydi (~1 daqiqada uyg'onadi); bepul baza 30 kundan keyin o'chiriladi |
| Koyeb, Replit va shu kabilar | Bepul tarifda uxlaydi |
| Fly.io, Railway, Heroku | Bepul tarif yo'q |
| Neon / Supabase (faqat baza) | Neon uxlaydi va uzoqda; Supabase 1 hafta faolsizlikdan keyin to'xtatadi |
| Vercel / Netlify / Cloudflare Pages | Faqat statik frontend, backend va baza yo'q |

## Oracle'ning kamchiliklari (oldindan biling)

1. **Karta kerak.** Ro'yxatdan o'tishda xalqaro Visa/Mastercard so'raladi (tekshiruv uchun ~$1 vaqtincha blok qilinishi mumkin). Uzcard/Humo odatda o'tmaydi, bu sizda to'siq bo'lishi mumkin.
2. **2026-yil iyunidan bepul ARM server yarmiga qisqargan:** 2 OCPU + 12 GB RAM (oldin 4 + 24 edi). Bu loyiha uchun yetarli.
3. **"Out of capacity" xatosi.** Ba'zi regionlarda bepul ARM server bo'sh bo'lmaydi. Bir necha soatdan keyin qayta urinib ko'ring yoki boshqa availability domain tanlang. Home region'ni keyin o'zgartirib bo'lmaydi.
4. **Faolsizlik (idle) xavfi.** Oracle hujjatlariga ko'ra, 7 kun davomida CPU yuklamasi (95-persentil) 20% dan past bo'lgan Always Free server qaytarib olinishi mumkin. Hisob tizimi tabiatan yengil, shuning uchun bu xavf real. Himoya: (a) har kuni zaxira nusxani tashqariga ko'chirish, (b) xohlasangiz hisobni Pay-As-You-Go'ga o'tkazish (bepul limit ichida qolsangiz to'lov yo'q; bu idle-reclaim'dan himoya qilishini Oracle hujjatidan o'zingiz tekshiring), (c) server qaytarib olinsa, zaxiradan 30 daqiqada boshqa joyda tiklash.
5. **Kafolat (SLA) yo'q.** Shartlar o'zgarib turadi (bu yil allaqachon bir marta o'zgardi). Zavod uchun muhim tizim bo'lsa, ~$5-7/oy to'lab oddiy VPS olish (Hetzner, DigitalOcean yoki mahalliy provayder) ancha ishonchli. Bu loyiha o'sha serverda ham aynan shu buyruqlar bilan ishlaydi.
6. **Shaxsiy ma'lumotlar.** Mijozlar ism/telefoni saqlanadi. O'zbekiston qonunchiligidagi shaxsiy ma'lumotlarni mamlakat ichida saqlash talabi sizga tegishli bo'lishi mumkin; mutaxassisdan tekshiring.

## Qadamlar

### 1. Server yaratish
- cloud.oracle.com da ro'yxatdan o'ting, Compute > Instances > Create instance.
- Image: **Ubuntu 24.04** (aarch64). Shape: **VM.Standard.A1.Flex**, **2 OCPU, 12 GB** (undan oshirmang, aks holda server o'chiriladi yoki pul yechiladi).
- SSH kalitni yuklab oling/yuklang. Boot volume 50-100 GB.
- Networking: public IP yoqilgan bo'lsin.

### 2. Portlarni ochish (ikki joyda!)
1. Oracle konsolida: VCN > Security List > Ingress Rules: **80** va **443** (TCP, 0.0.0.0/0) qo'shing.
2. Serverning o'zida (Oracle Ubuntu image'larida iptables yopiq):
```bash
sudo iptables -I INPUT 6 -m state --state NEW -p tcp --dport 80 -j ACCEPT
sudo iptables -I INPUT 6 -m state --state NEW -p tcp --dport 443 -j ACCEPT
sudo apt-get install -y iptables-persistent && sudo netfilter-persistent save
```

### 3. Docker o'rnatish
```bash
ssh ubuntu@SERVER_IP
curl -fsSL https://get.docker.com | sudo sh
sudo usermod -aG docker $USER && exit      # qayta kiring
```

### 4. Loyihani yuklash va ishga tushirish
```bash
# kompyuteringizdan:
scp -r Production_accounting ubuntu@SERVER_IP:~/
# serverda:
cd ~/Production_accounting
cp .env.example .env
nano .env     # SECRET_KEY=$(python3 -c "import secrets;print(secrets.token_urlsafe(48))")
              # POSTGRES_PASSWORD=$(openssl rand -base64 24)
docker compose -f docker-compose.prod.yml up -d --build
docker compose -f docker-compose.prod.yml exec backend python create_user.py admin --role admin
```
Brauzerda `http://SERVER_IP` oching va kiring. Birinchi build ARM serverda 5-10 daqiqa olishi mumkin.

### 5. Neon'dagi ma'lumotlarni ko'chirish (kerak bo'lsa)
```bash
NEON_URL="postgresql://USER:PASS@HOST/DB?sslmode=require" ./scripts/migrate_from_neon.sh
docker compose -f docker-compose.prod.yml restart backend
```
Eslatma: ko'chirilgan bazada `users` jadvali bo'lmaydi. Yuqoridagi `create_user.py` ni keyin ishga tushiring.

### 6. Bepul domen va HTTPS (tavsiya etiladi)
Login paroli HTTP orqali ochiq ketmasligi uchun HTTPS qo'ying. Bepul subdomen: masalan duckdns.org da `zavodim.duckdns.org` ni server IP'siga yo'naltiring, so'ng `.env` da:
```
SITE_ADDRESS=zavodim.duckdns.org
```
va `docker compose -f docker-compose.prod.yml up -d`. Caddy sertifikatni o'zi oladi.

### 7. Zaxira va monitoring
```bash
crontab -e
0 2 * * * /home/ubuntu/Production_accounting/scripts/backup.sh >> /home/ubuntu/backup.log 2>&1
```
- Nusxalarni tashqariga ko'chiring: `rclone` (Google Drive/Dropbox bepul) va `backup.sh` oxiridagi qatorni yoqing.
- UptimeRobot (bepul) da `https://DOMEN/api/health` ni har 5 daqiqada tekshirtiring, Telegram/email xabar oling.
- Disk to'lib ketmasligi uchun ba'zan `df -h` ni tekshiring.

### 8. Qo'shimcha (ixtiyoriy)
Xotira kam bo'lsa yoki build paytida "killed" chiqsa, 2 GB swap qo'shing:
```bash
sudo fallocate -l 2G /swapfile && sudo chmod 600 /swapfile && sudo mkswap /swapfile && sudo swapon /swapfile
echo '/swapfile none swap sw 0 0' | sudo tee -a /etc/fstab
```
