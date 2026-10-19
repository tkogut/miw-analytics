"""
MetabaseClient — Bezpieczny klient analityczny dla Metabase (Odoo BI)
Zgodny ze standardem AGENTS-OS v6.5 Swarm Edition.

Kluczowe gwarancje:
1. STRICTLY READ-ONLY: Wyłącznie operacje SELECT, blokada mutacji danych.
2. ZERO ALERT FLOOD:
   - Trwały cache sesji (.metabase_session.json) ważny 14 dni.
   - Zapamiętywanie i wysyłanie ciasteczka `metabase.DEVICE`.
   - Nagłówek Chrome User-Agent.
   - Sprawdzanie ważności sesji (GET /api/user/current) PRZED próbą logowania.
"""

import json
import logging
import os
import re
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union

import requests
from dotenv import load_dotenv

logger = logging.getLogger("MetabaseClient")
if not logger.handlers:
    handler = logging.StreamHandler()
    formatter = logging.Formatter("[%(asctime)s] [%(levelname)s] %(name)s: %(message)s")
    handler.setFormatter(formatter)
    logger.addHandler(handler)
logger.setLevel(logging.INFO)


class ReadOnlyViolationError(PermissionError):
    """Zgłaszany przy próbie wykonania zapytania modyfikującego bazę."""
    pass


class MetabaseAuthenticationError(ConnectionError):
    """Zgłaszany przy błędach uwierzytelniania z Metabase."""
    pass


class MetabaseClient:
    """
    Bezpieczny klient do zapytań SQL przez API Metabase.
    """

    CHROME_USER_AGENT = (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
    )

    FORBIDDEN_SQL_KEYWORDS = {
        "INSERT", "UPDATE", "DELETE", "DROP", "ALTER", "TRUNCATE",
        "EXECUTE", "EXEC", "CREATE", "GRANT", "REVOKE", "MERGE",
        "REPLACE", "CALL", "UPSERT"
    }

    def __init__(
        self,
        base_url: Optional[str] = None,
        user: Optional[str] = None,
        password: Optional[str] = None,
        database_id: Optional[int] = None,
        session_cache_path: Optional[str] = None,
        api_key: Optional[str] = None,
        env_file: Optional[str] = None,
    ):
        if env_file:
            load_dotenv(env_file)
        else:
            load_dotenv()

        self.base_url = (base_url or os.getenv("METABASE_URL", "")).rstrip("/")
        self.user = user or os.getenv("METABASE_USER", "")
        self.password = password or os.getenv("METABASE_PASSWORD", "")
        
        db_id_env = os.getenv("METABASE_DB_ID", "15")
        self.database_id = int(database_id if database_id is not None else db_id_env)

        cache_path = session_cache_path or os.getenv(
            "METABASE_SESSION_CACHE_PATH", ".metabase_session.json"
        )
        self.session_cache_path = Path(cache_path).resolve()
        self.api_key = api_key or os.getenv("METABASE_API_KEY", "")

        self.session_id: Optional[str] = None
        self.device_id: Optional[str] = None
        self.user_info: Optional[Dict[str, Any]] = None

        if not self.base_url:
            raise ValueError("Brak adresu URL Metabase (METABASE_URL).")

    def _get_base_headers(self) -> Dict[str, str]:
        headers = {
            "User-Agent": self.CHROME_USER_AGENT,
            "Content-Type": "application/json",
            "Accept": "application/json",
        }
        if self.device_id:
            headers["Cookie"] = f"metabase.DEVICE={self.device_id}"
        if self.api_key:
            headers["x-api-key"] = self.api_key
        elif self.session_id:
            headers["X-Metabase-Session"] = self.session_id
        return headers

    def _load_cache(self) -> Optional[Dict[str, Any]]:
        if not self.session_cache_path.exists():
            return None
        try:
            with open(self.session_cache_path, "r", encoding="utf-8") as f:
                data = json.load(f)
                return data
        except Exception as e:
            logger.warning("Nie udało się odczytać cache sesji z %s: %s", self.session_cache_path, e)
            return None

    def _save_cache(self, session_id: str, device_id: Optional[str], user_info: Optional[Dict[str, Any]] = None):
        try:
            data = {
                "session_id": session_id,
                "device_id": device_id,
                "user_email": self.user,
                "saved_at": str(Path(self.session_cache_path).stat().st_mtime if self.session_cache_path.exists() else ""),
            }
            if user_info:
                data["user_info"] = {
                    "id": user_info.get("id"),
                    "email": user_info.get("email"),
                    "first_name": user_info.get("first_name"),
                    "last_name": user_info.get("last_name"),
                }
            self.session_cache_path.parent.mkdir(parents=True, exist_ok=True)
            with open(self.session_cache_path, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2)
            os.chmod(self.session_cache_path, 0o600)
            logger.info("Zapisano sesję do cache: %s (chmod 0600)", self.session_cache_path)
        except Exception as e:
            logger.warning("Nie udało się zapisać cache sesji: %s", e)

    def _check_session_alive(self, session_id: str, device_id: Optional[str]) -> Tuple[bool, Optional[Dict[str, Any]]]:
        headers = {
            "User-Agent": self.CHROME_USER_AGENT,
            "Accept": "application/json",
            "X-Metabase-Session": session_id,
        }
        if device_id:
            headers["Cookie"] = f"metabase.DEVICE={device_id}"

        url = f"{self.base_url}/api/user/current"
        try:
            resp = requests.get(url, headers=headers, timeout=10)
            if resp.status_code == 200:
                user_data = resp.json()
                if "id" in user_data or "email" in user_data:
                    return True, user_data
            return False, None
        except Exception as e:
            logger.warning("Błąd weryfikacji liveness sesji: %s", e)
            return False, None

    def authenticate(self, force_refresh: bool = False) -> bool:
        """
        Uwierzytelnia w Metabase zachowując tożsamość urządzenia (Zero Alert Flood).
        """
        if self.api_key:
            logger.info("Uwierzytelnianie za pomocą METABASE_API_KEY...")
            headers = self._get_base_headers()
            resp = requests.get(f"{self.base_url}/api/user/current", headers=headers, timeout=10)
            if resp.status_code == 200:
                self.user_info = resp.json()
                logger.info("Połączenie z API Key nawiązane pomyślnie.")
                return True
            raise MetabaseAuthenticationError(f"API Key odrzucony przez Metabase (status {resp.status_code}).")

        # 1. Sprawdź cache sesji (Liveness-First Check)
        cache = self._load_cache()
        if cache and not force_refresh:
            cached_session = cache.get("session_id")
            cached_device = cache.get("device_id")
            if cached_session:
                is_alive, user_data = self._check_session_alive(cached_session, cached_device)
                if is_alive:
                    self.session_id = cached_session
                    self.device_id = cached_device
                    self.user_info = user_data
                    logger.info("Aktywna sesja odzyskana z cache (Zero Alert Flood) dla: %s", user_data.get("email"))
                    return True
                else:
                    logger.info("Zapisana sesja w cache wygasła. Wymagane odnowienie logowania.")
                    if cached_device:
                        self.device_id = cached_device

        # 2. Logowanie (POST /api/session) z Device Cookie i Chrome UA
        if not self.user or not self.password:
            raise MetabaseAuthenticationError("Brak danych logowania (METABASE_USER / METABASE_PASSWORD).")

        login_url = f"{self.base_url}/api/session"
        headers = {
            "User-Agent": self.CHROME_USER_AGENT,
            "Content-Type": "application/json",
            "Accept": "application/json",
        }
        if self.device_id:
            headers["Cookie"] = f"metabase.DEVICE={self.device_id}"

        payload = {
            "username": self.user,
            "password": self.password,
        }

        logger.info("Nawiązywanie nowego logowania do Metabase: %s...", self.base_url)
        resp = requests.post(login_url, headers=headers, json=payload, timeout=15)

        if resp.status_code != 200:
            raise MetabaseAuthenticationError(
                f"Logowanie nie powiodło się (status {resp.status_code}): {resp.text[:200]}"
            )

        resp_data = resp.json()
        new_session_id = resp_data.get("id")
        if not new_session_id:
            raise MetabaseAuthenticationError("Brak tokena 'id' w odpowiedzi logowania Metabase.")

        self.session_id = new_session_id

        # Pobierz ciasteczko urządzenia
        device_cookie = resp.cookies.get("metabase.DEVICE")
        if device_cookie:
            self.device_id = device_cookie

        # Pobierz dane zalogowanego użytkownika
        _, user_data = self._check_session_alive(self.session_id, self.device_id)
        self.user_info = user_data

        # Zapisz do trwałego cache
        self._save_cache(self.session_id, self.device_id, self.user_info)
        logger.info("Zalogowano pomyślnie. Sesja zapisana na 14 dni.")
        return True

    def validate_read_only(self, sql_query: str) -> None:
        """
        Waliduje kwerendę pod kątem żelaznej reguły STRICTLY READ-ONLY.
        """
        # Usuń komentarze jedno- i wielolinijkowe oraz literały łańcuchowe
        cleaned = re.sub(r"--.*?$", "", sql_query, flags=re.MULTILINE)
        cleaned = re.sub(r"/\*.*?\*/", "", cleaned, flags=re.DOTALL)
        cleaned = re.sub(r"'(?:''|[^'])*'", "", cleaned)
        cleaned = cleaned.strip()

        tokens = re.findall(r"\b[A-Za-z_]+\b", cleaned)
        upper_tokens = [t.upper() for t in tokens]

        for token in upper_tokens:
            if token in self.FORBIDDEN_SQL_KEYWORDS:
                raise ReadOnlyViolationError(
                    f"⛔ Odmowa wykonania: Wykryto zabronioną operację modyfikującą bazę danych: '{token}'. "
                    f"Wszystkie zapytania muszą być STRICTLY READ-ONLY (SELECT)."
                )

        if not upper_tokens:
            raise ValueError("Pusta kwerenda SQL.")

        # Pierwsze słowo kluczowe powinno być SELECT lub WITH
        first_keyword = upper_tokens[0]
        if first_keyword not in ("SELECT", "WITH", "EXPLAIN"):
            raise ReadOnlyViolationError(
                f"⛔ Odmowa wykonania: Zapytanie musi zaczynać się od SELECT, WITH lub EXPLAIN, "
                f"otrzymano: '{first_keyword}'."
            )

    def query(self, sql_query: str, timeout: int = 60) -> Dict[str, Any]:
        """
        Wykonuje zapytanie SQL w Metabase na wybranej bazie danych (domyślnie 15).
        Zwraca sparsowane wyniki.
        """
        self.validate_read_only(sql_query)

        if not self.session_id and not self.api_key:
            self.authenticate()

        headers = self._get_base_headers()
        url = f"{self.base_url}/api/dataset"

        payload = {
            "database": self.database_id,
            "type": "native",
            "native": {
                "query": sql_query.strip()
            }
        }

        resp = requests.post(url, headers=headers, json=payload, timeout=timeout)

        # Jeśli token wygasł (401), spróbuj jednokrotnie odnowić sesję
        if resp.status_code == 401 and not self.api_key:
            logger.info("Otrzymano 401 z Metabase — odnawianie sesji...")
            self.authenticate(force_refresh=True)
            headers = self._get_base_headers()
            resp = requests.post(url, headers=headers, json=payload, timeout=timeout)

        if resp.status_code not in (200, 202):
            raise RuntimeError(
                f"Błąd wykonania zapytania w Metabase (status {resp.status_code}): {resp.text[:300]}"
            )

        data = resp.json()
        status = data.get("status")
        if status == "failed":
            error_msg = data.get("error", "Nieznany błąd wykonania kwerendy w Metabase.")
            raise RuntimeError(f"Metabase Query Error: {error_msg}")

        result_data = data.get("data", {})
        columns = [col.get("name") for col in result_data.get("cols", [])]
        rows = result_data.get("rows", [])

        return {
            "status": "success",
            "database_id": self.database_id,
            "columns": columns,
            "rows": rows,
            "row_count": len(rows),
            "raw": data,
        }

    def get_personal_collection_id(self) -> Optional[int]:
        """Zwraca identyfikator kolekcji osobistej aktualnego użytkownika."""
        if not self.user_info:
            self.authenticate()
        return self.user_info.get("personal_collection_id") if self.user_info else None

    def create_card(
        self,
        name: str,
        sql_query: str,
        collection_id: Optional[int] = None,
        display: str = "table",
        description: Optional[str] = None,
        visualization_settings: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Publikuje kwerendę SQL jako pytanie/kartę (Card) w Metabase (POST /api/card).
        Operacja dotyczy wyłącznie wewnętrznej bazy aplikacji Metabase (Zero zmian w Odoo).
        """
        self.validate_read_only(sql_query)
        if not self.session_id and not self.api_key:
            self.authenticate()

        target_collection_id = collection_id
        if target_collection_id is None:
            target_collection_id = self.get_personal_collection_id()

        payload = {
            "name": name,
            "description": description or "",
            "collection_id": target_collection_id,
            "display": display,
            "database_id": self.database_id,
            "dataset_query": {
                "database": self.database_id,
                "type": "native",
                "native": {
                    "query": sql_query.strip(),
                },
            },
            "visualization_settings": visualization_settings or {},
        }

        headers = self._get_base_headers()
        url = f"{self.base_url}/api/card"

        resp = requests.post(url, headers=headers, json=payload, timeout=20)
        if resp.status_code == 401 and not self.api_key:
            logger.info("Otrzymano 401 podczas tworzenia karty — odnawianie sesji...")
            self.authenticate(force_refresh=True)
            headers = self._get_base_headers()
            resp = requests.post(url, headers=headers, json=payload, timeout=20)

        if resp.status_code not in (200, 201, 202):
            raise RuntimeError(
                f"Błąd tworzenia karty w Metabase (status {resp.status_code}): {resp.text[:300]}"
            )

        card_data = resp.json()
        card_id = card_data.get("id")
        card_url = f"{self.base_url}/question/{card_id}"
        card_data["web_url"] = card_url
        logger.info(
            "Utworzono kartę '%s' (ID %s) w kolekcji %s: %s",
            name, card_id, target_collection_id, card_url
        )
        return card_data

    def create_dashboard(
        self,
        name: str,
        description: Optional[str] = None,
        collection_id: Optional[int] = None,
    ) -> Dict[str, Any]:
        """Tworzy pulpit w Metabase (POST /api/dashboard)."""
        if not self.session_id and not self.api_key:
            self.authenticate()

        target_collection_id = collection_id or self.get_personal_collection_id()
        payload = {
            "name": name,
            "description": description or "",
            "collection_id": target_collection_id,
        }
        headers = self._get_base_headers()
        url = f"{self.base_url}/api/dashboard"
        resp = requests.post(url, headers=headers, json=payload, timeout=20)
        if resp.status_code not in (200, 201, 202):
            raise RuntimeError(f"Błąd tworzenia pulpitu (status {resp.status_code}): {resp.text[:300]}")
        data = resp.json()
        data["web_url"] = f"{self.base_url}/dashboard/{data.get('id')}"
        return data

    def add_card_to_dashboard(
        self,
        dashboard_id: int,
        card_id: int,
        row: int = 0,
        col: int = 0,
        size_x: int = 18,
        size_y: int = 10,
    ) -> Dict[str, Any]:
        """Dodaje kartę do dashboardu (POST /api/dashboard/:id/cards)."""
        if not self.session_id and not self.api_key:
            self.authenticate()

        payload = {
            "cardId": card_id,
            "row": row,
            "col": col,
            "size_x": size_x,
            "size_y": size_y,
        }
        headers = self._get_base_headers()
        url = f"{self.base_url}/api/dashboard/{dashboard_id}/cards"
        resp = requests.post(url, headers=headers, json=payload, timeout=20)
        if resp.status_code not in (200, 201, 202):
            raise RuntimeError(f"Błąd dodawania karty do pulpitu (status {resp.status_code}): {resp.text[:300]}")
        return resp.json()

    def test_connection(self) -> Dict[str, Any]:
        """
        Weryfikuje połączenie z Metabase i bazą danych Odoo.
        """
        self.authenticate()
        test_query = "SELECT 1 AS connection_test, current_database() AS db_name, version() AS pg_version;"
        res = self.query(test_query)
        return {
            "metabase_url": self.base_url,
            "user": self.user_info.get("email") if self.user_info else self.user,
            "database_id": self.database_id,
            "query_result": res.get("rows"),
            "status": "CONNECTED_OK",
        }


if __name__ == "__main__":
    client = MetabaseClient()
    logger.info("Rozpoczynanie testu połączenia z Metabase...")
    info = client.test_connection()
    print("\n--- METABASE CONNECTION TEST SUCCESS ---")
    print(json.dumps(info, indent=2))

