# 📋 AGENTS-OS v6.5 Swarm Task Backlog

---
version: 6.5-swarm
sync_mode: distributed-union
---

## 🚀 Active Epics & Tickets
- [ ] **T-002**: Skrypt analityczny i weryfikacja odczytu zamówień Odoo (MIW Group 2026)
  - **Role**: Builder
  - **Status**: READY
  - **Scope**: Zapytania SQL do bazy `15` (`sale_order`, `res_currency_rate`), kwoty netto/miesięcznie dla Company ID 1.
- [ ] **T-003**: Generator raportów analitycznych i publikacja w Metabase (Cards & Dashboards API)
  - **Role**: Builder
  - **Status**: BACKLOG
  - **Scope**: Metody w `MetabaseClient` i skrypty CLI do tworzenia pytań/kart (`POST /api/card`) oraz dashboardów (`POST /api/dashboard`, `POST /api/dashboard/:id/cards`) z siatką (grid layout) w Personal/Shared Collections. Strict Read-Only dla Odoo.

## 📦 Backlog
<!-- Add new tasks below. Conflict-free union merge enabled. -->

## ✅ Completed Tasks
- [x] **T-001**: Implementacja bezpiecznego modułu `MetabaseClient` (Persistent Session Cache + Device Cookie) — zweryfikowano połączenie z Metabase (DB 15, PostgreSQL 17.11 Odoo `prod`), testy jednostkowe PASS, handshake zarejestrowany (2026-10-19)
- [x] **T-000**: Inicjalizacja projektu, konfiguracja `.env` i rejestracja architektury MetabaseClient w `.agents/docs/metabase_architecture.md` (2026-10-19)
