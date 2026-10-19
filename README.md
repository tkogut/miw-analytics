# miw-analytics — Analityka Odoo ERP przez Metabase

Silnik analityczny i raportowy dla **MIW Group**, łączący się z instancją **Metabase** (`https://reports.trilab.pl`) w celu odczytu i agregacji danych sprzedażowych oraz finansowych z systemu Odoo ERP (Baza `15` PostgreSQL).

Zarządzany w standardzie **AGENTS-OS v6.5 Swarm Edition**.

---

## 🔒 Żelazne Reguły Bezpieczeństwa
1. **STRICTLY READ-ONLY**: Wyłącznie zapytania `SELECT` / odczyt danych. Kategoryczny zakaz jakichkolwiek mutacji w bazie Odoo/Metabase.
2. **Zero Alert Flood (Ochrona przed spamem e-mail z Metabase)**:
   - Każde zapytanie musi wykorzystywać trwały moduł `MetabaseClient` (lub skrypt z Persistent Session Cache).
   - Token sesji (`X-Metabase-Session`) i ciasteczko `metabase.DEVICE` są przechowywane w `.metabase_session.json` (ważność 14 dni).
   - Zawsze sprawdzaj `GET /api/user/current` przed podjęciem próby ponownego logowania.
   - Więcej szczegółów w dokumentacji: [`.agents/docs/metabase_architecture.md`](.agents/docs/metabase_architecture.md).

---

## 🚀 Szybki Start
1. Upewnij się, że plik `.env` jest skonfigurowany (posiada `METABASE_URL`, `METABASE_USER`, `METABASE_PASSWORD`, `METABASE_DB_ID=15`).
2. Śledź backlog zadań w [`task.md`](task.md) oraz stan pamięci w [`.agents/MEMORY.md`](.agents/MEMORY.md).
