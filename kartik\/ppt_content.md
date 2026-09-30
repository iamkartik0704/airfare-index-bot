# SAFAR (Statutory Air Fare Analytics & Reporting)
**Presentation Outline for SIH 2026 - Problem Statement 26056 (MoSPI)**

Here is a structured 10-slide outline for your presentation. You can use this as the exact blueprint for your PPT.

---

### Slide 1: Title Slide
* **Title:** SAFAR - Statutory Air Fare Analytics & Reporting
* **Subtitle:** A Real-time Airfare Price Index (APIx) for India
* **Details:** Problem Statement 26056 (MoSPI) | Team Name
* **Visual:** The new SAFAR black/yellow airplane logo and a screenshot of the main dashboard.

### Slide 2: The Problem & The Mandate
* **The Gap:** Airfares are highly volatile and dynamic, but current CPI (Consumer Price Index) tracking often relies on lagged, static, or narrow data collection.
* **The Mandate (MoSPI):** Build a robust, automated system to capture real-time airfare data and construct a statistically sound price index.
* **Our Approach:** Build an index that is **statutory by construction**—using the exact estimator family and basket discipline that the CPI uses, ensuring it can be adopted by the NSO, not just admired.

### Slide 3: The SAFAR Solution
* **What is APIx?** A fixed-basket, hedonic airfare price index.
* **Scale & Scope:**
  * 5 Airlines (Direct) + 6 OTAs (Online Travel Agencies)
  * 24 City-Pairs (weighted by DGCA passenger volume data)
  * 5 Advance-Purchase Windows (T+1 to T+45)
* **Visual:** The "What the NSO would print" chart from your dashboard.

### Slide 4: The Index Formula (Methodology)
* **Formula:** `APIx(d) = 100 · Σ wᵣ · [Pᵣ(d)/Pᵣ(0)] · [Q(0)/Q(d)]`
* **Fixed Basket Weights (wᵣ):** Based on DGCA actual passenger shares. We don't guess route importance; we use statutory data.
* **Hedonic Quality Adjustment (Q):** Fares aren't created equal. We mathematically adjust for legroom, meals, change fees, and CO2 emissions. A cheaper flight isn't "cheaper" if you lose your baggage allowance.
* **Speaker Note:** *This is the slide where you prove your math is sound to the statisticians on the judging panel.*

### Slide 5: Ethical & Resilient Data Collection
* **Ethical by Construction:** We strictly respect `robots.txt` for every host. We never bypass CAPTCHAs.
* **Anti-Fragility:** If a site blocks us, the challenge is logged in our audit trail, and the missing cell is statistically imputed so the index never breaks.
* **Visual:** A screenshot of the "Pipeline" page showing the Collector Audit Trail.

### Slide 6: The APIx Dashboard
* **Purpose:** A command center for MoSPI analysts and RBI policymakers.
* **Design Language:** Built with a high-contrast, data-dense "Neobrutalist" aesthetic to ensure clarity and immediate readability of critical metrics.
* **Features:** 7-day smoothed means vs. raw daily observations, YoY/MoM deltas, and regional breakdowns.
* **Visual:** Full screenshot of the Overview page.

### Slide 7: Unpacking the Volatility (Covariates)
* **The "Why":** We don't just track the price going up; we track *why* it goes up.
* **Macro Drivers:** The dashboard performs live decomposition against covariates like Jet Fuel (ATF) prices, USD/INR exchange rates, and passenger traffic.
* **Visual:** The "Drivers" page showing the regression coefficients.

### Slide 8: The Booking Curve (Elasticity)
* **Lead-Time Analysis:** Fares behave differently depending on when they are booked.
* **Tracking Sub-Indices:** We track T+1 (urgent business travel) separately from T+30 (leisure travel) to give policymakers granular insights into different consumer pain points.
* **Visual:** The Booking Window elasticity curve chart.

### Slide 9: Validation & Back-testing
* **Proving Accuracy:** An index is useless if it doesn't correlate with reality.
* **The Back-test:** We validate the SAFAR APIx against historical DGCA yield data to prove strong Pearson/Spearman correlation and directional accuracy.
* **Visual:** The Validation scatter plot comparing SAFAR APIx to DGCA data.

### Slide 10: Tech Stack & Architecture
* **Data Engine:** Python Scrapy/Playwright for collection, feeding into a high-performance **DuckDB** embedded database for instantaneous analytical queries.
* **Backend:** **FastAPI** providing a robust REST API for both the dashboard and public consumers (e.g., RBI, NSO).
* **Frontend:** **Vite + React** tailored with custom Tailwind components, avoiding heavy client-side calculations by shifting aggregations to the DuckDB backend.
* **Visual:** A simple architecture diagram (Collector -> DuckDB -> FastAPI -> React UI).

---

### Key Things to Keep in Mind During the Pitch:
1. **Focus on the Math:** MoSPI is a statistical body. Emphasize the "Hedonic Quality Adjustment" and the "DGCA Fixed Weights." This proves you aren't just scraping random flights, but actually building a statutory-grade economic index.
2. **Highlight the Ethics:** Mentioning that you respect `robots.txt` and don't bypass CAPTCHAs is a huge green flag for government agencies who cannot legally use grey-hat scraping tools.
3. **Show, Don't Tell:** When talking about the dashboard, mention the deliberate UI design (high contrast, data density) meant for actual analysts, not just a flashy generic template.
