"""EDA по датасету Russia Real Estate 2018-2021. Цель — отфильтровать СПб и оценить качество."""

import pandas as pd
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data" / "raw" / "kaggle" / "all_v2.csv"
OUT = ROOT / "data" / "processed"
OUT.mkdir(parents=True, exist_ok=True)

print("=" * 60)
print("ЗАГРУЗКА")
print("=" * 60)
df = pd.read_csv(RAW, parse_dates=["date"])
print(f"Всего строк: {len(df):,}")
print(f"Колонки: {list(df.columns)}")
print(f"Период: {df['date'].min()} — {df['date'].max()}")

print("\n" + "=" * 60)
print("РЕГИОНЫ (топ-15 по количеству объявлений)")
print("=" * 60)
print(df["region"].value_counts().head(15))

print("\n" + "=" * 60)
print("ГЕОГРАФИЯ СПб — кандидаты по координатам")
print("=" * 60)
# СПб: 59.8-60.1 N, 30.0-30.6 E (приблизительно)
spb_geo_mask = (df["geo_lat"].between(59.7, 60.2)) & (df["geo_lon"].between(29.5, 31.0))
print(f"По координатам СПб: {spb_geo_mask.sum():,}")
print("Регионы внутри этой геозоны:")
print(df.loc[spb_geo_mask, "region"].value_counts().head(10))

print("\n" + "=" * 60)
print("ФИЛЬТРАЦИЯ ПО РЕГИОНУ 2661 (предполагаемый код СПб)")
print("=" * 60)
spb = df[df["region"] == 2661].copy()
print(f"Записей: {len(spb):,}")
print(f"Период: {spb['date'].min()} — {spb['date'].max()}")
print(f"Координатные границы: lat [{spb['geo_lat'].min():.3f}; {spb['geo_lat'].max():.3f}], lon [{spb['geo_lon'].min():.3f}; {spb['geo_lon'].max():.3f}]")

print("\n" + "=" * 60)
print("КАЧЕСТВО ДАННЫХ (СПб-срез)")
print("=" * 60)
print("Пропуски:")
print(spb.isna().sum())
print(f"\nДубликаты по всем колонкам: {spb.duplicated().sum():,}")
print(f"\nСтатистика по числовым полям:")
print(spb[["price", "area", "rooms", "level", "levels", "kitchen_area"]].describe().round(1))

print("\n" + "=" * 60)
print("ВЫБРОСЫ")
print("=" * 60)
print(f"Цена < 500k: {(spb['price'] < 500_000).sum():,}")
print(f"Цена > 100M: {(spb['price'] > 100_000_000).sum():,}")
print(f"Площадь < 10 м²: {(spb['area'] < 10).sum():,}")
print(f"Площадь > 500 м²: {(spb['area'] > 500).sum():,}")
print(f"Комнат > 10: {(spb['rooms'] > 10).sum():,}")
print(f"object_type values: {sorted(spb['object_type'].dropna().unique())}")
print(f"building_type values: {sorted(spb['building_type'].dropna().unique())}")

print("\n" + "=" * 60)
print("ОЧИСТКА: убираем выбросы")
print("=" * 60)
clean = spb[
    (spb["price"].between(500_000, 100_000_000))
    & (spb["area"].between(10, 500))
    & (spb["rooms"].between(0, 10))
].copy()
clean["price_per_sqm"] = (clean["price"] / clean["area"]).round(0)
print(f"После очистки: {len(clean):,} (было {len(spb):,}, потеря {(1-len(clean)/len(spb))*100:.1f}%)")
print(f"\nЦена за м² (₽):")
print(clean["price_per_sqm"].describe().round(0))

print("\n" + "=" * 60)
print("ДИНАМИКА ПО МЕСЯЦАМ")
print("=" * 60)
clean["year_month"] = clean["date"].dt.to_period("M")
monthly = clean.groupby("year_month").agg(
    listings=("price", "count"),
    avg_price_per_sqm=("price_per_sqm", "mean"),
    median_price_per_sqm=("price_per_sqm", "median"),
).round(0)
print(monthly.to_string())

print("\n" + "=" * 60)
print("СОХРАНЕНИЕ СПб-СРЕЗА")
print("=" * 60)
out_csv = OUT / "spb_listings_clean.csv"
clean.to_csv(out_csv, index=False)
print(f"→ {out_csv} ({out_csv.stat().st_size / 1024 / 1024:.1f} МБ)")
