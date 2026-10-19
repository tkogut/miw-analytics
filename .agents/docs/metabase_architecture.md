# 📊 Architektura Integracji Metabase (Odoo BI) & MetabaseClient

## 1. Kontekst i Przeznaczenie Systemu
Projekt `miw-analytics` służy do automatycznej analizy danych sprzedażowych, finansowych oraz operacyjnych z systemu **Odoo ERP**, z wykorzystaniem instancji analitycznej **Metabase** (`https://reports.trilab.pl`).

---

## 2. Parametry Połączenia i Środowiska
- **URL Metabase:** `https://reports.trilab.pl`
- **Użytkownik:** `tomasz.kogut@miw.group` (konto w `.env`)
- **ID Bazy Danych w Metabase:** `15` (Instancja bazy PostgreSQL dla Odoo MIW)
- **Firma Główna w Odoo:** Company ID `1` (`MIW Group Tomasz Kogut Sp. k.`)
- **Waluta Bazowa:** PLN (ID `17`), przeliczenia historyczne walut (np. EUR) realizowane przez tabelę `res_currency_rate`.
- **Zmienne środowiskowe (`.env`):**
  - `METABASE_URL`
  - `METABASE_USER`
  - `METABASE_PASSWORD`
  - `METABASE_DB_ID` (domyślnie `15`)
  - `METABASE_SESSION_CACHE_PATH` (domyślnie `.metabase_session.json`)
  - `METABASE_API_KEY` (opcjonalny)

---

## 3. Żelazna Reguła Bezpieczeństwa: STRICTLY READ-ONLY ⛔
- **Kategoryczny zakaz zapisu:** Wszystkie kwerendy wysyłane do bazy danych Metabase/Odoo MUSZĄ być wyłącznie operacjami odczytu (`SELECT`).
- **Niedozwolone:** `INSERT`, `UPDATE`, `DELETE`, `DROP`, `ALTER`, `TRUNCATE`, `EXECUTE`.
- Każde zapytanie analityczne musi być walidowane pod kątem braku mutacji danych.

---

## 4. Problem Alertów E-mail i Wypracowane Rozwiązanie (MetabaseClient)

### 4.1 Przyczyna wcześniejszych ostrzeżeń ("New login from a new device")
Metabase posiada mechanizm bezpieczeństwa:
Każde wywołanie `POST /api/session` bez ciasteczka `metabase.DEVICE` i/lub z domyślnym nagłówkiem biblioteki (`Python-urllib`) jest traktowane jako **nowe urządzenie**. Przy wielokrotnym uruchamianiu skryptów bez cache sesji generowało to natychmiastowe e-maile ostrzegawcze na skrzynkę użytkownika.

### 4.2 Standard Architektury `MetabaseClient` (Zero Alert Flood)
Moduł klienta `MetabaseClient` rozwiązuje ten problem na 4 poziomach:

1. **Persistent Session Cache (`.metabase_session.json`):**
   - Po pierwszym pomyślnym zalogowaniu token sesji (`id`) oraz wartość ciasteczka `metabase.DEVICE` są zapisywane w lokalnym pliku JSON z uprawnieniami `0600` (w `.gitignore`).
   - Token sesji Metabase jest ważny przez **14 dni** (`MB_SESSION_COOKIE_TIMEOUT`).

2. **Liveness-First Check (Sprawdzenie przed logowaniem):**
   - Zamiast logować się za każdym razem, klient najpierw odpytuje endpoint `GET /api/user/current` z nagłówkiem `X-Metabase-Session`.
   - Jeśli status to `200 OK`, zapytanie bazodanowe jest wykonywane natychmiast przy użyciu aktywnego tokena — **zero wywołań `/api/session`, zero e-maili**.

3. **Zachowanie Tożsamości Urządzenia (`metabase.DEVICE` + Chrome User-Agent):**
   - Gdy token wygaśnie (raz na 14 dni), skrypt wykonuje logowanie, dołączając nagłówek `Cookie: metabase.DEVICE=<zapisane_id>` oraz realistyczny `User-Agent: Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36`.
   - Metabase rozpoznaje to jako to samo, znane urządzenie i **nie wysyła** powiadomienia e-mail.

4. **Wsparcie dla API Key (`x-api-key`):**
   - Jeśli w zmiennych `.env` podany zostanie `METABASE_API_KEY`, klient pomija mechanizm sesji użytkownika i komunikuje się wyłącznie przez klucz API.

---

## 5. Wykonanie Zapytań SQL przez API Metabase
Endpoint do uruchamiania kwerend SQL (Database ID = 15):
- **POST** `/api/dataset`
- **Body:**
```json
{
  "database": 15,
  "type": "native",
  "native": {
    "query": "SELECT to_char(date_order, 'YYYY-MM') as miesiac, sum(amount_untaxed) as netto FROM sale_order WHERE state = 'sale' AND company_id = 1 AND date_order >= '2026-01-01' GROUP BY to_char(date_order, 'YYYY-MM') ORDER BY miesiac;"
  }
}
```
- **Nagłówki:**
  - `X-Metabase-Session: <token>`
  - `Content-Type: application/json`
  - `User-Agent: Mozilla/5.0 ...`

---

## 6. Przetestowane Schematy Odoo w Metabase
- **Zamówienia sprzedaży:** `sale_order`
  - Status potwierdzony: `state = 'sale'`
  - Kwota netto: `amount_untaxed`
  - Data zamówienia: `date_order`
  - Firma: `company_id = 1` (`MIW Group Tomasz Kogut Sp. k.`)
- **Przeliczenia walut:**
  - `currency_id = 17` -> PLN
  - Inne waluty (np. EUR) przeliczane po kursie z `res_currency_rate` na dzień zamówienia lub z pól `amount_untaxed` po znormalizowanym kursie.
