You are acting as the presentation strategist, product storyteller, technical architect,
and Figma Slides designer for our Smart India Hackathon 2026 submission.

Your task is to create the FINAL SIH PRESENTATION directly inside the provided
Figma Slides template.

==================================================
PROJECT
==================================================

Problem Statement:

SIH 2026 — PS 26056

Project:
Real-Time Airfare Price Index for India

The authoritative problem statement is available in this repository.

Repository:

/home/logan78/Desktop/airfare-index-bot

Read the relevant PS file, including:

/home/logan78/Desktop/airfare-index-bot/ps.md

==================================================
OFFICIAL FIGMA / SIH PRESENTATION TEMPLATE
==================================================

Use THIS presentation as the actual target presentation:

https://www.figma.com/slides/bTb73TM0t7kL98SyPduo03/SIH2026-IDEA-Presentation-Format?node-id=0-27&t=zTRuqOSDT8PxsWPv-0

Related deck link:

https://www.figma.com/deck/bTb73TM0t7kL98SyPduo03

IMPORTANT:

This template is the SOURCE OF TRUTH for:

- required slides
- maximum slide count
- headings
- sections
- instructions
- SIH rules
- layout constraints
- mandatory content
- submission requirements

FIRST inspect EVERY slide in the template.

Read every instruction written inside it.

Do not begin designing until you understand all SIH template rules.

If the template says:
- do not change a heading
- do not exceed a slide count
- keep specific content
- follow a specific format
- include specific information

then obey it exactly.

Do NOT casually create extra slides if the SIH template limits the deck.

Do NOT remove mandatory SIH headings.

Do NOT redesign the deck in a way that violates submission requirements.

==================================================
PROJECT DOCUMENTATION — CONTENT SOURCE
==================================================

You have TWO important sources of project documentation.

SOURCE A:

/home/logan78/Desktop/airfare-index-bot/kartik

Study this material thoroughly.

Use it for:
- existing project thinking
- feature definitions
- solution ideas
- previous research
- workflow
- implementation details
- business/product reasoning
- any useful diagrams or explanations

SOURCE B:

/home/logan78/Desktop/airfare-index-bot/docs

This is especially important for:

- final architecture
- scraper architecture
- system architecture
- database design
- API architecture
- pipeline design
- index engine
- observability
- deployment
- implementation architecture
- technical decisions

For TECHNICAL ARCHITECTURE, prefer docs/ as the source of truth.

If kartik/ and docs/ disagree about the final system architecture:

prefer:

ps.md
↓
latest docs/ architecture
↓
kartik/ supporting material
↓
existing implementation

Do not invent a completely different architecture.

==================================================
FIRST PHASE — RESEARCH
==================================================

Before editing the presentation, perform thorough research.

Research:

1. How successful Smart India Hackathon idea presentations are structured.
2. What SIH evaluators generally need to understand quickly.
3. How winning/strong hackathon presentations communicate:
   - problem
   - impact
   - novelty
   - feasibility
   - technical architecture
   - implementation
   - scalability
   - business/government value
4. Presentation patterns used by strong SIH teams.
5. Common reasons technical hackathon presentations become weak.
6. How to communicate architecture without overwhelming judges.
7. How to present a government/statistical-data product credibly.
8. How to demonstrate innovation beyond simply "we built a scraper."

Research should INFORM the presentation.

However:

THE OFFICIAL SIH TEMPLATE RULES OVERRIDE GENERIC INTERNET ADVICE.

Do not change the required SIH format because another presentation used
a different format.

==================================================
UNDERSTAND THE PRODUCT FIRST
==================================================

Before designing slides, deeply understand PS 26056.

The product is NOT simply:

"an airline web scraper."

It should be communicated as an end-to-end statistical data platform:

Airline + OTA Sources
        ↓
Ethical Data Acquisition
        ↓
Raw Fare Evidence
        ↓
Validation + Normalization
        ↓
Data Quality + Deduplication
        ↓
Canonical Airfare Dataset
        ↓
Airfare Price Index Engine
        ↓
Analytics + Backtesting
        ↓
NSO / MoSPI / RBI API
        ↓
Interactive Dashboard

Understand why the project matters.

The core story should address the gap between:

CURRENT SYSTEM
manual / limited airfare price collection

and:

PROPOSED SYSTEM
automated, scalable, auditable, high-frequency airfare price intelligence.

==================================================
IMPORTANT PROJECT CAPABILITIES
==================================================

Extract the exact capabilities from ps.md and documentation.

Important concepts likely include:

- major Indian airlines
- OTAs
- dynamic airfare collection
- representative city-pair basket
- T+1
- T+7
- T+15
- T+30
- T+45 advance booking windows
- fare class
- base fare
- taxes
- airport fees
- convenience fee
- total fare
- daily index
- weekly index
- monthly index
- route-level analysis
- lead-time elasticity
- sector heatmaps
- historical fare trends
- DGCA validation/backtesting
- 30-day historical/backtesting capability
- source health monitoring
- data quality
- auditability
- API access
- dashboard
- scheduled acquisition
- ethical scraping
- robots.txt awareness
- rate limiting
- retry/backoff
- normalized database

Do not simply list all of these.

Turn them into a coherent product story.

==================================================
KEY DIFFERENTIATION
==================================================

The presentation should clearly communicate why this is more than
Scrapy/Selenium + dashboard.

Potential differentiators should come from the actual architecture:

- multi-source acquisition engine
- source adapter architecture
- resilient fetch strategies
- raw-data preservation
- canonical fare schema
- auditable data lineage
- configurable route/index methodology
- source-health monitoring
- index reproducibility
- automated quality pipeline
- advance-purchase-window intelligence
- lead-time elasticity
- backtesting against public DGCA information
- API-first government integration
- extensible new-source onboarding

Only claim features that are supported by the documentation or implementation.

Never invent achievements.

==================================================
SCRAPER ARCHITECTURE
==================================================

Use docs/ to understand the scraper.

Where relevant, explain it visually as something like:

                    Acquisition Engine
                           |
            +--------------+--------------+
            |              |              |
        HTTP Fetch     Browser Fetch    Structured/XHR
            |              |              |
            +--------------+--------------+
                           |
                      Source Adapter
                           |
                       Raw Quote
                           |
                       Validation
                           |
                      Normalization

Keep it visually understandable.

Do not fill the slide with class names unless required.

The presentation is for judges, not for repository documentation.

==================================================
SYSTEM ARCHITECTURE
==================================================

Use the ACTUAL architecture documented in:

/home/logan78/Desktop/airfare-index-bot/docs

Create a professional simplified architecture diagram.

It should show major logical boundaries, for example:

Sources
↓
Acquisition
↓
Processing / Quality
↓
Storage
↓
Index Engine
↓
API
↓
Dashboard / Government Consumers

Show important supporting systems where useful:

- scheduler
- observability
- source health
- raw data
- canonical database
- backtesting

The architecture slide should communicate the system in approximately
10–20 seconds when viewed by a judge.

Do not turn it into a giant UML diagram.

==================================================
PRODUCT-FIRST STORYTELLING
==================================================

The deck should feel like a PRODUCT presentation,
not a college assignment.

Each slide should answer one major question.

Examples:

WHY?
Why does this problem matter?

WHAT?
What exactly are we building?

HOW?
How does it work?

WHY US / WHY THIS APPROACH?
What makes the solution technically strong?

CAN IT WORK?
Is it feasible and scalable?

WHAT DOES THE USER SEE?
What does the dashboard/product provide?

HOW IS IT VALIDATED?
How do we ensure trustworthy data/index values?

WHAT IS THE IMPACT?
How does MoSPI/NSO/RBI benefit?

Do not overload slides with paragraphs.

==================================================
CONTENT DENSITY
==================================================

Prefer:

short headline
+
strong diagram
+
3–5 concise supporting points

over:

large paragraphs.

Turn text into:

- diagrams
- flows
- timelines
- comparison tables
- metric cards
- architecture blocks
- process graphics
- charts
- callouts

where appropriate.

A judge should understand the main point of each slide without reading
hundreds of words.

==================================================
VISUAL STYLE
==================================================

Follow the SIH template's visual constraints first.

Within those constraints, make the deck:

- professional
- modern
- clean
- technical
- government/product appropriate
- visually consistent
- high contrast
- presentation-friendly

Avoid:

- childish illustrations
- random gradients
- excessive glow
- excessive AI-looking visuals
- clutter
- tiny text
- inconsistent icons
- decorative elements with no meaning
- excessive animation

Use consistent:

- typography
- spacing
- iconography
- diagram styling
- border radius
- hierarchy
- alignment

==================================================
USE REAL PRODUCT UI WHEN POSSIBLE
==================================================

Inspect the repository and any existing frontend implementation.

If meaningful product UI already exists, consider using:

- dashboard screenshot
- route analytics
- airfare charts
- heatmap
- source health
- historical trend page

instead of generic mockups.

If the implementation/frontend exists in another branch, it may be used
as inspiration/reference where appropriate.

Do NOT invent screenshots of features that do not exist unless clearly
identified as a conceptual mockup.

==================================================
DEMO WEBSITE LINK
==================================================

Reserve a clearly visible area for:

LIVE DEMO

Do not hard-code a fake URL.

Use a placeholder such as:

[LIVE DEMO URL]

Design it so we can later replace the placeholder with the final URL.

Prefer including space for:

- clickable link
- QR code

if appropriate under the SIH template rules.

==================================================
DEMO VIDEO LINK
==================================================

Also reserve a clearly visible area for:

DEMO VIDEO

Use placeholder:

[YOUTUBE DEMO URL]

Again, do not invent a fake URL.

Design space for:

- clickable YouTube link
- QR code

if appropriate.

If there is a final/demo slide, this may be a good location.

If SIH template rules suggest another location, follow the template.

==================================================
QR CODE PLACEHOLDERS
==================================================

Where appropriate reserve:

[QR — LIVE DEMO]

and

[QR — DEMO VIDEO]

Do NOT generate QR codes until actual URLs are available.

The placeholders should be easy to replace later.

==================================================
EVIDENCE / NUMBERS
==================================================

Where numerical claims appear:

- verify them
- prefer authoritative government / official sources
- keep citations or source references documented
- do not fabricate performance numbers

If implementation benchmarks exist in repository documentation,
use them only if they were actually measured.

Do NOT claim:

99.9% accuracy
10x faster
millions of records

or similar marketing numbers without evidence.

==================================================
TECH STACK
==================================================

Show the real implementation stack from the repository/docs.

Do NOT include a technology just because it sounds impressive.

Explain technologies in terms of architectural responsibility.

Example:

Scraping Engine
Python / Scrapling-inspired adapters

API
FastAPI

Storage
PostgreSQL

Dashboard
actual frontend stack

Scheduling
actual documented scheduler

Observability
actual documented tools

Do not create a meaningless logo wall.

==================================================
FEASIBILITY
==================================================

The presentation should communicate BOTH:

SIH PROTOTYPE ARCHITECTURE

and, where useful,

PRODUCTION EVOLUTION

Do not make the prototype look unnecessarily distributed.

If the current architecture intentionally avoids Kafka or heavy
microservices for SIH, preserve that.

Explain scalability as an evolution path rather than pretending the
prototype already runs at national production scale.

==================================================
DATA TRUST / AUDITABILITY
==================================================

This is especially important because the intended consumers include
government/statistical organizations.

Communicate concepts such as:

raw observation
↓
normalized observation
↓
quality flags
↓
index computation
↓
traceable output

A judge should understand that an index value can be traced back to
the underlying fare observations.

==================================================
PRESENTATION RULES
==================================================

For every slide:

1. Understand what SIH expects from that slide.
2. Determine the single most important message.
3. Use project documentation to support it.
4. Use diagrams/visuals wherever they explain better than text.
5. Keep text concise.
6. Maintain strong hierarchy.
7. Avoid jargon unless needed.
8. Ensure all important technical claims are correct.

==================================================
ANIMATIONS
==================================================

Use animations only where they improve explanation.

Good uses:

- progressive architecture reveal
- pipeline stages
- before → after
- workflow
- product flow

Avoid animations that exist only for decoration.

Animations should remain:

- subtle
- professional
- fast
- predictable

Do not risk presentation failure by depending on complex animation behavior.

==================================================
DESIGN PROCESS
==================================================

PHASE 1
Inspect the entire official Figma Slides template.

PHASE 2
Extract all template rules and mandatory sections.

PHASE 3
Read ps.md completely.

PHASE 4
Read relevant content under:

/home/logan78/Desktop/airfare-index-bot/kartik

PHASE 5
Read ALL important architecture material under:

/home/logan78/Desktop/airfare-index-bot/docs

PHASE 6
Inspect existing implementation/frontend where useful.

PHASE 7
Research strong SIH/hackathon presentation practices.

PHASE 8
Create a slide-by-slide content strategy BEFORE making major edits.

For each slide define:

- objective
- key message
- evidence
- visual approach
- source documentation
- optional animation

PHASE 9
Check the content strategy against SIH template requirements.

PHASE 10
Implement the slides directly in Figma Slides.

PHASE 11
Review the complete deck as a judge.

PHASE 12
Improve visual hierarchy, consistency, and storytelling.

==================================================
FINAL JUDGE REVIEW
==================================================

Before considering the presentation complete, review it from the
perspective of an SIH evaluator.

Ask:

Can I understand the problem in <30 seconds?

Can I understand the proposed solution immediately?

Is the innovation obvious?

Is this more than "web scraping"?

Can I understand how the system works?

Does the architecture look feasible?

Can I see why NSO/MoSPI/RBI would use this?

Is the data trustworthy?

Can I understand how the index is produced?

Is scalability addressed realistically?

Is there evidence/backtesting strategy?

Is the dashboard/product visible?

Are the live demo and video locations obvious?

Is anything too technical?

Is anything too vague?

Is any slide overcrowded?

Does every slide comply with the official SIH template?

Fix any weakness you find.

==================================================
FINAL TECHNICAL REVIEW
==================================================

Cross-check every architecture claim against:

/home/logan78/Desktop/airfare-index-bot/docs

Cross-check every product requirement against:

/home/logan78/Desktop/airfare-index-bot/ps.md

Cross-check supporting implementation/product details against:

/home/logan78/Desktop/airfare-index-bot/kartik

Do NOT introduce architecture that does not exist in the approved plan.

==================================================
DO NOT
==================================================

Do NOT:

- make a generic AI-generated hackathon presentation
- ignore SIH template instructions
- exceed the allowed slide count
- remove mandatory sections
- invent metrics
- invent completed functionality
- invent government approvals
- create fake demo URLs
- create fake YouTube URLs
- add random technologies
- overcomplicate architecture
- use giant paragraphs
- use unreadably small text
- turn the deck into repository documentation
- copy content blindly from other SIH teams
- replace technical accuracy with marketing language

==================================================
EXPECTED RESULT
==================================================

The final Figma Slides deck should feel like:

OFFICIAL SIH FORMAT
+
STRONG PRODUCT STORY
+
REAL TECHNICAL DEPTH
+
CLEAR ARCHITECTURE
+
REALISTIC IMPLEMENTATION
+
GOVERNMENT-GRADE DATA TRUST
+
POLISHED VISUAL DESIGN
+
DEMO-READY PRESENTATION

It should communicate that this is not merely an airfare scraper.

It is an:

AUDITABLE, HIGH-FREQUENCY AIRFARE INTELLIGENCE AND PRICE-INDEX PLATFORM
FOR INDIA.

==================================================
FINAL REPORT
==================================================

After completing the deck, report:

1. SIH template rules discovered
2. slide-by-slide story used
3. major changes made
4. project documentation used for each major technical section
5. architecture represented
6. product differentiators emphasized
7. research insights incorporated
8. places reserved for LIVE DEMO URL
9. places reserved for YOUTUBE DEMO URL
10. any content that still requires real data/screenshots
11. any unverifiable claim intentionally omitted
12. final presentation review findings

Begin by inspecting the Figma Slides template and extracting its rules.

Do not redesign anything until those rules are understood.