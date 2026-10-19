# 📋 AGENTS-OS v6.5 Swarm Task Backlog

---
version: 6.5-swarm
sync_mode: distributed-union
---

## 🚀 Active Epics & Tickets
- [ ] **T-004**: Pulpit analityczny sprzedaży MIW Group (Dashboard w Metabase)
  - **Role**: Builder
  - **Status**: READY
  - **Scope**: Utworzenie dashboardu (`POST /api/dashboard`) w Personal/Shared Collection, dodanie kart z KPI (wartość zamówień, konwersja ofert, realizacja sprzedaży) z układem siatki.

## 📦 Backlog
<!-- Add new tasks below. Conflict-free union merge enabled. -->

## ✅ Completed Tasks
- [x] **T-003**: Generator raportów analitycznych i publikacja w Metabase (Card 725 'Wagi Samochodowe 2026' w Personal Collection 47, URL: https://reports.trilab.pl/question/725) (2026-10-19)
- [x] **T-002**: Skrypt analityczny i weryfikacja odczytu zamówień, ofert i faktur Odoo 2026 (Wagi Samochodowe crm_team=11, Company ID 1, waluta PLN) (2026-10-19)
- [x] **T-001**: Implementacja bezpiecznego modułu `MetabaseClient` (Persistent Session Cache + Device Cookie) — zweryfikowano połączenie z Metabase (DB 15, PostgreSQL 17.11 Odoo `prod`), testy jednostkowe PASS, handshake zarejestrowany (2026-10-19)
- [x] **T-000**: Inicjalizacja projektu, konfiguracja `.env` i rejestracja architektury MetabaseClient w `.agents/docs/metabase_architecture.md` (2026-10-19)
