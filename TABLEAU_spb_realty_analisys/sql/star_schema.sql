-- ============================================================================
-- Star schema: рынок жилья Санкт-Петербурга 2018–2021
-- Источник: Kaggle Russia Real Estate 2018–2021 (mrdaniilak)
-- ============================================================================

CREATE SCHEMA IF NOT EXISTS realty;

-- ---------------------------------------------------------------------------
-- DIMENSIONS
-- ---------------------------------------------------------------------------

DROP TABLE IF EXISTS realty.dim_date CASCADE;
CREATE TABLE realty.dim_date (
    date_id      DATE PRIMARY KEY,
    year         SMALLINT NOT NULL,
    quarter      VARCHAR(7) NOT NULL,   -- '2020Q1'
    year_month   VARCHAR(7) NOT NULL,   -- '2020-03'
    month_num    SMALLINT NOT NULL,
    week_of_year SMALLINT NOT NULL,
    is_covid     BOOLEAN  NOT NULL      -- 2020-03-01..2021-05-31
);

DROP TABLE IF EXISTS realty.dim_district CASCADE;
CREATE TABLE realty.dim_district (
    district_id   SMALLINT PRIMARY KEY,
    district_name VARCHAR(64) NOT NULL,
    macro_zone    VARCHAR(32) NOT NULL,  -- Центр / Север / Юг / Восток / Юго-запад / Пригород ...
    centroid_lat  NUMERIC(8, 5) NOT NULL,
    centroid_lon  NUMERIC(8, 5) NOT NULL
);

DROP TABLE IF EXISTS realty.dim_object_type CASCADE;
CREATE TABLE realty.dim_object_type (
    object_type        SMALLINT PRIMARY KEY,  -- 1 / 11
    object_type_label  VARCHAR(32) NOT NULL   -- 'Новостройка' / 'Вторичка'
);

DROP TABLE IF EXISTS realty.dim_building CASCADE;
CREATE TABLE realty.dim_building (
    building_type        SMALLINT PRIMARY KEY,
    building_type_label  VARCHAR(32) NOT NULL  -- Панель / Монолит / Кирпич / Блок / Дерево / Неизвестно
);

-- ---------------------------------------------------------------------------
-- FACT
-- ---------------------------------------------------------------------------

DROP TABLE IF EXISTS realty.fact_listings CASCADE;
CREATE TABLE realty.fact_listings (
    listing_id      BIGSERIAL PRIMARY KEY,
    date_id         DATE        NOT NULL REFERENCES realty.dim_date(date_id),
    district_id     SMALLINT    NOT NULL REFERENCES realty.dim_district(district_id),
    object_type     SMALLINT    NOT NULL REFERENCES realty.dim_object_type(object_type),
    building_type   SMALLINT             REFERENCES realty.dim_building(building_type),
    rooms           SMALLINT,
    area            NUMERIC(7, 2)  NOT NULL,
    kitchen_area    NUMERIC(7, 2),
    level_num       SMALLINT,
    levels_total    SMALLINT,
    price           NUMERIC(14, 2) NOT NULL,
    price_per_sqm   NUMERIC(12, 2) NOT NULL,
    geo_lat         NUMERIC(8, 5) NOT NULL,
    geo_lon         NUMERIC(8, 5) NOT NULL
);

CREATE INDEX idx_fact_listings_date     ON realty.fact_listings(date_id);
CREATE INDEX idx_fact_listings_district ON realty.fact_listings(district_id);
CREATE INDEX idx_fact_listings_type     ON realty.fact_listings(object_type);

-- ---------------------------------------------------------------------------
-- MART VIEWS (для Tableau / Power BI)
-- ---------------------------------------------------------------------------

CREATE OR REPLACE VIEW realty.v_monthly_dynamics AS
SELECT
    d.year_month,
    d.year,
    d.quarter,
    d.is_covid,
    ot.object_type_label,
    COUNT(*)                              AS listings,
    AVG(f.price_per_sqm)::INT             AS avg_price_per_sqm,
    PERCENTILE_CONT(0.5) WITHIN GROUP
        (ORDER BY f.price_per_sqm)::INT   AS median_price_per_sqm,
    SUM(f.price) / 1e9                    AS total_volume_bn_rub
FROM realty.fact_listings f
JOIN realty.dim_date         d  ON d.date_id     = f.date_id
JOIN realty.dim_object_type  ot ON ot.object_type = f.object_type
GROUP BY d.year_month, d.year, d.quarter, d.is_covid, ot.object_type_label;

CREATE OR REPLACE VIEW realty.v_district_yearly AS
SELECT
    dd.district_id,
    dd.district_name,
    dd.macro_zone,
    dd.centroid_lat,
    dd.centroid_lon,
    d.year,
    COUNT(*)                              AS listings,
    AVG(f.price_per_sqm)::INT             AS avg_price_per_sqm,
    PERCENTILE_CONT(0.5) WITHIN GROUP
        (ORDER BY f.price_per_sqm)::INT   AS median_price_per_sqm
FROM realty.fact_listings f
JOIN realty.dim_district dd ON dd.district_id = f.district_id
JOIN realty.dim_date     d  ON d.date_id      = f.date_id
GROUP BY dd.district_id, dd.district_name, dd.macro_zone,
         dd.centroid_lat, dd.centroid_lon, d.year;

-- ---------------------------------------------------------------------------
-- KPI: COVID-эффект (главный показатель главного экрана)
-- ---------------------------------------------------------------------------

CREATE OR REPLACE VIEW realty.v_covid_impact_by_district AS
WITH pre AS (
    SELECT f.district_id,
           PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY f.price_per_sqm)::INT AS pre_median
    FROM realty.fact_listings f
    WHERE f.date_id BETWEEN '2019-09-01' AND '2020-02-29'
    GROUP BY f.district_id
),
post AS (
    SELECT f.district_id,
           PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY f.price_per_sqm)::INT AS post_median
    FROM realty.fact_listings f
    WHERE f.date_id BETWEEN '2020-12-01' AND '2021-04-30'
    GROUP BY f.district_id
)
SELECT
    dd.district_name,
    dd.macro_zone,
    pre.pre_median,
    post.post_median,
    ROUND(((post.post_median - pre.pre_median)::NUMERIC
            / pre.pre_median) * 100, 1) AS change_pct
FROM pre
JOIN post ON post.district_id = pre.district_id
JOIN realty.dim_district dd ON dd.district_id = pre.district_id
ORDER BY change_pct DESC;
