import os
import textwrap

# Data Pipeline
os.makedirs('packages/data_pipeline/models', exist_ok=True)
with open('packages/data_pipeline/models/__init__.py', 'w') as f: f.write('')
with open('packages/data_pipeline/models/db.py', 'w') as f:
    f.write(textwrap.dedent("""\
    from sqlalchemy.orm import declarative_base, sessionmaker
    from sqlalchemy import Column, Integer, String, Float, DateTime, Boolean, ForeignKey, JSON
    from datetime import datetime

    Base = declarative_base()

    class Source(Base):
        __tablename__ = 'sources'
        id = Column(Integer, primary_key=True)
        name = Column(String, unique=True, nullable=False)
        type = Column(String, nullable=False)
        status = Column(String, default='ACTIVE')
        rate_limit_rpm = Column(Integer, default=60)

    class Route(Base):
        __tablename__ = 'routes'
        id = Column(Integer, primary_key=True)
        origin_iata = Column(String, nullable=False)
        destination_iata = Column(String, nullable=False)
        dgca_weight = Column(Float, default=1.0)

    class ScrapeJob(Base):
        __tablename__ = 'scrape_jobs'
        id = Column(Integer, primary_key=True)
        started_at = Column(DateTime, default=datetime.utcnow)
        completed_at = Column(DateTime, nullable=True)
        status = Column(String, default='PENDING')
        target_date = Column(DateTime, nullable=False)
        purchase_window = Column(Integer, nullable=False)

    class RawQuote(Base):
        __tablename__ = 'raw_quotes'
        id = Column(Integer, primary_key=True)
        job_id = Column(Integer, ForeignKey('scrape_jobs.id'))
        source_id = Column(Integer, ForeignKey('sources.id'))
        raw_payload = Column(JSON)
        created_at = Column(DateTime, default=datetime.utcnow)

    class NormalizedQuote(Base):
        __tablename__ = 'normalized_quotes'
        id = Column(Integer, primary_key=True)
        raw_id = Column(Integer, ForeignKey('raw_quotes.id'))
        route_id = Column(Integer, ForeignKey('routes.id'))
        travel_date = Column(DateTime, nullable=False)
        advance_window = Column(Integer, nullable=False)
        carrier = Column(String, nullable=False)
        base_fare = Column(Float, nullable=False)
        total_fare = Column(Float, nullable=False)
        scrape_timestamp = Column(DateTime, default=datetime.utcnow)

    class IndexObservation(Base):
        __tablename__ = 'index_observations'
        date = Column(DateTime, primary_key=True)
        route_id = Column(Integer, primary_key=True)
        window = Column(Integer, primary_key=True)
        median_price = Column(Float, nullable=False)
        imputed = Column(Boolean, default=False)
    """))

with open('packages/data_pipeline/normalization/etl.py', 'w') as f:
    f.write(textwrap.dedent("""\
    class ETLPipeline:
        def extract(self, raw_data):
            return raw_data
        
        def transform(self, data):
            # Transformation logic
            return data
            
        def load(self, data, db_session):
            # Load into DB
            pass
    """))

# Source Adapters
airlines = ['air_india', 'spicejet', 'akasa', 'air_india_express']
otas = ['makemytrip', 'cleartrip', 'ixigo', 'yatra', 'easemytrip']

for airline in airlines:
    os.makedirs(f'packages/scraping/sources/airlines/{airline}', exist_ok=True)
    with open(f'packages/scraping/sources/airlines/{airline}/adapter.py', 'w') as f:
        f.write(textwrap.dedent(f"""\
        class {airline.title().replace('_', '')}Adapter:
            def metadata(self):
                return {{"name": "{airline}", "type": "AIRLINE", "rate_limit": 60}}
            
            def build_requests(self, context):
                return []
                
            def parse(self, response):
                return []
                
            def health_check(self):
                return True
        """))

for ota in otas:
    os.makedirs(f'packages/scraping/sources/otas/{ota}', exist_ok=True)
    with open(f'packages/scraping/sources/otas/{ota}/adapter.py', 'w') as f:
        f.write(textwrap.dedent(f"""\
        class {ota.title().replace('_', '')}Adapter:
            def metadata(self):
                return {{"name": "{ota}", "type": "OTA", "rate_limit": 30}}
            
            def build_requests(self, context):
                return []
                
            def parse(self, response):
                return []
                
            def health_check(self):
                return True
        """))

# FastAPI Endpoints
os.makedirs('apps/api/routers', exist_ok=True)
with open('apps/api/routers/index.py', 'w') as f:
    f.write(textwrap.dedent("""\
    from fastapi import APIRouter

    router = APIRouter(prefix="/api/v1/index")

    @router.get("/daily")
    def get_daily_index(start_date: str, end_date: str, window: int = None):
        return {"status": "ok", "data": []}
        
    @router.get("/historical")
    def get_historical_index():
        return {"status": "ok", "data": []}
    """))

with open('apps/api/routers/routes.py', 'w') as f:
    f.write(textwrap.dedent("""\
    from fastapi import APIRouter

    router = APIRouter(prefix="/api/v1/routes")

    @router.get("/{origin}-{destination}/trends")
    def get_route_trends(origin: str, destination: str):
        return {"status": "ok", "route": f"{origin}-{destination}", "data": []}
    """))

with open('apps/api/routers/system.py', 'w') as f:
    f.write(textwrap.dedent("""\
    from fastapi import APIRouter

    router = APIRouter(prefix="/api/v1/system")

    @router.get("/health")
    def system_health():
        return {"status": "ok", "health": "good"}
    """))

with open('apps/api/routers/data.py', 'w') as f:
    f.write(textwrap.dedent("""\
    from fastapi import APIRouter

    router = APIRouter(prefix="/api/v1/data")

    @router.get("/quotes")
    def get_quotes(date: str):
        return {"status": "ok", "data": []}
    """))
