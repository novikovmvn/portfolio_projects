"""
Маппинг координат → район СПб (по ближайшему центроиду), построение моделей-измерений
и подготовка готовых к Tableau CSV-агрегатов.
"""

import numpy as np
import pandas as pd
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PROCESSED = ROOT / "data" / "processed"
TABLEAU = ROOT / "data" / "tableau"
TABLEAU.mkdir(exist_ok=True, parents=True)

# ---------- Справочник районов СПб (центроиды, ~приближённые) ----------
DISTRICTS = pd.DataFrame(
    [
        ("Адмиралтейский", 59.917, 30.300, "Центр"),
        ("Василеостровский", 59.940, 30.265, "Центр"),
        ("Выборгский", 60.050, 30.310, "Север"),
        ("Калининский", 60.020, 30.420, "Север"),
        ("Кировский", 59.880, 30.270, "Юг"),
        ("Колпинский", 59.740, 30.590, "Пригород"),
        ("Красногвардейский", 59.950, 30.460, "Северо-восток"),
        ("Красносельский", 59.840, 30.130, "Юго-запад"),
        ("Кронштадтский", 60.000, 29.770, "Пригород"),
        ("Курортный", 60.180, 29.960, "Пригород"),
        ("Московский", 59.860, 30.320, "Юг"),
        ("Невский", 59.880, 30.450, "Восток"),
        ("Петроградский", 59.960, 30.300, "Центр"),
        ("Петродворцовый", 59.880, 29.910, "Пригород"),
        ("Приморский", 60.000, 30.270, "Север"),
        ("Пушкинский", 59.720, 30.400, "Пригород"),
        ("Фрунзенский", 59.870, 30.380, "Юг"),
        ("Центральный", 59.930, 30.360, "Центр"),
    ],
    columns=["district_name", "centroid_lat", "centroid_lon", "macro_zone"],
)
DISTRICTS.index.name = "district_id"
DISTRICTS = DISTRICTS.reset_index()

# ---------- Справочники типов ----------
OBJECT_TYPES = pd.DataFrame(
    [(1, "Новостройка"), (11, "Вторичка")],
    columns=["object_type", "object_type_label"],
)

BUILDING_TYPES = pd.DataFrame(
    [
        (0, "Неизвестно"),
        (1, "Панельный"),
        (2, "Монолитный"),
        (3, "Кирпичный"),
        (4, "Блочный"),
        (5, "Деревянный"),
    ],
    columns=["building_type", "building_type_label"],
)

# ---------- Загрузка очищенного среза ----------
print("Загружаю SPb-срез...")
df = pd.read_csv(PROCESSED / "spb_listings_clean.csv", parse_dates=["date"])
print(f"  {len(df):,} строк")

# ---------- Маппинг координат → район (по ближайшему центроиду) ----------
print("Маппинг районов по ближайшему центроиду...")
lats = df["geo_lat"].to_numpy()
lons = df["geo_lon"].to_numpy()
c_lats = DISTRICTS["centroid_lat"].to_numpy()
c_lons = DISTRICTS["centroid_lon"].to_numpy()

# Векторизованное вычисление расстояний (без haversine — для СПб евклид достаточно)
# shape: (n_listings, n_districts)
dlat = lats[:, None] - c_lats[None, :]
dlon = (lons[:, None] - c_lons[None, :]) * np.cos(np.radians(c_lats[None, :]))
dist2 = dlat**2 + dlon**2
df["district_id"] = dist2.argmin(axis=1)

df = df.merge(DISTRICTS[["district_id", "district_name", "macro_zone"]], on="district_id")
df = df.merge(OBJECT_TYPES, on="object_type")
df = df.merge(BUILDING_TYPES, on="building_type", how="left")

# ---------- Деривативы для Tableau ----------
df["year_month"] = df["date"].dt.to_period("M").astype(str)
df["year"] = df["date"].dt.year
df["quarter"] = df["date"].dt.to_period("Q").astype(str)
df["covid_flag"] = df["date"].between("2020-03-01", "2021-05-31").map({True: "COVID-период", False: "До COVID"})

print(f"  Распределение по районам (топ-5):")
print(df["district_name"].value_counts().head().to_string())

# ---------- Денормализованный fact для Tableau ----------
fact_cols = [
    "date", "year", "quarter", "year_month", "covid_flag",
    "district_id", "district_name", "macro_zone",
    "object_type", "object_type_label",
    "building_type", "building_type_label",
    "rooms", "area", "level", "levels", "kitchen_area",
    "price", "price_per_sqm",
    "geo_lat", "geo_lon",
]
fact = df[fact_cols].copy()
fact.to_csv(TABLEAU / "fact_listings.csv", index=False)
print(f"→ fact_listings.csv ({(TABLEAU / 'fact_listings.csv').stat().st_size / 1024 / 1024:.1f} МБ)")

# ---------- Агрегат 1: динамика по месяцам × тип объекта ----------
agg_monthly = (
    fact.groupby(["year_month", "object_type_label"], as_index=False)
    .agg(
        listings=("price", "count"),
        avg_price_per_sqm=("price_per_sqm", "mean"),
        median_price_per_sqm=("price_per_sqm", "median"),
        total_volume_bn_rub=("price", lambda s: s.sum() / 1_000_000_000),
    )
    .round(0)
)
agg_monthly.to_csv(TABLEAU / "agg_monthly.csv", index=False)
print(f"→ agg_monthly.csv ({len(agg_monthly)} строк)")

# ---------- Агрегат 2: район × год ----------
agg_district = (
    fact.groupby(["district_name", "macro_zone", "year"], as_index=False)
    .agg(
        listings=("price", "count"),
        avg_price_per_sqm=("price_per_sqm", "mean"),
        median_price_per_sqm=("price_per_sqm", "median"),
    )
    .round(0)
)
agg_district = agg_district.merge(
    DISTRICTS[["district_name", "centroid_lat", "centroid_lon"]], on="district_name"
)
agg_district.to_csv(TABLEAU / "agg_district.csv", index=False)
print(f"→ agg_district.csv ({len(agg_district)} строк)")

# ---------- Агрегат 3: COVID-эффект — KPI для главного экрана ----------
def covid_kpi(group_col):
    pre = fact[fact["date"].between("2019-09-01", "2020-02-29")].groupby(group_col)["price_per_sqm"].median()
    post = fact[fact["date"].between("2020-12-01", "2021-04-30")].groupby(group_col)["price_per_sqm"].median()
    out = pd.DataFrame({"pre_covid_median": pre, "post_covid_median": post}).reset_index()
    out["change_pct"] = ((out["post_covid_median"] - out["pre_covid_median"]) / out["pre_covid_median"] * 100).round(1)
    return out

kpi_overall = covid_kpi("object_type_label")
kpi_overall.to_csv(TABLEAU / "kpi_covid_by_types.csv", index=False)
print(f"→ kpi_covid_by_types.csv ({len(kpi_overall)} строк)")
print(kpi_overall.to_string(index=False))

kpi_district = covid_kpi("district_name")
kpi_district.to_csv(TABLEAU / "kpi_covid_by_district.csv", index=False)
print(f"→ kpi_covid_by_district.csv ({len(kpi_district)} строк)")
print("\nТоп-5 районов по росту цен COVID-период:")
print(kpi_district.sort_values("change_pct", ascending=False).head().to_string(index=False))
print("\nДно-5 районов:")
print(kpi_district.sort_values("change_pct").head().to_string(index=False))

# ---------- Справочники ----------
DISTRICTS.to_csv(TABLEAU / "dim_district.csv", index=False)
print(f"→ dim_district.csv (18 строк)")

print("\nГотово. Файлы для Tableau:")
for f in sorted(TABLEAU.glob("*.csv")):
    print(f"  {f.name}: {f.stat().st_size / 1024:.1f} КБ")
