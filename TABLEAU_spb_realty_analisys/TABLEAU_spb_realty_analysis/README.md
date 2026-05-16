# Рынок жилья Санкт-Петербурга 2018–2021

> BI-дашборд: влияние COVID на рост цен на жилую недвижимость в Санкт-Петербурге. Динамика, география, структура — на открытых данных Kaggle.

**🔗 Tableau Public:** [Saint Petersburg Real Estate Market 2018–2021](https://public.tableau.com/app/profile/maks.novikov/viz/SaintPetersburgRealEstateMarket20182021/Dashboard)


**📸 Скриншоты:** [mnovikov-cv.tilda.ws](https://github.com/novikovmvn/portfolio_projects/petproject_spb_realty/screenshots)


---

## Выводы

| Сегмент | Медиана до COVID (09.19–02.20) | После (12.20–04.21) | Δ |
|---|---|---|---|
| Вторичка | 115 319 ₽/м² | 162 009 ₽/м² | **+40.5%** |
| Новостройки | 115 385 ₽/м² | 150 000 ₽/м² | **+30.0%** |

**Топ-5 районов по росту цен в COVID-период:**

| Район | До | После | Δ |
|---|---|---|---|
| Центральный | 143 087 | 250 432 | **+75.0%** |
| Курортный | 107 812 | 159 176 | +47.6% |
| Адмиралтейский | 139 198 | 200 073 | +43.7% |
| Приморский | 116 123 | 165 116 | +42.2% |
| Петродворцовый | 95 990 | 134 091 | +39.7% |

Центральные районы Петербурга — почти двойной рост цен за 18 месяцев.

---

## О проекте

Полный цикл BI-разработки на открытом Kaggle-датасете: загрузка → преобразование → моделирование «звезда» → агрегаты → публикация интерактивного дашборда. Стек повторяет коммерческие задачи: Python + PostgreSQL + Tableau.

Бизнес-вопросы дашборда:

1. Как менялась средняя цена за м² в СПб 2018–2021?
2. Как пандемия 2020 повлияла на рынок?
3. Как распределяются цены по 18 районам Петербурга?
4. Чем отличается новостройка от вторички по динамике?

---

## Объём и качество данных

- **5 477 007** объявлений по РФ → **461 820** по СПб (`region = 2661`)
- После очистки выбросов (IQR-фильтр по цене, площади, комнатам): **437 295** записей (потеря 5.3%)
- Период: 02.2018 – 05.2021, плотные данные с 09.2018
- 0 пропусков, 232 дубля — датасет промышленного качества

---

## Источник данных

[Russia Real Estate 2018–2021](https://www.kaggle.com/datasets/mrdaniilak/russia-real-estate-20182021) — 5 млн объявлений недвижимости по РФ с координатами.

---

## Структура репозитория

```
petproject_spb_realty/
├── README.md
├── data/
│   ├── raw/kaggle/              ← оригинал датасета (all_v2.csv, 390 МБ)
│   ├── processed/               ← SPb-срез после чистки
│   └── tableau/                 ← готовые CSV для Tableau Public
│       ├── fact_listings.csv    ← денормализованный факт (78 МБ)
│       ├── dim_district.csv     ← 18 районов с центроидами
│       ├── agg_monthly.csv      ← динамика месяц × тип объекта
│       ├── agg_district.csv     ← район × год
│       ├── kpi_covid_by_types.csv
│       └── kpi_covid_by_district.csv
├── notebooks/
│   ├── 01_eda.py                ← загрузка, фильтрация СПб, очистка
│   └── 02_districts_and_aggregates.py  ← маппинг районов, агрегаты
├── sql/
│   └── star_schema.sql          ← DDL модели «звезда» в PostgreSQL
├── docs/
│   └── methodology.md           ← гипотезы, источники, допущения
└── screenshots/
    └── main.png                 ← превью дашборда
```

---

## Модель данных («звезда»)

```
                  ┌──────────────────┐
                  │  fact_listings   │
                  │                  │
   dim_date ──────│ date_id          │── dim_district
                  │ district_id      │
   dim_object ────│ object_type      │── dim_building
                  │ building_type    │
                  │ area, rooms      │
                  │ price            │
                  │ price_per_sqm    │
                  │ geo (lat, lon)   │
                  └──────────────────┘
```

Полный DDL в [`sql/star_schema.sql`](sql/star_schema.sql) — включая 3 view-витрины для отчётности (`v_monthly_dynamics`, `v_district_yearly`, `v_covid_impact_by_district`).

---

## Воспроизведение

```bash
# 1. Скачать датасет с Kaggle и поместить в data/raw/kaggle/all_v2.csv

# 2. Создать venv и установить pandas, numpy
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

# 3. EDA и фильтрация СПб
python notebooks/01_eda.py

# 4. Маппинг районов и подготовка агрегатов для Tableau
python notebooks/02_districts_and_aggregates.py

# 5. Открыть data/tableau/fact_listings.csv в Tableau Public
```

---

## Стек

- **Python 3.14** — pandas, numpy (векторизованный nearest-centroid для маппинга районов)
- **PostgreSQL** — DDL «звезды» и аналитические view (демонстрационно)
- **Tableau Public** — визуализация
- **Git/GitHub** — версионирование

---

## Автор

**Максим Новиков** — BI-аналитик / BI-разработчик, Санкт-Петербург.

Портфолио: [mnovikov-cv.tilda.ws](https://mnovikov-cv.tilda.ws)

GitHub: [novikovmvn](https://github.com/novikovmvn)
