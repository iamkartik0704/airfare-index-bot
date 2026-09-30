import duckdb
import logging
from typing import List
from pathlib import Path
from .collect.base import RawQuote
from .clean import CleanQuote

log = logging.getLogger("safar.db")

DB_PATH = Path(__file__).resolve().parents[2] / "data" / "apix.duckdb"

def get_connection():
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    return duckdb.connect(str(DB_PATH))

def init_db():
    with get_connection() as con:
        con.execute("""
            CREATE SEQUENCE IF NOT EXISTS seq_raw_quote_id;
            CREATE TABLE IF NOT EXISTS raw_quotes (
                id INTEGER DEFAULT nextval('seq_raw_quote_id'),
                source_id VARCHAR,
                carrier VARCHAR,
                route_id VARCHAR,
                origin VARCHAR,
                destination VARCHAR,
                departure DATE,
                lead_time INTEGER,
                fare_class VARCHAR,
                flight_no VARCHAR,
                fare_text VARCHAR,
                tax_text VARCHAR,
                fee_text VARCHAR,
                seats_left INTEGER,
                refundable BOOLEAN,
                baggage_kg INTEGER,
                collected_at TIMESTAMP,
                is_synthetic BOOLEAN DEFAULT FALSE
            );
            
            CREATE SEQUENCE IF NOT EXISTS seq_std_price_id;
            CREATE TABLE IF NOT EXISTS std_prices (
                id INTEGER DEFAULT nextval('seq_std_price_id'),
                route VARCHAR,
                airline VARCHAR,
                travel_date DATE,
                booking_datetime TIMESTAMP,
                lead_days INTEGER,
                fare_class VARCHAR,
                base_fare DOUBLE,
                taxes DOUBLE,
                udf DOUBLE,
                convenience_fee DOUBLE,
                total_fare DOUBLE,
                quality DOUBLE,
                flags VARCHAR[],
                imputed BOOLEAN,
                source VARCHAR,
                is_synthetic BOOLEAN DEFAULT FALSE
            );
            
            CREATE TABLE IF NOT EXISTS index_points (
                date DATE PRIMARY KEY,
                value DOUBLE,
                nominal DOUBLE,
                quality_index DOUBLE,
                hedge_ratio DOUBLE,
                avg_fare DOUBLE,
                observations INTEGER,
                is_synthetic BOOLEAN DEFAULT FALSE
            );
        """)
        # For seamless upgrades of existing DB
        try:
            con.execute("ALTER TABLE raw_quotes ADD COLUMN is_synthetic BOOLEAN DEFAULT FALSE")
            con.execute("ALTER TABLE std_prices ADD COLUMN is_synthetic BOOLEAN DEFAULT FALSE")
            con.execute("ALTER TABLE index_points ADD COLUMN is_synthetic BOOLEAN DEFAULT FALSE")
        except:
            pass
        log.info("Initialized DuckDB schema at %s", DB_PATH)

def insert_raw_quotes(quotes: List[RawQuote]):
    if not quotes:
        return
    with get_connection() as con:
        con.executemany("""
            INSERT INTO raw_quotes (
                source_id, carrier, route_id, origin, destination, departure, 
                lead_time, fare_class, flight_no, fare_text, tax_text, fee_text, 
                seats_left, refundable, baggage_kg, collected_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, [
            (q.source_id, q.carrier, q.route_id, q.origin, q.destination, q.departure,
             q.lead_time, q.fare_class, q.flight_no, q.fare_text, q.tax_text, q.fee_text,
             q.seats_left, q.refundable, q.baggage_kg, q.collected_at)
            for q in quotes
        ])

def insert_std_prices(quotes: List[CleanQuote], departure_date: str, collected_at: str):
    if not quotes:
        return
    with get_connection() as con:
        con.executemany("""
            INSERT INTO std_prices (
                route, airline, travel_date, booking_datetime, lead_days,
                fare_class, base_fare, taxes, udf, convenience_fee, total_fare,
                quality, flags, imputed, source, is_synthetic
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, FALSE)
        """, [
            (q.route_id, q.carrier, departure_date, collected_at, q.lead_time,
             q.fare_class, q.base_fare, q.taxes, q.udf, q.convenience_fee, q.total_fare,
             q.quality, q.flags, q.imputed, q.source_id)
            for q in quotes
        ])

def insert_index_point(point: dict):
    with get_connection() as con:
        con.execute("""
            INSERT INTO index_points (
                date, value, nominal, quality_index, hedge_ratio, avg_fare, observations, is_synthetic
            ) VALUES (?, ?, ?, ?, ?, ?, ?, FALSE)
            ON CONFLICT (date) DO UPDATE SET
                value = EXCLUDED.value,
                nominal = EXCLUDED.nominal,
                quality_index = EXCLUDED.quality_index,
                hedge_ratio = EXCLUDED.hedge_ratio,
                avg_fare = EXCLUDED.avg_fare,
                observations = EXCLUDED.observations,
                is_synthetic = FALSE
        """, (
            point["date"], point["value"], point["nominal"], point["qualityIndex"],
            point["hedgeRatio"], point["avgFare"], point["observations"]
        ))
