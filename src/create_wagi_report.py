"""
Publikacja raportu analitycznego zespołu Wagi Samochodowe w Personal Collection Tomasza w Metabase.
Zgodny ze standardem AGENTS-OS v6.5 Swarm Edition.
Strictly Read-Only (baza Odoo) + Zero Alert Flood.
"""

import json
import logging
from pathlib import Path
import sys

# Ensure src/ is on sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent))

from metabase_client import MetabaseClient

logging.basicConfig(level=logging.INFO, format="[%(asctime)s] [%(levelname)s] %(message)s")
logger = logging.getLogger("CreateWagiReport")

WAGI_REPORT_SQL = """
WITH offers AS (
    SELECT 
        so.user_id,
        to_char(so.date_order, 'YYYY-MM') AS miesiac,
        count(*) AS liczba_ofert,
        round(sum(CASE WHEN coalesce(so.currency_rate, 0) > 0 THEN so.amount_untaxed / so.currency_rate ELSE so.amount_untaxed END)::numeric, 2) AS wartosc_ofert_pln
    FROM sale_order so
    WHERE so.team_id = 11 
      AND so.company_id = 1
      AND so.state IN ('draft', 'sent')
      AND so.date_order >= '2026-01-01' AND so.date_order < '2027-01-01'
    GROUP BY so.user_id, to_char(so.date_order, 'YYYY-MM')
),
orders AS (
    SELECT 
        so.user_id,
        to_char(so.date_order, 'YYYY-MM') AS miesiac,
        count(*) AS liczba_zamowien,
        round(sum(CASE WHEN coalesce(so.currency_rate, 0) > 0 THEN so.amount_untaxed / so.currency_rate ELSE so.amount_untaxed END)::numeric, 2) AS wartosc_zamowien_pln
    FROM sale_order so
    WHERE so.team_id = 11 
      AND so.company_id = 1
      AND so.state IN ('sale', 'done')
      AND so.date_order >= '2026-01-01' AND so.date_order < '2027-01-01'
    GROUP BY so.user_id, to_char(so.date_order, 'YYYY-MM')
),
invoices AS (
    SELECT 
        am.invoice_user_id AS user_id,
        to_char(am.invoice_date, 'YYYY-MM') AS miesiac,
        count(*) AS liczba_faktur,
        round(sum(am.amount_untaxed_signed)::numeric, 2) AS wartosc_faktur_pln
    FROM account_move am
    WHERE am.team_id = 11 
      AND am.company_id = 1
      AND am.state = 'posted'
      AND am.move_type = 'out_invoice'
      AND am.invoice_date >= '2026-01-01' AND am.invoice_date < '2027-01-01'
    GROUP BY am.invoice_user_id, to_char(am.invoice_date, 'YYYY-MM')
),
all_keys AS (
    SELECT user_id, miesiac FROM offers
    UNION
    SELECT user_id, miesiac FROM orders
    UNION
    SELECT user_id, miesiac FROM invoices
)
SELECT 
    k.miesiac AS "Miesiąc",
    coalesce(p.name, 'Nieprzypisany') AS "Handlowiec",
    coalesce(off.liczba_ofert, 0) AS "Oferty (liczba)",
    coalesce(off.wartosc_ofert_pln, 0.00) AS "Oferty (wartość netto PLN)",
    coalesce(ord.liczba_zamowien, 0) AS "Zamówienia (liczba)",
    coalesce(ord.wartosc_zamowien_pln, 0.00) AS "Zamówienia (wartość netto PLN)",
    coalesce(inv.liczba_faktur, 0) AS "Faktury (liczba)",
    coalesce(inv.wartosc_faktur_pln, 0.00) AS "Faktury (wartość netto PLN)"
FROM all_keys k
LEFT JOIN res_users u ON u.id = k.user_id
LEFT JOIN res_partner p ON p.id = u.partner_id
LEFT JOIN offers off ON off.user_id = k.user_id AND off.miesiac = k.miesiac
LEFT JOIN orders ord ON ord.user_id = k.user_id AND ord.miesiac = k.miesiac
LEFT JOIN invoices inv ON inv.user_id = k.user_id AND inv.miesiac = k.miesiac
ORDER BY k.miesiac ASC, "Zamówienia (wartość netto PLN)" DESC, "Handlowiec" ASC;
""".strip()


def publish_report():
    client = MetabaseClient()
    client.authenticate()

    personal_collection_id = client.get_personal_collection_id()
    logger.info("Personal Collection ID: %s", personal_collection_id)

    # Visualization settings with currency formatting
    vis_settings = {
        "column_settings": {
            '["name","Oferty (wartość netto PLN)"]': {
                "number_style": "currency",
                "currency": "PLN",
                "currency_style": "symbol",
                "decimals": 2,
            },
            '["name","Zamówienia (wartość netto PLN)"]': {
                "number_style": "currency",
                "currency": "PLN",
                "currency_style": "symbol",
                "decimals": 2,
            },
            '["name","Faktury (wartość netto PLN)"]': {
                "number_style": "currency",
                "currency": "PLN",
                "currency_style": "symbol",
                "decimals": 2,
            },
            '["name","Oferty (liczba)"]': {
                "number_style": "decimal",
                "decimals": 0,
            },
            '["name","Zamówienia (liczba)"]': {
                "number_style": "decimal",
                "decimals": 0,
            },
            '["name","Faktury (liczba)"]': {
                "number_style": "decimal",
                "decimals": 0,
            },
        }
    }

    card_name = "Wagi Samochodowe — Miesięczne zestawienie handlowców (2026)"
    card_desc = (
        "Zestawienie miesięczne per handlowiec dla zespołu sprzedaży 'Wagi Samochodowe' (ID 11, MIW Group Sp. k.): "
        "oferty (draft/sent), zamówienia potwierdzone (sale/done) oraz wystawione faktury sprzedaży (posted out_invoice) "
        "z przeliczeniem na walutę bazową PLN."
    )

    logger.info("Tworzenie raportu / pytania w Metabase...")
    card = client.create_card(
        name=card_name,
        sql_query=WAGI_REPORT_SQL,
        collection_id=personal_collection_id,
        display="table",
        description=card_desc,
        visualization_settings=vis_settings,
    )

    card_id = card.get("id")
    web_url = card.get("web_url")
    print("\n" + "=" * 70)
    print("✅ RAPORT METABASE ZOSTAŁ POMYŚLNIE OPULIKOWANY!")
    print(f"📌 Nazwa raportu: {card_name}")
    print(f"🆔 ID Karty: {card_id}")
    print(f"📂 Kolekcja: Personal Collection (ID {personal_collection_id})")
    print(f"🔗 Bezpośredni link URL: {web_url}")
    print("=" * 70 + "\n")
    return card


if __name__ == "__main__":
    publish_report()
