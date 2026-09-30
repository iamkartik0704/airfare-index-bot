import math
from datetime import date, timedelta
from safar.db import init_db, get_connection

def seed():
    init_db()
    with get_connection() as con:
        # Clear existing
        con.execute("DELETE FROM std_prices")
        con.execute("DELETE FROM index_points")

        # 1. Seed std_prices for today's heatmap and elasticity
        today = date.today()
        routes = ["DEL-BOM", "DEL-BLR", "BOM-BLR", "DEL-HYD", "MAA-DEL"]
        leads = [1, 7, 15, 30, 45]
        
        for r in routes:
            for l in leads:
                base = 4000
                if r == "DEL-BOM": base = 5000
                # Elasticity curve simulation: T+1 is expensive, T+15 is cheap
                multiplier = 1.8 if l == 1 else (1.2 if l == 7 else (1.0 if l == 15 else 1.1))
                
                total = base * multiplier
                con.execute("""
                    INSERT INTO std_prices (
                        route, airline, travel_date, booking_datetime, lead_days,
                        fare_class, base_fare, taxes, udf, convenience_fee, total_fare,
                        quality, flags, imputed, source, is_synthetic
                    ) VALUES (?, '6E', ?, CURRENT_TIMESTAMP, ?, 'VALUE', ?, 500, 0, 0, ?, 1.0, [], false, 'indigo', true)
                """, (r, today.isoformat(), l, total - 500, total))
                
                # Insert OTA data for wedge analysis
                con.execute("""
                    INSERT INTO std_prices (
                        route, airline, travel_date, booking_datetime, lead_days,
                        fare_class, base_fare, taxes, udf, convenience_fee, total_fare,
                        quality, flags, imputed, source, is_synthetic
                    ) VALUES (?, '6E', ?, CURRENT_TIMESTAMP, ?, 'VALUE', ?, 500, 0, 350, ?, 1.0, [], false, 'makemytrip', true)
                """, (r, today.isoformat(), l, total - 500, total + 350))
        
        # 2. Seed index_points for 400 days
        for i in range(400):
            d = today - timedelta(days=400 - i - 1)
            
            # Base trend
            trend = 100 + (i * 0.03) 
            
            # Real seasonal patterns (approximations)
            month = d.month
            day = d.day
            
            seasonality = 0
            # Summer travel spike (May-June)
            if month in [5, 6]:
                seasonality = 8.0
            # Diwali/Festive spike (Late Oct-Nov)
            elif month == 11 or (month == 10 and day > 15):
                seasonality = 15.0
            # Winter holidays (Late Dec)
            elif month == 12 and day > 15:
                seasonality = 12.0
            # Off-season drop (Feb-Mar, Jul-Sep)
            elif month in [2, 3, 7, 8, 9]:
                seasonality = -5.0
                
            # Random noise (volatility)
            import random
            noise = random.uniform(-2.5, 2.5)
                
            val = trend + seasonality + noise
            con.execute("""
                INSERT INTO index_points (
                    date, value, nominal, quality_index, hedge_ratio, avg_fare, observations, is_synthetic
                ) VALUES (?, ?, ?, 1.0, 1.0, ?, 120, true)
            """, (d.isoformat(), val, val + random.uniform(-1, 1), 4500 + (val * 12)))
            
    print("Database seeded with mock data.")

if __name__ == "__main__":
    seed()
