"""API contract tests: success paths, validation, auth, error structure."""

from __future__ import annotations

import csv
import io
from datetime import date
from decimal import Decimal

import pytest
from fastapi.testclient import TestClient

from tests.api.conftest import API_KEY, DAYS, ROUTES, START

LAST = date(2026, 9, 3)


class TestIndex:
    def test_latest_headline(self, client: TestClient) -> None:
        body = client.get("/api/v1/index/latest").json()
        assert body["date"] == LAST.isoformat()
        assert body["data_origin"] == "simulated"
        assert body["base_period"] == ["2026-08-26", "2026-09-01"]
        assert body["methodology_status"]["basket_weights"] == "INDICATIVE"
        assert Decimal(body["coverage_pct"]) > 0
        assert body["change_mom_pct"] is not None  # August → September

    def test_daily_series_with_rolling_mean(self, client: TestClient) -> None:
        body = client.get("/api/v1/index/daily").json()
        assert len(body["items"]) == DAYS
        first = body["items"][0]
        assert first["rolling_value"] == first["value"]
        # The base-period average of the daily index is 100 by construction.
        base = [Decimal(p["value"]) for p in body["items"][:7]]
        assert abs(sum(base) / 7 - 100) < Decimal("1.5")

    def test_date_filter_and_scopes(self, client: TestClient) -> None:
        body = client.get("/api/v1/index/daily", params={"start_date": "2026-09-01", "scope": "WINDOW", "key": "T+7"}).json()
        assert [p["period_start"] for p in body["items"]] == ["2026-09-01", "2026-09-02", "2026-09-03"]
        weekly = client.get("/api/v1/index/weekly").json()["items"]
        monthly = client.get("/api/v1/index/monthly").json()["items"]
        assert {p["period_start"] for p in monthly} == {"2026-08-01", "2026-09-01"}
        assert all(date.fromisoformat(p["period_start"]).weekday() == 0 for p in weekly)

    def test_sub_indices_cover_all_windows(self, client: TestClient) -> None:
        items = client.get("/api/v1/index/sub-indices").json()["items"]
        windows = {i["scope_key"] for i in items if i["scope"] == "WINDOW"}
        assert windows == {"T+1", "T+7", "T+15", "T+30", "T+45"}

    def test_lineage_links_value_to_cells_and_parameters(self, client: TestClient) -> None:
        body = client.get(f"/api/v1/index/daily/{LAST.isoformat()}/lineage").json()
        assert body["parameters"]["method"] == "laspeyres_fixed_basket"
        assert len(body["cells"]) == len(ROUTES) * 5
        fares = client.get(body["quotes_endpoint"]).json()
        assert fares["total"] > 0 and all(f["is_canonical"] for f in fares["items"])

    def test_invalid_query_is_a_structured_422(self, client: TestClient) -> None:
        resp = client.get("/api/v1/index/daily", params={"start_date": "not-a-date"})
        assert resp.status_code == 422
        error = resp.json()["error"]
        assert error["code"] == "validation_error" and error["request_id"]
        assert resp.headers["x-request-id"] == error["request_id"]

    def test_unknown_lineage_date_is_404(self, client: TestClient) -> None:
        resp = client.get("/api/v1/index/daily/2020-01-01/lineage")
        assert resp.status_code == 404 and resp.json()["error"]["code"] == "not_found"


class TestRoutesAndAnalytics:
    def test_routes_list(self, client: TestClient) -> None:
        routes = client.get("/api/v1/routes").json()
        assert len(routes) == 24
        priced = [r for r in routes if r["latest_index"] is not None]
        assert {r["code"] for r in priced} == set(ROUTES)
        assert sum(Decimal(r["weight_share_pct"]) for r in routes) == pytest.approx(Decimal(100), abs=Decimal("0.1"))

    def test_route_trends_and_lead_time(self, client: TestClient) -> None:
        body = client.get("/api/v1/routes/DEL-BOM/trends").json()
        assert body["route"]["code"] == "DEL-BOM"
        assert len(body["history"]) == DAYS
        windows = [p["purchase_window"] for p in body["lead_time"]["points"]]
        assert windows == [1, 7, 15, 30, 45]
        assert body["lead_time"]["elasticity"] < 0  # later purchase is cheaper

    def test_route_validation(self, client: TestClient) -> None:
        assert client.get("/api/v1/routes/del-BOM/trends").status_code == 422
        assert client.get("/api/v1/routes/GOI-IXC/trends").status_code == 404

    def test_heatmap_carriers_channels_funnel(self, client: TestClient) -> None:
        heat = client.get("/api/v1/analytics/heatmap", params={"frequency": "WEEKLY"}).json()
        assert {c["route"] for c in heat["cells"]} == set(ROUTES)
        carriers = client.get("/api/v1/analytics/carriers").json()["items"]
        assert carriers and all(Decimal(c["median_fare"]) > 0 for c in carriers)
        channels = client.get("/api/v1/analytics/channels").json()["items"]
        assert channels and all(Decimal(c["wedge_pct"]) > 0 for c in channels)  # OTA adds a fee
        funnel = client.get("/api/v1/analytics/funnel").json()
        assert funnel["raw"] >= funnel["normalized"] >= funnel["canonical"] > 0
        assert funnel["duplicates"] + funnel["outliers"] >= 0

    def test_lead_time_endpoint(self, client: TestClient) -> None:
        body = client.get("/api/v1/analytics/lead-time", params={"date": START.isoformat()}).json()
        assert body["date"] == START.isoformat() and body["data_origin"] == "simulated"


class TestFares:
    def test_pagination_and_filters(self, client: TestClient) -> None:
        page = client.get("/api/v1/fares", params={"route": "DEL-BOM", "limit": 5, "offset": 5}).json()
        assert page["limit"] == 5 and page["offset"] == 5 and len(page["items"]) == 5
        assert all(f["route"] == "DEL-BOM" for f in page["items"])
        outliers = client.get("/api/v1/fares", params={"quality_flag": "OUTLIER"}).json()
        assert all(f["quality_flag"] == "OUTLIER" for f in outliers["items"])
        assert client.get("/api/v1/fares", params={"limit": 10_000}).status_code == 422

    def test_fare_lineage_reaches_raw_payload_and_response(self, client: TestClient) -> None:
        fare_id = client.get("/api/v1/fares", params={"limit": 1}).json()["items"][0]["id"]
        body = client.get(f"/api/v1/fares/{fare_id}").json()
        assert body["raw_payload"]["total_fare"].startswith("₹") or body["fare"]["availability"] != "AVAILABLE"
        assert len(body["response_sha256"]) == 64 and body["job_id"]
        assert client.get("/api/v1/fares/999999999").status_code == 404


class TestSystemAndJobs:
    def test_system_health_and_sources(self, client: TestClient) -> None:
        body = client.get("/api/v1/system/health").json()
        assert body["database"] == "ok"
        simulated = {s["id"]: s for s in body["sources"]}["simulated"]
        assert simulated["runnable"] and simulated["jobs_succeeded"] > 0
        assert body["freshness"]["latest_observation_date"] == LAST.isoformat()
        indigo = {s["id"]: s for s in body["sources"]}["indigo"]
        assert not indigo["runnable"] and not indigo["tos_reviewed"]

    def test_jobs_and_sweeps(self, client: TestClient) -> None:
        sweeps = client.get("/api/v1/sweeps").json()
        assert sweeps["total"] == DAYS and sweeps["items"][0]["status"] == "COMPLETED"
        jobs = client.get("/api/v1/jobs", params={"status": "SUCCESS", "limit": 2}).json()
        assert jobs["total"] == DAYS * len(ROUTES) * 5 * 2
        job_id = jobs["items"][0]["id"]
        assert client.get(f"/api/v1/jobs/{job_id}").json()["status"] == "SUCCESS"

    def test_operator_endpoints_require_api_key(self, client: TestClient) -> None:
        job_id = client.get("/api/v1/jobs", params={"limit": 1}).json()["items"][0]["id"]
        denied = client.post(f"/api/v1/jobs/{job_id}/requeue")
        assert denied.status_code == 401 and denied.json()["error"]["code"] == "unauthorized"
        wrong = client.post(f"/api/v1/jobs/{job_id}/requeue", headers={"X-API-Key": "nope"})
        assert wrong.status_code == 401
        ok = client.post(f"/api/v1/jobs/{job_id}/requeue", headers={"X-API-Key": API_KEY})
        assert ok.json() == {"requeued": 1}
        assert client.get(f"/api/v1/jobs/{job_id}").json()["status"] == "PENDING"

    def test_manual_sweep(self, client: TestClient) -> None:
        resp = client.post(
            "/api/v1/sweeps",
            json={"observation_date": "2026-09-04", "routes": ["DEL-BOM"], "windows": [1, 7]},
            headers={"X-API-Key": API_KEY},
        )
        assert resp.status_code == 202 and resp.json()["jobs_enqueued"] == 4
        bad = client.post(
            "/api/v1/sweeps", json={"sources": ["indigo"]}, headers={"X-API-Key": API_KEY}
        )
        assert bad.status_code == 422 and bad.json()["error"]["code"] == "configuration_error"


class TestValidationAndData:
    def test_backtest_and_benchmarks_are_labelled_synthetic(self, client: TestClient) -> None:
        body = client.get("/api/v1/backtests/latest").json()
        assert body["benchmark_is_synthetic"] and body["apix_is_synthetic"]
        assert body["days_covered"] == DAYS
        assert body["verdict"].startswith("INSUFFICIENT") and "SYNTHETIC" in body["verdict"]
        benchmarks = client.get("/api/v1/benchmarks").json()
        assert all("not DGCA data" in b["source_label"] for b in benchmarks)

    def test_methodology_reports_external_dependencies(self, client: TestClient) -> None:
        body = client.get("/api/v1/methodology").json()
        assert body["basket"]["status"] == "INDICATIVE" and len(body["basket"]["routes"]) == 24
        assert body["purchase_windows"] == [1, 7, 15, 30, 45]
        assert any("DGCA" in d for d in body["external_dependencies"])

    def test_protected_quotes_export(self, client: TestClient) -> None:
        assert client.get("/api/v1/data/quotes", params={"date": LAST.isoformat()}).status_code == 401
        resp = client.get(
            "/api/v1/data/quotes", params={"date": LAST.isoformat()}, headers={"X-API-Key": API_KEY}
        )
        rows = list(csv.DictReader(io.StringIO(resp.text)))
        assert rows and all(r["is_canonical"] == "True" for r in rows)
        assert {"raw_quote_id", "response_id", "job_id"} <= set(rows[0])
        evidence = client.get(f"/api/v1/data/evidence/{rows[0]['response_id']}", headers={"X-API-Key": API_KEY})
        assert evidence.status_code == 200 and b'"results"' in evidence.content

    def test_metrics_and_probes(self, client: TestClient) -> None:
        assert client.get("/api/v1/health/live").json() == {"status": "ok"}
        assert client.get("/api/v1/health/ready").json()["database"] == "ok"
        assert "safar_" in client.get("/metrics").text
