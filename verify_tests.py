import asyncio
import os
import sys

# Add the project root to sys.path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from packages.data_pipeline.models.db import Base
from apps.api.main import app
from fastapi.testclient import TestClient

from packages.data_pipeline.normalization.etl import ETLPipeline
from packages.scraping.sources.airlines.air_india.adapter import AirIndiaAdapter
from packages.scraping.core.fetchers.base import Request, Response

def test_db_and_etl():
    engine = create_engine('sqlite:///:memory:')
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    session = Session()
    print("Database schema created successfully.")
    
    adapter = AirIndiaAdapter()
    response = Response(
        request=Request("http://dummy.com"),
        status=200,
        body=b"<html><div class='flight-card'><span class='base-fare'>1000</span><span class='total-fare'>1500</span></div></html>",
        headers={}
    )
    quotes = adapter.parse(response)
    
    etl = ETLPipeline()
    etl.load(quotes, session)
    print(f"ETL pipeline loaded {len(quotes)} quotes successfully.")

def test_fastapi():
    client = TestClient(app)
    response = client.get("/")
    assert response.status_code == 200, response.text
    assert response.json() == {"message": "Welcome to APIx SAFAR"}
    
    response = client.get("/api/v1/system/health")
    assert response.status_code == 200, response.text
    
    response = client.get("/api/v1/routes/DEL-BOM/trends")
    assert response.status_code == 200, response.text
    
    print("FastAPI endpoints tested successfully.")

if __name__ == "__main__":
    test_db_and_etl()
    test_fastapi()
    print("All tests passed!")
