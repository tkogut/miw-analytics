# 🧠 AGENTS-OS v6.5 SWARM MEMORY ENGINE (v0.42.1)

---
version: 0.42.1
schema: agents-os-memory-v1
sync_mode: distributed-union
last_sync: 2026-10-19
---

## 🧭 Swarm Node & Machine Registry
- **Active Node**: Local Workspace (`/home/admin_tk/projects/miw-analytics`)
- **Sync Protocol**: Native Git Union Merge (`.gitattributes`)
- **Lifecycle Triggers**: `SessionStart` (rebase pull) / `SessionEnd` (auto state-dump push)

## 📌 Epics & Persistent Context
- **Active Epic**: Odoo BI & Metabase Analytics Engine (`miw-analytics`)
- **Primary Domain**: Analityka zamówień, sprzedaży i procesów biznesowych MIW Group z Odoo ERP za pośrednictwem Metabase (`https://reports.trilab.pl`).
- **System Constraints & Invariants**:
  - **STRICTLY READ-ONLY**: Kategoryczny zakaz zapisu, modyfikacji i usuwania danych w Odoo ERP. Wyłącznie kwerendy analityczne `SELECT`.
  - **Ochrona przed alertami e-mail (Zero Alert Flood)**: Implementacja `MetabaseClient` z trwałym cache sesji (`.metabase_session.json`), zachowaniem ciasteczka `metabase.DEVICE` i weryfikacją `GET /api/user/current` przed wywołaniem logowania.
  - **Tworzenie Raportów i Dashboardów w Metabase**: Pełne wsparcie dla programistycznego publikowania raportów / kart (`POST /api/card`) oraz interaktywnych pulpitów (`POST /api/dashboard`) w Metabase (zapis wyłącznie w bazie aplikacji Metabase w Personal Collection lub Shared Collections — zero zmian w Odoo).
  - Triad Separation of Concerns (Coordinator: plan & route / Builder: implement & test / Auditor: lint & verify).
  - Worktree Isolation Mandate (`tmp/worktrees/`).

## 📝 Decisions & Key Milestones
- [INIT] Project initialized under AGENTS-OS v6.5 Swarm Edition.
- [CONFIG] Skopiowano konfigurację środowiska do `.env` (dostęp do `https://reports.trilab.pl`, user `tomasz.kogut@miw.group`, Database ID `15` PostgreSQL Odoo).
- [SECURITY] Utworzono specyfikację architektury w `.agents/docs/metabase_architecture.md` zapobiegającą alertom e-mail o nowym urządzeniu ("New login from a new device").
- [DATA] Potwierdzono identyfikatory: Company ID 1 (`MIW Group Tomasz Kogut Sp. k.`), waluta bazowa PLN (ID 17).
- [CAPABILITY] Potwierdzono możliwość tworzenia wykresów, pytań (Cards) i pulpitów (Dashboards) w Metabase przez API bez naruszania bazy Odoo.
- [AUTH] Wdrożono i zweryfikowano `src/metabase_client.py` z architekturą Zero Alert Flood (trwały token w `.metabase_session.json` + `metabase.DEVICE` + Chrome UA). Nawiązano stabilne połączenie z instancją bazy PostgreSQL Odoo `prod` (DB 15).

## 🔄 Machine Session Log
<!-- Format: - [YYYY-MM-DD HH:MM UTC] [Node] [Role] Description -->
- [INIT] [Local] [Coordinator] Swarm memory initialized with union-merge capability.
- [2026-10-19 09:36 UTC] [Local] [Coordinator] Przeniesiono konfigurację środowiskową i zarejestrowano architekturę bezpiecznego klienta MetabaseClient.
- [2026-10-19 09:44 UTC] [Local] [Builder/Coordinator] Zaimplementowano moduł MetabaseClient, przeprowadzono testy jednostkowe i live handshake z Metabase (DB 15 / Odoo prod).
- [2026-10-19 09:41 UTC] [Local] [Coordinator] Zarejestrowano architekturę tworzenia raportów (Cards) i Dashboardów bezpośrednio w Metabase.
