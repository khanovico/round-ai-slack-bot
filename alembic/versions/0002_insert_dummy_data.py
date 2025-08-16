"""Insert dummy data for app_metrics

Revision ID: 0002
Revises: 0001
Create Date: 2025-08-16 00:01:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '0002'
down_revision = '0001'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # First set the seed
    op.execute("SELECT setseed(0.42)")
    
    # Execute the main dummy data generation as a single statement
    op.execute("""
    WITH
    -- Build a list of fake app names
    apps AS (
      SELECT 'App '||TO_CHAR(g, 'FM000')||' '||
             (ARRAY['Paint','Notes','Todo','Weather','Calendar','Music','Maps','Finance','Health','Camera','Reader','Chat','Studio','Sketch','Tracker','Shop','News','Travel','Photo','Game'])[1 + (random()*19)::int]
             || ' ' ||
             (ARRAY['Lite','Pro','Max','Go','Plus','X','Pro Max','Mini','Pro+','Next'])[1 + (random()*9)::int]
             AS app_name
      FROM generate_series(1, 15) g
    ),
    platforms AS (
      SELECT unnest(ARRAY['iOS','Android']) AS platform
    ),
    -- Pick a country set (ISO-like names for demo)
    countries AS (
      SELECT unnest(ARRAY[
        'US','GB','DE','FR','CA','AU','BR','IN','JP',
        'ES','IT','NL','SE','NO','DK','FI','PL','MX','AR'
      ]) AS country
    ),
    dates AS (
      SELECT d::date AS date
      FROM generate_series(DATE '2025-01-01', DATE '2025-08-15', interval '1 day') d
    ),
    -- Per-country demand multipliers (US highest; tweak as you like)
    country_weight AS (
      SELECT country,
             CASE country
               WHEN 'US' THEN 1.80 WHEN 'GB' THEN 1.25 WHEN 'DE' THEN 1.20 WHEN 'FR' THEN 1.15
               WHEN 'CA' THEN 1.20 WHEN 'AU' THEN 1.15 WHEN 'JP' THEN 1.20 WHEN 'KR' THEN 1.15
               WHEN 'IN' THEN 0.90 WHEN 'BR' THEN 0.95 WHEN 'SG' THEN 1.10 WHEN 'AE' THEN 1.05
               ELSE 1.00
             END AS w
      FROM countries
    ),
    -- Platform multipliers (Android slightly larger volume, lower ARPU)
    platform_weight AS (
      SELECT 'iOS'::text AS platform, 0.95::float AS w, 1.20::float AS arpu_boost
      UNION ALL
      SELECT 'Android', 1.05, 0.90
    ),
    -- Seasonality: weekly + yearly components for installs
    seasonality AS (
      SELECT date,
             (1.0                                   -- base
              + 0.20 * sin(2*pi()*(extract(doy from date)/365.0))  -- annual swing
              + 0.10 * cos(2*pi()*(extract(dow from date)/7.0))    -- weekday vs weekend
             ) AS s
      FROM dates
    ),
    -- App-specific baselines & monetization params
    app_params AS (
      SELECT a.app_name,
             (50 + (random()*450))::int AS base_installs, -- 50..500
             0.10 + random()*0.90       AS quality,       -- quality scalar 0.1..1.0
             0.20 + random()*1.30       AS arpu_iap,      -- IAP ARPU $0.20..$1.50
             0.05 + random()*0.45       AS arpu_ads,      -- Ads ARPU $0.05..$0.50
             0.25 + random()*2.00       AS cpi            -- CPI $0.25..$2.25
      FROM apps a
    ),
    universe AS (
      SELECT
        ap.app_name, p.platform, d.date, c.country,
        ap.base_installs, ap.quality, ap.arpu_iap, ap.arpu_ads, ap.cpi,
        cw.w AS w_country, pw.w AS w_platform, pw.arpu_boost,
        s.s AS s_day
      FROM app_params ap
      CROSS JOIN platforms p
      JOIN platform_weight pw ON pw.platform = p.platform
      CROSS JOIN dates d
      JOIN seasonality s USING (date)
      CROSS JOIN countries c
      JOIN country_weight cw USING (country)
    )
    INSERT INTO app_metrics (app_name, platform, date, country, installs, in_app_revenue, ads_revenue, ua_cost)
    SELECT
      app_name,
      platform,
      date,
      country,
      installs,
      ROUND(GREATEST(0, installs * (arpu_iap * arpu_boost) * (0.85 + random()*0.3))::numeric, 2)  AS in_app_revenue,
      ROUND(GREATEST(0, installs * (arpu_ads)               * (0.85 + random()*0.3))::numeric, 2)  AS ads_revenue,
      ROUND(GREATEST(0, installs * (cpi)                    * (0.85 + random()*0.3))::numeric, 2)  AS ua_cost
    FROM (
      SELECT
        *,
        -- Core installs model (integer)
        GREATEST(
          0,
          (
            base_installs
            * quality
            * w_country
            * w_platform
            * s_day
            * (0.7 + random()*0.6)     -- day-to-day noise 0.7..1.3
            * CASE WHEN random() < 0.05 THEN (1.5 + random()*1.0) ELSE 1.0 END  -- occasional spikes
          )::int
        ) AS installs
      FROM universe
    ) m
    -- Randomly drop ~20% rows to simulate missing/paused geos or tracking gaps
    WHERE random() < 0.80
    """)
    
    # Analyze table separately
    op.execute("ANALYZE app_metrics")


def downgrade() -> None:
    # Delete all dummy data
    op.execute("DELETE FROM app_metrics;")