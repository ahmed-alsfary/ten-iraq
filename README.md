# TenderIQ Iraq

منصة ذكية للبحث ومراقبة وتحليل المناقصات والعطاءات الحكومية العراقية.

## Stack (Python)

| Layer | Choice |
|---|---|
| API + Web | FastAPI + Jinja2 + HTMX + Tailwind |
| ORM | SQLAlchemy 2 + Alembic |
| DB | PostgreSQL |
| Cache / Broker | Redis |
| Jobs | Celery |
| Storage | MinIO |
| Crawlers | httpx + BeautifulSoup (Scrapy/Playwright لاحقًا) |
| Search (V1) | PostgreSQL FTS (+ pgvector لاحقًا) |
| AI (Phase 2) | Ollama / Qwen + cloud provider abstraction |

> الواجهة تُخدم من بايثون (SSR) بدل Vue — أسهل للـSEO والـRTL، ونفس اللغة مع السكرابنج والـworkers.

## هيكل المشروع

```
ten-iraq/
├── docker-compose.yml
├── Dockerfile
├── backend/
│   ├── app/
│   │   ├── core/           # config, db, security
│   │   ├── domain/         # models, enums
│   │   ├── modules/        # identity, tenders, sources, web
│   │   ├── crawlers/       # Generic HTML (+ adapters لاحقًا)
│   │   ├── infrastructure/ # MinIO, etc.
│   │   ├── worker/         # Celery tasks
│   │   ├── templates/      # Frontend (Jinja)
│   │   └── static/
│   └── requirements.txt
└── README.md
```

## التشغيل السريع (بدون Docker)

> مهم: نفّذ الأوامر من مجلد المشروع `ten-iraq` وليس من مشروع آخر.

```bash
cd ~/Documents/GitHub/ten-iraq
chmod +x scripts/dev.sh
./scripts/dev.sh
```

ثم افتح:

- الموقع: http://localhost:8000
- API docs: http://localhost:8000/api/docs

الوضع المحلي يستخدم **SQLite** ولا يحتاج PostgreSQL / Redis / Docker.

### بديل يدوي

```bash
cd ~/Documents/GitHub/ten-iraq
cp .env.example .env
python3 -m venv .venv
source .venv/bin/activate
pip install -r backend/requirements.txt
cd backend
uvicorn app.main:app --reload --port 8000
```

## التشغيل مع Docker (اختياري)

ثبّت [Docker Desktop](https://www.docker.com/products/docker-desktop/) ثم:

```bash
cd ~/Documents/GitHub/ten-iraq
# عدّل .env إلى DATABASE_URL الخاصة بـ PostgreSQL
docker compose up --build
```

- الموقع: http://localhost:8000
- MinIO console: http://localhost:9001 (`tenderiq` / `tenderiqsecret`)

## API أساسي

```
POST /api/v1/auth/register
POST /api/v1/auth/login
GET  /api/v1/tenders
POST /api/v1/tenders
GET  /api/v1/sources
POST /api/v1/sources
POST /api/v1/sources/{id}/crawl
GET  /api/v1/health
```

## مراحل التطوير

1. **Phase 0** — Foundation (الحالي)
2. **Phase 1** — Sources + Crawler Engine + Search + Admin
3. **Phase 2** — OCR + AI Extraction + Change Detection
4. **Phase 3** — Alerts (Email / Telegram)
5. **Phase 4** — Company Matching + Subscriptions
6. **Phase 5** — Analytics / Forecasting / Enterprise API

## ملاحظة عن السكرابنج

لا تضع منطق كل موقع داخل الـHTTP request. المسار:

```
Source → Celery crawl_source → Crawler adapter → Dedup → Tender rows
```

### مصدر ITP (مفعّل)

يتم السحب من المنصة الرسمية [itp.iq](https://itp.iq/) عبر API العام:

```
POST https://api.itp.iq/api/bus/tenders/get
{"page": 0, "count": 50}
```

تشغيل أول زحف:

```bash
cd ~/Documents/GitHub/ten-iraq
source .venv/bin/activate
cd backend
PYTHONPATH=. python scripts/seed_and_crawl_itp.py
```

أو عبر API بعد إنشاء المصدر:

```
POST /api/v1/sources/{id}/crawl
```

لاحقًا يمكن إضافة:

- Scrapy project منفصل للزحف الثقيل
- Playwright للمواقع الديناميكية
- Custom adapters لكل بوابة معقدة
