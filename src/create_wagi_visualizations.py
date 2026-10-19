"""
Utworzenie i publikacja zestawu wizualizacji oraz dedykowanego Dashboardu
w Personal Collection Tomasza w Metabase.
AGENTS-OS v6.5 Swarm Edition.
Strictly Read-Only (Odoo DB) + Zero Alert Flood.
"""

import json
import logging
from pathlib import Path
import sys

# Ensure src/ is on sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent))

from metabase_client import MetabaseClient

logging.basicConfig(level=logging.INFO, format="[%(asctime)s] [%(levelname)s] %(message)s")
logger = logging.getLogger("CreateWagiVisualizations")

# 1. SQL: KPI Suma Zamówień
SQL_KPI_ORDERS_PLN = """
SELECT 
    round(sum(CASE WHEN coalesce(currency_rate, 0) > 0 THEN amount_untaxed / currency_rate ELSE amount_untaxed END)::numeric, 2) AS "Wartość zamówień (PLN)"
FROM sale_order
WHERE team_id = 11 AND company_id = 1 AND state IN ('sale', 'done')
  AND date_order >= '2026-01-01' AND date_order < '2027-01-01';
""".strip()

# 2. SQL: KPI Suma Faktur
SQL_KPI_INVOICES_PLN = """
SELECT 
    round(sum(amount_untaxed_signed)::numeric, 2) AS "Wartość faktur (PLN)"
FROM account_move
WHERE team_id = 11 AND company_id = 1 AND state = 'posted' AND move_type = 'out_invoice'
  AND invoice_date >= '2026-01-01' AND invoice_date < '2027-01-01';
""".strip()

# 3. SQL: KPI Liczba Zamówień
SQL_KPI_ORDERS_COUNT = """
SELECT 
    count(*) AS "Liczba potwierdzonych zamówień"
FROM sale_order
WHERE team_id = 11 AND company_id = 1 AND state IN ('sale', 'done')
  AND date_order >= '2026-01-01' AND date_order < '2027-01-01';
""".strip()

# 4. SQL: Bar Chart Sprzedaż per Handlowiec miesięcznie
SQL_BAR_SALES_PER_REP = """
SELECT 
    to_char(so.date_order, 'YYYY-MM') AS "Miesiąc",
    coalesce(p.name, 'Nieprzypisany') AS "Handlowiec",
    round(sum(CASE WHEN coalesce(so.currency_rate, 0) > 0 THEN so.amount_untaxed / so.currency_rate ELSE so.amount_untaxed END)::numeric, 2) AS "Wartość zamówień (PLN)"
FROM sale_order so
LEFT JOIN res_users u ON u.id = so.user_id
LEFT JOIN res_partner p ON p.id = u.partner_id
WHERE so.team_id = 11 
  AND so.company_id = 1
  AND so.state IN ('sale', 'done')
  AND so.date_order >= '2026-01-01' AND so.date_order < '2027-01-01'
GROUP BY to_char(so.date_order, 'YYYY-MM'), coalesce(p.name, 'Nieprzypisany')
ORDER BY "Miesiąc" ASC, "Wartość zamówień (PLN)" DESC;
""".strip()

# 5. SQL: Pie Chart Udział w Sprzedaży
SQL_PIE_SALES_SHARE = """
SELECT 
    coalesce(p.name, 'Nieprzypisany') AS "Handlowiec",
    round(sum(CASE WHEN coalesce(so.currency_rate, 0) > 0 THEN so.amount_untaxed / so.currency_rate ELSE so.amount_untaxed END)::numeric, 2) AS "Wartość zamówień (PLN)"
FROM sale_order so
LEFT JOIN res_users u ON u.id = so.user_id
LEFT JOIN res_partner p ON p.id = u.partner_id
WHERE so.team_id = 11 
  AND so.company_id = 1
  AND so.state IN ('sale', 'done')
  AND so.date_order >= '2026-01-01' AND so.date_order < '2027-01-01'
GROUP BY coalesce(p.name, 'Nieprzypisany')
ORDER BY "Wartość zamówień (PLN)" DESC;
""".strip()

# 6. SQL: Line Chart Trend Lejka
SQL_LINE_FUNNEL_TREND = """
WITH m_offers AS (
    SELECT to_char(date_order, 'YYYY-MM') AS miesiac,
           round(sum(CASE WHEN coalesce(currency_rate, 0) > 0 THEN amount_untaxed / currency_rate ELSE amount_untaxed END)::numeric, 2) AS oferty_pln
    FROM sale_order
    WHERE team_id = 11 AND company_id = 1 AND state IN ('draft', 'sent')
      AND date_order >= '2026-01-01' AND date_order < '2027-01-01'
    GROUP BY to_char(date_order, 'YYYY-MM')
),
m_orders AS (
    SELECT to_char(date_order, 'YYYY-MM') AS miesiac,
           round(sum(CASE WHEN coalesce(currency_rate, 0) > 0 THEN amount_untaxed / currency_rate ELSE amount_untaxed END)::numeric, 2) AS zamowienia_pln
    FROM sale_order
    WHERE team_id = 11 AND company_id = 1 AND state IN ('sale', 'done')
      AND date_order >= '2026-01-01' AND date_order < '2027-01-01'
    GROUP BY to_char(date_order, 'YYYY-MM')
),
m_invoices AS (
    SELECT to_char(invoice_date, 'YYYY-MM') AS miesiac,
           round(sum(amount_untaxed_signed)::numeric, 2) AS faktury_pln
    FROM account_move
    WHERE team_id = 11 AND company_id = 1 AND state = 'posted' AND move_type = 'out_invoice'
      AND invoice_date >= '2026-01-01' AND invoice_date < '2027-01-01'
    GROUP BY to_char(invoice_date, 'YYYY-MM')
),
months AS (
    SELECT miesiac FROM m_offers UNION SELECT miesiac FROM m_orders UNION SELECT miesiac FROM m_invoices
)
SELECT 
    m.miesiac AS "Miesiąc",
    coalesce(o.oferty_pln, 0) AS "Wartość ofert (PLN)",
    coalesce(ord.zamowienia_pln, 0) AS "Wartość zamówień (PLN)",
    coalesce(inv.faktury_pln, 0) AS "Wartość faktur (PLN)"
FROM months m
LEFT JOIN m_offers o ON o.miesiac = m.miesiac
LEFT JOIN m_orders ord ON ord.miesiac = m.miesiac
LEFT JOIN m_invoices inv ON inv.miesiac = m.miesiac
ORDER BY m.miesiac ASC;
""".strip()


def build_wagi_visualizations():
    client = MetabaseClient()
    client.authenticate()

    p_col = client.get_personal_collection_id()
    logger.info("Personal Collection ID: %s", p_col)

    created_cards = {}

    # 1. Karta KPI: Suma Zamówień
    logger.info("Tworzenie karty KPI: Suma Zamówień 2026...")
    card_kpi_orders = client.create_card(
        name="Wagi Samochodowe — Suma Zamówień 2026 (PLN)",
        sql_query=SQL_KPI_ORDERS_PLN,
        collection_id=p_col,
        display="scalar",
        description="Łączna wartość netto potwierdzonych zamówień (PLN) zespołu Wagi Samochodowe w 2026 r.",
        visualization_settings={
            "column_settings": {
                '["name","Wartość zamówień (PLN)"]': {
                    "number_style": "currency",
                    "currency": "PLN",
                    "currency_style": "symbol",
                    "decimals": 2,
                }
            }
        },
    )
    created_cards["kpi_orders"] = card_kpi_orders["id"]

    # 2. Karta KPI: Suma Faktur
    logger.info("Tworzenie karty KPI: Suma Faktur 2026...")
    card_kpi_inv = client.create_card(
        name="Wagi Samochodowe — Suma Faktur 2026 (PLN)",
        sql_query=SQL_KPI_INVOICES_PLN,
        collection_id=p_col,
        display="scalar",
        description="Łączna wartość netto wystawionych faktur sprzedaży (PLN) zespołu Wagi Samochodowe w 2026 r.",
        visualization_settings={
            "column_settings": {
                '["name","Wartość faktur (PLN)"]': {
                    "number_style": "currency",
                    "currency": "PLN",
                    "currency_style": "symbol",
                    "decimals": 2,
                }
            }
        },
    )
    created_cards["kpi_inv"] = card_kpi_inv["id"]

    # 3. Karta KPI: Liczba Zamówień
    logger.info("Tworzenie karty KPI: Liczba Zamówień 2026...")
    card_kpi_count = client.create_card(
        name="Wagi Samochodowe — Liczba Zamówień 2026",
        sql_query=SQL_KPI_ORDERS_COUNT,
        collection_id=p_col,
        display="scalar",
        description="Łączna liczba potwierdzonych zamówień sprzedaży zespołu Wagi Samochodowe w 2026 r.",
        visualization_settings={
            "column_settings": {
                '["name","Liczba potwierdzonych zamówień"]': {
                    "number_style": "decimal",
                    "decimals": 0,
                }
            }
        },
    )
    created_cards["kpi_count"] = card_kpi_count["id"]

    # 4. Karta Wykres Słupkowy: Sprzedaż per Handlowiec miesięcznie
    logger.info("Tworzenie wykresu słupkowego: Sprzedaż per Handlowiec...")
    card_bar = client.create_card(
        name="Wagi Samochodowe — Sprzedaż per Handlowiec (Miesięcznie 2026)",
        sql_query=SQL_BAR_SALES_PER_REP,
        collection_id=p_col,
        display="bar",
        description="Miesięczna wartość potwierdzonych zamówień sprzedaży w podziale na handlowców (PLN, 2026).",
        visualization_settings={
            "graph.dimensions": ["Miesiąc", "Handlowiec"],
            "graph.metrics": ["Wartość zamówień (PLN)"],
            "stackable.stack_type": "stacked",
            "column_settings": {
                '["name","Wartość zamówień (PLN)"]': {
                    "number_style": "currency",
                    "currency": "PLN",
                    "decimals": 0,
                }
            },
        },
    )
    created_cards["bar_rep"] = card_bar["id"]

    # 5. Karta Wykres Kołowy: Udział Handlowców
    logger.info("Tworzenie wykresu kołowego: Udział Handlowców...")
    card_pie = client.create_card(
        name="Wagi Samochodowe — Udział Handlowców w Sprzedaży (2026)",
        sql_query=SQL_PIE_SALES_SHARE,
        collection_id=p_col,
        display="pie",
        description="Procentowy i wartościowy udział poszczególnych handlowców w całkowitych zamówieniach 2026.",
        visualization_settings={
            "pie.dimension": "Handlowiec",
            "pie.metric": "Wartość zamówień (PLN)",
            "pie.show_legend": True,
            "pie.show_total": True,
            "column_settings": {
                '["name","Wartość zamówień (PLN)"]': {
                    "number_style": "currency",
                    "currency": "PLN",
                    "decimals": 0,
                }
            },
        },
    )
    created_cards["pie_share"] = card_pie["id"]

    # 6. Karta Wykres Liniowy: Trend Lejka
    logger.info("Tworzenie wykresu liniowego: Trend Lejka...")
    card_line = client.create_card(
        name="Wagi Samochodowe — Trend Lejka: Oferty vs Zamówienia vs Faktury (2026)",
        sql_query=SQL_LINE_FUNNEL_TREND,
        collection_id=p_col,
        display="line",
        description="Miesięczny trend porównawczy: wartość wygenerowanych ofert, potwierdzonych zamówień i wystawionych faktur (PLN).",
        visualization_settings={
            "graph.dimensions": ["Miesiąc"],
            "graph.metrics": [
                "Wartość ofert (PLN)",
                "Wartość zamówień (PLN)",
                "Wartość faktur (PLN)",
            ],
            "column_settings": {
                '["name","Wartość ofert (PLN)"]': {
                    "number_style": "currency",
                    "currency": "PLN",
                    "decimals": 0,
                },
                '["name","Wartość zamówień (PLN)"]': {
                    "number_style": "currency",
                    "currency": "PLN",
                    "decimals": 0,
                },
                '["name","Wartość faktur (PLN)"]': {
                    "number_style": "currency",
                    "currency": "PLN",
                    "decimals": 0,
                },
            },
        },
    )
    created_cards["line_trend"] = card_line["id"]

    # Karta Główna Tabela (ID 725)
    table_card_id = 725
    created_cards["table_detail"] = table_card_id

    # 7. Utworzenie dedykowanego Dashboardu
    logger.info("Tworzenie dedykowanego pulpitu (Dashboard) w Metabase...")
    dash_desc = (
        "Kompleksowy pulpit analityczny sprzedaży zespołu 'Wagi Samochodowe' (ID 11, MIW Group Sp. k.): "
        "kluczowe wskaźniki KPI, dynamika miesięczna per handlowiec, struktura udziału w przychodach oraz zestawienie szczegółowe."
    )
    dashboard = client.create_dashboard(
        name="Pulpit Sprzedaży — Wagi Samochodowe (2026)",
        description=dash_desc,
        collection_id=p_col,
    )
    dash_id = dashboard["id"]
    dash_url = dashboard["web_url"]
    logger.info("Utworzono pulpit ID %s: %s", dash_id, dash_url)

    # 8. Układ siatki kart na pulpicie (Siatka 24 kolumn)
    # Row 0: KPI Zamówienia (0..8), KPI Faktury (8..16), KPI Liczba (16..24), wys. 4
    # Row 4: Słupkowy (0..15), Kołowy (15..24), wys. 9
    # Row 13: Liniowy Lejek (0..24), wys. 9
    # Row 22: Tabela Szczegółowa (0..24), wys. 11
    cards_layout = [
        {
            "card_id": created_cards["kpi_orders"],
            "row": 0,
            "col": 0,
            "size_x": 8,
            "size_y": 4,
        },
        {
            "card_id": created_cards["kpi_inv"],
            "row": 0,
            "col": 8,
            "size_x": 8,
            "size_y": 4,
        },
        {
            "card_id": created_cards["kpi_count"],
            "row": 0,
            "col": 16,
            "size_x": 8,
            "size_y": 4,
        },
        {
            "card_id": created_cards["bar_rep"],
            "row": 4,
            "col": 0,
            "size_x": 15,
            "size_y": 9,
        },
        {
            "card_id": created_cards["pie_share"],
            "row": 4,
            "col": 15,
            "size_x": 9,
            "size_y": 9,
        },
        {
            "card_id": created_cards["line_trend"],
            "row": 13,
            "col": 0,
            "size_x": 24,
            "size_y": 9,
        },
        {
            "card_id": created_cards["table_detail"],
            "row": 22,
            "col": 0,
            "size_x": 24,
            "size_y": 11,
        },
    ]

    logger.info("Rozmieszczanie kart na siatce pulpitu...")
    client.set_dashboard_cards(dash_id, cards_layout)

    print("\n" + "=" * 75)
    print("🚀 SUKCES: PAKIET WIZUALIZACJI I PULPIT METABASE OPULIKOWANE!")
    print(f"📊 Nazwa pulpitu: Pulpit Sprzedaży — Wagi Samochodowe (2026)")
    print(f"🆔 ID Pulpitu: {dash_id}")
    print(f"🔗 Bezpośredni link do Pulpitu: {dash_url}")
    print(f"📂 Kolekcja: Personal Collection (ID {p_col})")
    print("\nUtworzone wizualizacje:")
    print(f"  • [KPI] Wartość zamówień (PLN): {client.base_url}/question/{created_cards['kpi_orders']}")
    print(f"  • [KPI] Wartość faktur (PLN):   {client.base_url}/question/{created_cards['kpi_inv']}")
    print(f"  • [KPI] Liczba zamówień:        {client.base_url}/question/{created_cards['kpi_count']}")
    print(f"  • [Bar] Sprzedaż per handlowiec:{client.base_url}/question/{created_cards['bar_rep']}")
    print(f"  • [Pie] Udział handlowców:      {client.base_url}/question/{created_cards['pie_share']}")
    print(f"  • [Line] Trend Lejka 2026:      {client.base_url}/question/{created_cards['line_trend']}")
    print(f"  • [Table] Tabela zestawienia:   {client.base_url}/question/{table_card_id}")
    print("=" * 75 + "\n")

    return {
        "dashboard_id": dash_id,
        "dashboard_url": dash_url,
        "cards": created_cards,
    }


if __name__ == "__main__":
    build_wagi_visualizations()
