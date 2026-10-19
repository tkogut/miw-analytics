# 📋 AGENTS-OS v6.5 Swarm Task Backlog

---
version: 6.5-swarm
sync_mode: distributed-union
---

## 🚀 Active Epics & Tickets
- [ ] **T-001**: Implementacja bezpiecznego modułu `MetabaseClient` (Persistent Session Cache + Device Cookie)
  - **Role**: Builder
  - **Status**: READY
  - **Scope**: Utworzenie `src/metabase_client.py` z obsługą cache tokena w `.metabase_session.json` (14 dni), zachowaniem ciasteczka `metabase.DEVICE`, nagłówkiem Chrome User-Agent i liveness check (`GET /api/user/current`) przed logowaniem. Strict Read-Only.
- [ ] **T-002**: Skrypt analityczny i weryfikacja odczytu zamówień Odoo (MIW Group 2026)
  - **Role**: Builder
  - **Status**: BACKLOG
  - **Scope**: Zapytania SQL do bazy `15` (`sale_order`, `res_currency_rate`), kwoty netto/miesięcznie dla Company ID 1.
- [ ] **T-003**: Generator raportów analitycznych i integracja CLI / API
  - **Role**: Builder
  - **Status**: BACKLOG

## 📦 Backlog
<!-- Add new tasks below. Conflict-free union merge enabled. -->

## ✅ Completed Tasks
- [x] **T-000**: Inicjalizacja projektu, konfiguracja `.env` i rejestracja architektury MetabaseClient w `.agents/docs/metabase_architecture.md` (2026-10-19)
