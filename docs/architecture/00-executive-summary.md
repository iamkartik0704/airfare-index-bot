# 00 Executive Summary

## Overview
This architecture blueprint describes the design and implementation strategy for the Real-time Airfare Price Index (APIx) project, developed for the SIH 2026 problem statement issued by the Ministry of Statistics and Programme Implementation (MoSPI). The goal is to replace the manual collection of airfares for the Consumer Price Index (CPI) with an automated, scalable, and high-frequency data collection system.

## The Problem
Airfares in India follow dynamic pricing models. The same flight sector can vary by 200-400% based on the advance booking window, demand, and fuel prices. Over 90% of tickets are booked online via Airline portals and Online Travel Aggregators (OTAs). Manual collection fails to capture this real-time dynamic pricing. MoSPI and the NSO require an automated system to scrape fares, normalize data, and calculate a realistic Airfare Price Index (APIx).

## The V4 Architecture Solution
The V4 Architecture heavily borrows from modern web scraping paradigms, notably the open-source **Scrapling** project. Instead of tightly coupling web requests, browser automation, and data parsing into monolithic scripts, the architecture cleanly separates these concerns:
- **Fetchers:** `HttpFetcher` for simple endpoints and `BrowserFetcher` (Playwright) for JS-heavy React/Angular SPAs.
- **Adapters:** Source-specific parsing and extraction rules that map raw HTML/JSON to a Canonical Data Model.
- **Pipeline:** A robust data normalization pipeline that validates, deduplicates, and stores data in a structured PostgreSQL database.
- **Index Engine:** A statistical module that aggregates normalized data using DGCA route weights to compute daily, weekly, and monthly APIx indices.
- **API & Dashboard:** A FastAPI backend and a Next.js frontend to visualize the data, including heatmaps and elasticity curves.

## Prototype vs. Production
For the SIH hackathon prototype, the system is designed to be highly reliable, easily testable, and demonstrable with 2-3 airline sources and 1-2 OTAs. Complex distributed infrastructure (e.g., Kafka) has been removed in favor of a simpler task queue (Celery/Redis or APScheduler) and a robust PostgreSQL relational store with JSONB support for raw data auditing.

This blueprint serves as the comprehensive guide for developers to implement the system from the ground up, ensuring maintainability, auditability, and adherence to ethical scraping standards.
