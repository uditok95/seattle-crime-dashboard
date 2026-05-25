-- ============================================================
-- SPD Crime Data Analysis — SQL Queries  (Updated: merged dataset)
-- Tool: DuckDB (pip install duckdb) — queries CSVs directly.
--
-- Run in Python:
--   import duckdb
--   con = duckdb.connect()
--   con.execute(open('spd_analysis.sql').read())
--
-- Or DuckDB CLI:  .read spd_analysis.sql
-- ============================================================

-- ── 1. MERGE BOTH CSVS INTO ONE VIEW ─────────────────────────────────────────
--   Supplement (Jan-May 2021 reported crimes) + Main dataset, dedup on Offense ID

CREATE OR REPLACE VIEW spd_raw AS
SELECT * FROM read_csv_auto(
    'D:\Foster ''27\Q3\IS\SPD_Crime_Data__2008-Present_20260518 (1).csv',
    header=true, quote='"'
)
UNION ALL
SELECT * FROM read_csv_auto(
    'D:\Foster ''27\Q3\IS\SPD_Crime_Data__2021tillMay.csv',
    header=true, quote='"'
);

-- Deduplicate on Offense ID, keep first occurrence (orig wins)
CREATE OR REPLACE VIEW spd_dedup AS
SELECT * FROM (
    SELECT *,
           ROW_NUMBER() OVER (PARTITION BY "Offense ID" ORDER BY "Report DateTime") AS rn
    FROM spd_raw
) t WHERE rn = 1;

-- ── 2. CLEAN + FEATURE-ENGINEER ───────────────────────────────────────────────
CREATE OR REPLACE VIEW spd AS
SELECT
    "Report Number"                                          AS report_number,
    strptime("Offense Date", '%Y %b %d %I:%M:%S %p')        AS offense_dt,
    "Offense Sub Category"                                   AS sub_category,
    "Offense Category"                                       AS offense_category,
    "NIBRS Offense Code Description"                         AS nibrs_desc,
    "NIBRS_offense_code"                                     AS nibrs_code,
    "Block Address"                                          AS block_address,
    "Neighborhood"                                           AS neighborhood,
    "Precinct"                                               AS precinct,
    "Beat"                                                   AS beat,
    TRY_CAST("Latitude"  AS DOUBLE)                          AS lat,
    TRY_CAST("Longitude" AS DOUBLE)                          AS lon,
    year(strptime("Offense Date", '%Y %b %d %I:%M:%S %p'))  AS yr,
    month(strptime("Offense Date", '%Y %b %d %I:%M:%S %p')) AS mo,
    dayofweek(strptime("Offense Date", '%Y %b %d %I:%M:%S %p')) AS dow,
    hour(strptime("Offense Date", '%Y %b %d %I:%M:%S %p'))  AS hr,
    CASE
        WHEN month(strptime("Offense Date",'%Y %b %d %I:%M:%S %p')) IN (12,1,2)  THEN 'Winter'
        WHEN month(strptime("Offense Date",'%Y %b %d %I:%M:%S %p')) IN (3,4,5)   THEN 'Spring'
        WHEN month(strptime("Offense Date",'%Y %b %d %I:%M:%S %p')) IN (6,7,8)   THEN 'Summer'
        ELSE 'Fall'
    END                                                      AS season
FROM spd_dedup
WHERE yr BETWEEN 2021 AND 2025;

-- ── DATA QUALITY CHECK ────────────────────────────────────────────────────────
SELECT
    COUNT(*)                                              AS total_rows,
    SUM(CASE WHEN offense_dt IS NULL    THEN 1 END)       AS null_dates,
    SUM(CASE WHEN neighborhood = ''
              OR neighborhood IS NULL  THEN 1 END)        AS null_neighborhood,
    SUM(CASE WHEN lat IS NULL
              OR lat = 0              THEN 1 END)         AS null_lat,
    COUNT(DISTINCT report_number)                         AS unique_reports,
    MIN(offense_dt)                                       AS earliest,
    MAX(offense_dt)                                       AS latest
FROM spd;

-- ============================================================
-- Q1 — Property crime trend (2021–2025, full year)
-- ============================================================

-- 1a. Count per year + YoY % change
SELECT
    yr,
    COUNT(*)                                              AS property_crimes,
    ROUND(100.0 * COUNT(*) /
          LAG(COUNT(*)) OVER (ORDER BY yr) - 100, 1)     AS yoy_pct_change
FROM spd
WHERE offense_category = 'PROPERTY CRIME'
GROUP BY yr
ORDER BY yr;

-- 1b. Year-over-year by crime type (pivot 2021-2025)
SELECT
    nibrs_desc,
    SUM(CASE WHEN yr=2021 THEN 1 ELSE 0 END)  AS "2021",
    SUM(CASE WHEN yr=2022 THEN 1 ELSE 0 END)  AS "2022",
    SUM(CASE WHEN yr=2023 THEN 1 ELSE 0 END)  AS "2023",
    SUM(CASE WHEN yr=2024 THEN 1 ELSE 0 END)  AS "2024",
    SUM(CASE WHEN yr=2025 THEN 1 ELSE 0 END)  AS "2025",
    ROUND(100.0*(SUM(CASE WHEN yr=2025 THEN 1 ELSE 0 END) -
                 SUM(CASE WHEN yr=2021 THEN 1 ELSE 0 END)) /
          NULLIF(SUM(CASE WHEN yr=2021 THEN 1 ELSE 0 END),0), 1) AS chg_21_to_25_pct
FROM spd
WHERE offense_category = 'PROPERTY CRIME'
GROUP BY nibrs_desc
HAVING SUM(1) > 200
ORDER BY "2022" DESC;

-- 1c. Top 15 neighborhoods by total property crime
SELECT
    neighborhood,
    SUM(CASE WHEN yr=2021 THEN 1 ELSE 0 END)  AS "2021",
    SUM(CASE WHEN yr=2022 THEN 1 ELSE 0 END)  AS "2022",
    SUM(CASE WHEN yr=2023 THEN 1 ELSE 0 END)  AS "2023",
    SUM(CASE WHEN yr=2024 THEN 1 ELSE 0 END)  AS "2024",
    SUM(CASE WHEN yr=2025 THEN 1 ELSE 0 END)  AS "2025",
    COUNT(*)                                   AS total_21_25,
    ROUND(100.0*(SUM(CASE WHEN yr=2025 THEN 1 ELSE 0 END) -
                 SUM(CASE WHEN yr=2021 THEN 1 ELSE 0 END)) /
          NULLIF(SUM(CASE WHEN yr=2021 THEN 1 ELSE 0 END),0), 1) AS chg_pct
FROM spd
WHERE offense_category = 'PROPERTY CRIME'
  AND neighborhood <> ''
GROUP BY neighborhood
ORDER BY total_21_25 DESC
LIMIT 15;

-- 1d. Slide stat box figures for Q1
SELECT
    SUM(CASE WHEN yr=2021 THEN 1 END)               AS crimes_2021,
    SUM(CASE WHEN yr=2022 THEN 1 END)               AS crimes_2022_peak,
    SUM(CASE WHEN yr=2025 THEN 1 END)               AS crimes_2025,
    ROUND(100.0*(SUM(CASE WHEN yr=2025 THEN 1 END) -
                 SUM(CASE WHEN yr=2022 THEN 1 END)) /
          SUM(CASE WHEN yr=2022 THEN 1 END), 1)     AS pct_chg_peak_to_2025,
    ROUND(100.0*(SUM(CASE WHEN yr=2025 THEN 1 END) -
                 SUM(CASE WHEN yr=2021 THEN 1 END)) /
          SUM(CASE WHEN yr=2021 THEN 1 END), 1)     AS pct_chg_2021_to_2025
FROM spd
WHERE offense_category = 'PROPERTY CRIME';

-- ============================================================
-- Q2 — Temporal fingerprint: Burglary vs TFMV
-- ============================================================

-- 2a. By hour of day
SELECT
    hr,
    SUM(CASE WHEN nibrs_desc='Burglary/Breaking & Entering' THEN 1 END) AS burglary,
    SUM(CASE WHEN nibrs_desc='Theft From Motor Vehicle'     THEN 1 END) AS tfmv
FROM spd
WHERE nibrs_desc IN ('Burglary/Breaking & Entering','Theft From Motor Vehicle')
GROUP BY hr
ORDER BY hr;

-- 2b. By day of week
SELECT
    CASE dow
        WHEN 0 THEN 'Sunday'    WHEN 1 THEN 'Monday'   WHEN 2 THEN 'Tuesday'
        WHEN 3 THEN 'Wednesday' WHEN 4 THEN 'Thursday' WHEN 5 THEN 'Friday'
        WHEN 6 THEN 'Saturday'
    END                                                         AS day_name,
    SUM(CASE WHEN nibrs_desc='Burglary/Breaking & Entering' THEN 1 END) AS burglary,
    SUM(CASE WHEN nibrs_desc='Theft From Motor Vehicle'     THEN 1 END) AS tfmv
FROM spd
WHERE nibrs_desc IN ('Burglary/Breaking & Entering','Theft From Motor Vehicle')
GROUP BY dow ORDER BY dow;

-- 2c. By season
SELECT
    season,
    SUM(CASE WHEN nibrs_desc='Burglary/Breaking & Entering' THEN 1 END) AS burglary,
    SUM(CASE WHEN nibrs_desc='Theft From Motor Vehicle'     THEN 1 END) AS tfmv
FROM spd
WHERE nibrs_desc IN ('Burglary/Breaking & Entering','Theft From Motor Vehicle')
GROUP BY season
ORDER BY burglary DESC;

-- 2d. Slide stat box figures for Q2
SELECT
    ROUND(100.0 * SUM(CASE WHEN nibrs_desc='Burglary/Breaking & Entering'
                             AND (hr < 6 OR hr >= 18) THEN 1 END) /
          NULLIF(SUM(CASE WHEN nibrs_desc='Burglary/Breaking & Entering' THEN 1 END),0), 1)
                                                AS burg_nighttime_pct,
    ROUND(100.0 * SUM(CASE WHEN nibrs_desc='Theft From Motor Vehicle'
                             AND (hr < 6 OR hr >= 18) THEN 1 END) /
          NULLIF(SUM(CASE WHEN nibrs_desc='Theft From Motor Vehicle'     THEN 1 END),0), 1)
                                                AS tfmv_evening_night_pct,
    (SELECT season FROM (
        SELECT season, COUNT(*) AS n FROM spd
        WHERE nibrs_desc IN ('Burglary/Breaking & Entering','Theft From Motor Vehicle')
        GROUP BY season ORDER BY n DESC LIMIT 1
    )) AS combined_peak_season
FROM spd
WHERE nibrs_desc IN ('Burglary/Breaking & Entering','Theft From Motor Vehicle');

-- ============================================================
-- Q3 — U-District per-capita vs city-wide  (pop constants below)
--      Seattle ~749,000 | U-District ~49,000
-- ============================================================

-- 3a. Annual counts
SELECT
    yr,
    SUM(CASE WHEN neighborhood LIKE '%UNIVERSITY%' THEN 1 ELSE 0 END) AS ud_crimes,
    COUNT(*)                                                            AS city_crimes,
    ROUND(100.0 *
          SUM(CASE WHEN neighborhood LIKE '%UNIVERSITY%' THEN 1 ELSE 0 END)
          / COUNT(*), 2)                                                AS ud_share_pct
FROM spd
WHERE offense_category = 'PROPERTY CRIME'
GROUP BY yr ORDER BY yr;

-- 3b. Per-100k rates
SELECT
    yr,
    ud, city,
    ROUND(ud   / 49000.0  * 100000, 0) AS ud_per_100k,
    ROUND(city / 749000.0 * 100000, 0) AS city_per_100k,
    ROUND((ud/49000.0) / (city/749000.0), 2) AS rate_ratio
FROM (
    SELECT yr,
           SUM(CASE WHEN neighborhood LIKE '%UNIVERSITY%' THEN 1 END) AS ud,
           COUNT(*) AS city
    FROM spd WHERE offense_category = 'PROPERTY CRIME'
    GROUP BY yr
) ORDER BY yr;

-- 3c. U-District top crime types vs city mix
SELECT
    nibrs_desc,
    SUM(CASE WHEN neighborhood LIKE '%UNIVERSITY%' THEN 1 ELSE 0 END)  AS ud_count,
    ROUND(100.0*SUM(CASE WHEN neighborhood LIKE '%UNIVERSITY%' THEN 1 ELSE 0 END) /
          SUM(SUM(CASE WHEN neighborhood LIKE '%UNIVERSITY%' THEN 1 ELSE 0 END))
          OVER (), 1)                                                   AS ud_pct,
    COUNT(*)                                                            AS city_count,
    ROUND(100.0*COUNT(*) / SUM(COUNT(*)) OVER (), 1)                    AS city_pct
FROM spd
WHERE offense_category = 'PROPERTY CRIME'
GROUP BY nibrs_desc
HAVING SUM(1) > 100
ORDER BY ud_count DESC;

-- ============================================================
-- Q4 — Dense/Urban (apartment-heavy) vs Residential (house-heavy)
-- ============================================================

-- 4a. Crime mix per area type
SELECT
    area_type,
    nibrs_desc,
    cnt,
    ROUND(100.0 * cnt / SUM(cnt) OVER (PARTITION BY area_type), 1) AS pct
FROM (
    SELECT
        CASE
            WHEN neighborhood IN (
                'CAPITOL HILL','FIRST HILL','BELLTOWN',
                'SLU/CASCADE','DOWNTOWN COMMERCIAL','PIONEER SQUARE'
            ) THEN 'Dense/Urban'
            WHEN neighborhood IN (
                'QUEEN ANNE','MAGNOLIA','BALLARD SOUTH','BALLARD NORTH',
                'WALLINGFORD','GREENWOOD','FREMONT','MADRONA/LESCHI'
            ) THEN 'Residential'
        END AS area_type,
        nibrs_desc,
        COUNT(*) AS cnt
    FROM spd WHERE offense_category = 'PROPERTY CRIME'
    GROUP BY area_type, nibrs_desc
) WHERE area_type IS NOT NULL
ORDER BY area_type, cnt DESC;

-- 4b. Key ratios per area type
SELECT
    area_type,
    SUM(CASE WHEN nibrs_desc='Burglary/Breaking & Entering' THEN 1 END) AS burglary,
    SUM(CASE WHEN nibrs_desc='Theft From Motor Vehicle'     THEN 1 END) AS tfmv,
    SUM(CASE WHEN nibrs_desc='Motor Vehicle Theft'          THEN 1 END) AS mv_theft,
    SUM(CASE WHEN nibrs_desc='Shoplifting'                  THEN 1 END) AS shoplifting,
    COUNT(*) AS total,
    ROUND(100.0*SUM(CASE WHEN nibrs_desc='Burglary/Breaking & Entering' THEN 1 END)/COUNT(*),1) AS burg_pct,
    ROUND(100.0*SUM(CASE WHEN nibrs_desc='Motor Vehicle Theft'          THEN 1 END)/COUNT(*),1) AS mvt_pct,
    ROUND(100.0*SUM(CASE WHEN nibrs_desc='Shoplifting'                  THEN 1 END)/COUNT(*),1) AS shop_pct
FROM (
    SELECT nibrs_desc,
        CASE
            WHEN neighborhood IN ('CAPITOL HILL','FIRST HILL','BELLTOWN',
                                  'SLU/CASCADE','DOWNTOWN COMMERCIAL','PIONEER SQUARE')
                THEN 'Dense/Urban'
            WHEN neighborhood IN ('QUEEN ANNE','MAGNOLIA','BALLARD SOUTH','BALLARD NORTH',
                                  'WALLINGFORD','GREENWOOD','FREMONT','MADRONA/LESCHI')
                THEN 'Residential'
        END AS area_type
    FROM spd WHERE offense_category = 'PROPERTY CRIME'
) WHERE area_type IS NOT NULL
GROUP BY area_type;

-- 4c. Year-over-year per area type
SELECT
    yr,
    SUM(CASE WHEN neighborhood IN('CAPITOL HILL','FIRST HILL','BELLTOWN',
        'SLU/CASCADE','DOWNTOWN COMMERCIAL','PIONEER SQUARE') THEN 1 END) AS dense_urban,
    SUM(CASE WHEN neighborhood IN('QUEEN ANNE','MAGNOLIA','BALLARD SOUTH','BALLARD NORTH',
        'WALLINGFORD','GREENWOOD','FREMONT','MADRONA/LESCHI') THEN 1 END) AS residential
FROM spd
WHERE offense_category = 'PROPERTY CRIME'
GROUP BY yr ORDER BY yr;
