from apps.api.routers import analytics, backtests, data, fares, health, index, jobs, routes, system

ALL_ROUTERS = [
    health.router,
    index.router,
    routes.router,
    analytics.router,
    fares.router,
    system.router,
    jobs.router,
    backtests.router,
    data.router,
]

__all__ = ["ALL_ROUTERS"]
