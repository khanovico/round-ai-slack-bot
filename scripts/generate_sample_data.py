#!/usr/bin/env python3
"""
Sample data generator for AppMetrics table
This script creates realistic sample data for mobile app analytics
"""

import asyncio
import random
from datetime import date, timedelta
from decimal import Decimal
from sqlalchemy import select
from app.db.database import AsyncSessionLocal
from app.models.app_metrics import AppMetrics


# Sample app names with realistic categories
SAMPLE_APPS = [
    "Round AI Assistant",
    "Round Analytics Pro", 
    "Round Portfolio Tracker",
    "Round Investment AI",
    "Round Market Analyzer",
    "Round Trading Bot",
    "Round Crypto Tracker",
    "Round Stock Screener",
    "Round Financial Planner",
    "Round Wealth Manager"
]

# Sample countries with realistic market sizes
COUNTRIES = [
    ("US", 1.0),      # United States - baseline
    ("GB", 0.8),      # United Kingdom
    ("DE", 0.7),      # Germany
    ("FR", 0.6),      # France
    ("CA", 0.6),      # Canada
    ("AU", 0.5),      # Australia
    ("JP", 0.5),      # Japan
    ("IN", 0.4),      # India
    ("BR", 0.4),      # Brazil
    ("MX", 0.3),      # Mexico
    ("ES", 0.3),      # Spain
    ("IT", 0.3),      # Italy
    ("NL", 0.3),      # Netherlands
    ("SE", 0.2),      # Sweden
    ("NO", 0.2),      # Norway
]

# Platforms with different characteristics
PLATFORMS = [
    ("iOS", 0.9, 1.2),   # iOS: lower volume, higher ARPU
    ("Android", 1.1, 0.8) # Android: higher volume, lower ARPU
]


async def generate_sample_data():
    """Generate and insert sample data into the database"""
    
    # Date range: last 3 months
    end_date = date.today()
    start_date = end_date - timedelta(days=90)
    
    print(f"Generating sample data from {start_date} to {end_date}")
    
    async with AsyncSessionLocal() as db:
        # Check if data already exists
        existing_count = await db.execute(select(AppMetrics))
        existing_count = len(existing_count.scalars().all())
        
        if existing_count > 0:
            print(f"Found {existing_count} existing records. Skipping data generation.")
            return
        
        # Generate data for each day
        current_date = start_date
        total_records = 0
        
        while current_date <= end_date:
            # Add some weekend/weekday variation
            is_weekend = current_date.weekday() >= 5
            weekend_multiplier = 1.3 if is_weekend else 1.0
            
            # Add some monthly seasonality
            month_factor = 1.0 + 0.2 * (current_date.month - 6) / 6  # Peak in summer
            
            for app_name in SAMPLE_APPS:
                for platform, volume_mult, arpu_mult in PLATFORMS:
                    for country, country_mult in COUNTRIES:
                        # Base installs with realistic variations
                        base_installs = random.randint(50, 500)
                        
                        # Apply multipliers
                        final_installs = int(
                            base_installs * 
                            volume_mult * 
                            country_mult * 
                            weekend_multiplier * 
                            month_factor * 
                            random.uniform(0.7, 1.3)  # Daily noise
                        )
                        
                        # Ensure installs are non-negative
                        final_installs = max(0, final_installs)
                        
                        if final_installs > 0:
                            # Calculate revenue based on installs
                            # iOS typically has higher ARPU than Android
                            base_arpu_iap = Decimal('0.50')  # $0.50 base
                            base_arpu_ads = Decimal('0.15')  # $0.15 base
                            base_cpi = Decimal('1.00')       # $1.00 base
                            
                            # Apply platform-specific ARPU adjustments
                            iap_revenue = Decimal(str(final_installs * float(base_arpu_iap * arpu_mult)))
                            ads_revenue = Decimal(str(final_installs * float(base_arpu_ads * arpu_mult)))
                            ua_cost = Decimal(str(final_installs * float(base_cpi)))
                            
                            # Add some randomness to revenue
                            iap_revenue *= Decimal(str(random.uniform(0.8, 1.2)))
                            ads_revenue *= Decimal(str(random.uniform(0.8, 1.2)))
                            ua_cost *= Decimal(str(random.uniform(0.8, 1.2)))
                            
                            # Round to 2 decimal places
                            iap_revenue = iap_revenue.quantize(Decimal('0.01'))
                            ads_revenue = ads_revenue.quantize(Decimal('0.01'))
                            ua_cost = ua_cost.quantize(Decimal('0.01'))
                            
                            # Create and add the record
                            metric = AppMetrics(
                                app_name=app_name,
                                platform=platform,
                                date=current_date,
                                country=country,
                                installs=final_installs,
                                in_app_revenue=iap_revenue,
                                ads_revenue=ads_revenue,
                                ua_cost=ua_cost
                            )
                            
                            db.add(metric)
                            total_records += 1
            
            current_date += timedelta(days=1)
            
            # Progress indicator
            if total_records % 1000 == 0:
                print(f"Generated {total_records} records...")
        
        # Commit all records
        await db.commit()
        print(f"Successfully generated {total_records} sample records!")
        
        # Show some sample data
        print("\nSample of generated data:")
        sample_records = await db.execute(
            select(AppMetrics).limit(5)
        )
        for record in sample_records.scalars().all():
            print(f"  {record.app_name} | {record.platform} | {record.country} | "
                  f"{record.date} | {record.installs} installs | "
                  f"${record.in_app_revenue} IAP | ${record.ads_revenue} Ads | ${record.ua_cost} UA")


if __name__ == "__main__":
    print("Starting sample data generation...")
    asyncio.run(generate_sample_data())
    print("Sample data generation complete!")
