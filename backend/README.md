# Social Event Mapper — Backend

FastAPI + Supabase ile JWT tabanlı authentication sistemi.

## Kurulum

### 1. Env dosyasını oluştur

```bash
cp .env.example .env
```

`.env` içindeki değerleri doldur:

| Değişken | Nereden alınır |
|----------|----------------|
| `SUPABASE_URL` | Supabase Dashboard → Settings → API |
| `SUPABASE_KEY` | Supabase Dashboard → Settings → API → `service_role` key |
| `JWT_SECRET` | `openssl rand -base64 32` |
| `JWT_REFRESH_SECRET` | `openssl rand -base64 32` |
| `GOOGLE_CLIENT_ID` | Google Cloud Console → Credentials |
| `GOOGLE_CLIENT_SECRET` | Google Cloud Console → Credentials |
| `SMTP_USER` | Gmail adresi |
| `SMTP_PASSWORD` | Google Account → App Passwords |

### 2. Docker ile çalıştır

> **Not:** Supabase tabloları ortak hesapta zaten oluşturulmuş durumda. Sıfırdan kurulum gerekirse `sql/001_create_tables.sql` dosyasını Supabase SQL Editor'da çalıştır.

Proje root'unda (`docker-compose.yml`'ın olduğu yer):

```bash
docker-compose up --build
```

API: `http://localhost:8888`
Swagger docs: `http://localhost:8888/docs`

## API Endpoint'leri

| Method | Endpoint | Auth | Açıklama |
|--------|----------|------|----------|
| GET | /health | - | Sistem + DB durumu |
| POST | /auth/register | - | Kayıt (email + password) |
| POST | /auth/login | - | Giriş |
| POST | /auth/refresh | - | Access token yenileme |
| POST | /auth/logout | - | Çıkış |
| GET | /auth/me | Bearer | Kullanıcı bilgileri |
| GET | /auth/verify-email?token=x | - | Email onaylama |
| POST | /auth/resend-verification | Bearer | Onay maili tekrar gönder |
| GET | /auth/google?mode=login | - | Google OAuth başlat |
| GET | /auth/google/callback | - | Google OAuth callback |

## Teknolojiler

- **FastAPI** — Web framework
- **Supabase** — PostgreSQL veritabanı (`supabase-py` SDK)
- **bcrypt** — Password hashing
- **python-jose** — JWT token
- **Docker** — Containerization
