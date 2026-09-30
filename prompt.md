

You are the lead software engineer responsible for implementing the complete SIH 26056 project in this repository:

/home/logan78/Desktop/airfare-index-bot

The official problem statement is:

@ps.md

The approved architecture, engineering design, implementation roadmap, codebase structure, and subsystem specifications are located in:

/home/logan78/Desktop/airfare-index-bot/docs

Your task is to IMPLEMENT the project according to those documents.

==================================================
PRIMARY RULE
==================================================

The docs/ directory is the architectural source of truth.

DO NOT redesign the project from scratch.

DO NOT invent a different folder structure.

DO NOT remove folders because they currently look unused.

DO NOT flatten the architecture.

DO NOT replace the documented architecture with a simpler architecture unless the documentation explicitly allows it.

The existing folder skeleton represents intentional architectural boundaries.

Every relevant folder/file described in the architecture should eventually contain its intended implementation.

If something in the docs is ambiguous, inspect:

1. ps.md
2. all relevant docs
3. existing code
4. neighboring modules

before making a decision.

If there is a genuine conflict between documents, prefer:

ps.md requirements
    ↓
latest architecture documents
    ↓
implementation blueprint
    ↓
existing code

Document any unavoidable interpretation.

==================================================
STEP 0 — INSPECT EVERYTHING FIRST
==================================================

DO NOT immediately start coding.

First read:

@ps.md

and recursively inspect:

docs/

Read ALL architecture and implementation documentation relevant to the system.

Also inspect:

- current repository tree
- existing source code
- configuration
- package manifests
- Docker files
- database code
- tests
- scripts
- CI configuration
- environment examples

Understand what has already been implemented.

Then create a requirement-to-code mapping.

For each major requirement determine:

- requirement
- architecture subsystem
- intended package/module
- current implementation status
- missing implementation
- dependencies
- tests required

Classify implementation status as:

DONE
PARTIAL
MISSING
NEEDS_REFACTOR

Do not modify architecture documents merely to match incomplete code.

The implementation should move toward the approved architecture.

==================================================
PROBLEM OBJECTIVE
==================================================

Build an industry-grade implementation of SIH 26056:

A real-time airfare price-index platform capable of collecting,
normalizing, validating, storing, analyzing and serving airfare data.

The implementation must satisfy the requirements defined in ps.md,
including where applicable:

- airline data acquisition
- OTA data acquisition
- JavaScript-rendered sources
- structured API/XHR extraction when appropriate
- scheduled scraping
- T+1
- T+7
- T+15
- T+30
- T+45 advance purchase windows
- representative route basket
- carrier information
- fare classes
- base fare
- taxes
- airport/user-development fees
- convenience fees
- total fare
- cancellations
- sold-out observations
- missing-data handling
- deduplication
- outlier detection
- normalization
- daily Airfare Price Index
- weekly Airfare Price Index
- monthly Airfare Price Index
- route-level analytics
- lead-time elasticity
- sector heatmaps
- historical trends
- API access
- dashboard support
- DGCA comparison
- 30-day backtesting capability
- auditability
- source health
- observability
- ethical scraping
- rate limiting
- robots.txt awareness
- testing
- documentation

==================================================
ARCHITECTURE COMPLIANCE
==================================================

Follow the architecture defined in docs/.

Preserve the documented boundaries between areas such as:

- scraping
- source adapters
- domain models
- normalization
- data quality
- persistence
- scheduling
- orchestration
- index computation
- API
- observability
- backtesting
- dashboard integration
- infrastructure
- configuration
- testing

The exact names and package boundaries in docs/ take precedence.

Do not create duplicate versions of existing abstractions.

Before creating any new:

- model
- service
- repository
- utility
- adapter
- configuration
- exception
- client
- schema

search the repository for an existing equivalent.

Reuse existing abstractions where appropriate.

==================================================
FOLDER SKELETON RULE
==================================================

The folder skeleton already created from the architecture MUST be preserved.

Do not delete empty architectural folders simply because they are not yet used.

Instead progressively implement the responsibilities assigned to them.

Example principle:

folder exists
   ↓
read architecture responsibility
   ↓
implement correct module
   ↓
wire into system
   ↓
test

Do NOT create:

src2/
new_backend/
final_backend/
scraper_v2/
utils_new/

or similar parallel architectures.

There must be ONE coherent system.
==================================================
REFERENCE IMPLEMENTATION BRANCH
==================================================

There is another Git branch in this repository that contains an earlier
implementation and frontend work.

Treat that branch as a REFERENCE / INSPIRATION SOURCE only.

Before implementation:

1. inspect available branches
2. identify the branch containing the prior implementation/frontend
3. inspect its code, UI, architecture, components, API patterns, schemas,
   workflows, styling, and useful implementation ideas

Use that branch to learn from:
- existing frontend design
- dashboard components
- page layouts
- charts
- UX patterns
- API usage
- data models
- scraper-related work
- helper utilities
- reusable components
- previous implementation decisions

However:

- DO NOT blindly copy the branch
- DO NOT merge it automatically
- DO NOT switch the project architecture to match that branch
- DO NOT let that branch override ps.md or docs/
- DO NOT copy known technical debt or broken abstractions
- DO NOT introduce duplicate implementations

Priority remains:

ps.md
    ↓
approved docs/ architecture
    ↓
current implementation plan
    ↓
reference branch

If a useful implementation exists in the reference branch:

1. understand what it does
2. compare it with the approved architecture
3. reuse or adapt it only if compatible
4. place it in the correct folder/module defined by docs/
5. refactor it where necessary to meet current standards
6. add/update tests

For frontend work especially, use the reference branch as inspiration for:

- overall visual direction
- dashboard layout
- reusable components
- charts
- navigation
- responsive behavior
- interaction patterns

But implement the final frontend according to the current architecture
and requirements.

Before reusing code from the reference branch, check:

- does an equivalent already exist on the current branch?
- does it fit the documented architecture?
- does it introduce stale dependencies?
- does it use outdated schemas or APIs?
- does it have tests?
- does it create duplicate business logic?

Document important reused/adapted ideas in:

docs/decisions.md

with notes such as:

Reference branch component:
What was reused:
What was changed:
Why:
==================================================
SCRAPING ENGINE
==================================================

Implement the scraping architecture described in docs/.

The scraper design may be inspired by:

https://github.com/D4Vinci/Scrapling

but the project itself must remain specialized for airfare collection.

Do NOT clone Scrapling.

Use ideas only where appropriate, such as:

- fetcher abstraction
- HTTP fetch
- browser fetch
- structured response handling
- session lifecycle
- retry policies
- rate limiting
- request/response abstractions
- source-specific adapters
- parser isolation
- configuration
- exception hierarchy
- source health
- adaptive parsing concepts where justified
- concurrency control

Prefer structured data/API/XHR extraction over brittle DOM parsing
when legally and technically appropriate.

Use DOM extraction when necessary.

Every source implementation should remain isolated behind an adapter.

For example conceptually:

SourceAdapter
    |
    +-- request/search builder
    +-- fetch strategy
    +-- response parser
    +-- source normalization
    +-- source policy
    +-- health reporting

The rest of the application must not know source-specific HTML selectors.

==================================================
ETHICAL SCRAPING
==================================================

The system must NOT depend upon defeating security controls.

Implement compliant mechanisms such as:

- per-domain rate limiting
- exponential backoff
- retries
- session persistence
- robots.txt awareness
- configurable source policies
- request throttling
- graceful failure
- blocked-source detection
- source health tracking
- circuit breakers where architecture requires them

Do not implement CAPTCHA-breaking mechanisms.

Do not build security-control bypasses.

Proxy abstractions may exist where documented, but they should remain
configurable infrastructure rather than hard-coded evasion logic.

==================================================
CANONICAL DOMAIN MODEL
==================================================

Use the canonical models specified in docs/.

All sources must eventually produce the same normalized representation.

Important concepts likely include:

AirfareQuote
FlightSegment
Route
Carrier
FareComponent
SearchContext
AdvancePurchaseWindow
SourceMetadata
ScrapeMetadata
IndexObservation
IndexValue
QualityFlag
SourceHealthMetric

Do not expose source-specific raw structures beyond the acquisition layer.

Preserve raw observations separately from normalized data.

==================================================
RAW DATA MUST BE PRESERVED
==================================================

Never destructively transform the only copy of scraped data.

The architecture must maintain the flow:

source response
    ↓
raw observation
    ↓
validation
    ↓
normalization
    ↓
quality checks
    ↓
canonical observation
    ↓
index computation

Maintain lineage between:

index value
→ normalized observation
→ raw observation
→ scrape job
→ source

A computed index should be auditable.

==================================================
DATABASE
==================================================

Implement the persistence architecture exactly as specified in docs/.

Use migrations.

Do not create schema dynamically at runtime as the primary production mechanism.

Implement:

- correct primary keys
- foreign keys
- uniqueness constraints
- indexes
- timestamps
- audit fields
- source metadata
- scrape-job metadata
- raw quote storage
- normalized quote storage
- index storage
- quality flags
- backtest results
- source health

Use JSON/JSONB only where flexible raw metadata is appropriate.

Prefer typed relational columns for fields involved in:

- filtering
- joins
- aggregation
- indexing
- price calculations

==================================================
IDEMPOTENCY
==================================================

The pipeline must be safe to retry.

Repeated execution of the same logical scrape job must not accidentally
create uncontrolled duplicate observations.

Design and use stable uniqueness semantics.

Implement deduplication according to the architecture.

==================================================
SCHEDULER / ORCHESTRATION
==================================================

Implement scraping jobs across relevant dimensions such as:

route
× source
× travel date
× purchase window

Support:

T+1
T+7
T+15
T+30
T+45

Follow the scheduler design from docs.

Implement:

- job creation
- retries
- timeout handling
- concurrency control
- per-source limits
- failure recording
- manual reruns
- idempotency
- source disabling
- recovery after worker restart

Do not introduce Kafka or additional distributed infrastructure
unless the approved architecture explicitly requires it.

==================================================
INDEX ENGINE
==================================================

Keep index computation independent from scraping.

Conceptually:

scraping
   ↓
normalized observations
   ↓
index engine

The index engine must operate from canonical stored observations,
not directly from website responses.

Implement architecture for:

- daily index
- weekly index
- monthly index
- route-level aggregation
- carrier analysis
- purchase-window analysis
- weights
- base period
- missing observations
- data-quality exclusions
- backtesting

IMPORTANT:

Do NOT invent official NSO/DGCA statistical methodology.

Where ps.md or the docs indicate that official route weights or formulas
must be provided externally, keep them configurable and document the dependency.

==================================================
API
==================================================

Implement the API architecture documented in docs.

Keep layers separated:

router
   ↓
service
   ↓
repository/domain
   ↓
database

Do not place business logic directly in route handlers.

Endpoints should cover the documented system capabilities, including where specified:

- routes
- fares
- fare history
- latest observations
- daily index
- weekly index
- monthly index
- heatmap data
- lead-time curves
- source health
- scrape jobs
- data freshness
- backtesting results

Use:

- request validation
- response schemas
- proper HTTP status codes
- centralized exception handling
- structured errors
- pagination where appropriate

==================================================
CONFIGURATION
==================================================

Centralize configuration.

Use environment variables for deployment-specific values.

Do not hard-code:

- database URLs
- passwords
- API credentials
- tokens
- source credentials
- proxy credentials
- deployment-specific hosts

Maintain an example environment configuration.

Never commit real secrets.

==================================================
OBSERVABILITY
==================================================

Implement the observability strategy from docs.

At minimum make important operations measurable.

Track things such as:

- scrape success
- scrape failure
- latency
- HTTP status
- parser failure
- block detection
- records collected
- missing fields
- route coverage
- source health
- data freshness
- index calculation failure

Use structured logging.

Logs should carry contextual fields where practical:

job_id
source
route
travel_date
purchase_window
request_id

Do not scatter random print statements throughout the project.

==================================================
ERROR HANDLING
==================================================

Use meaningful exception hierarchies.

Differentiate failures such as:

network error
timeout
source blocked
rate limited
parser failure
validation failure
normalization failure
database failure
index calculation failure
configuration failure

Errors should contain sufficient context for debugging.

Do not silently swallow failures.

==================================================
TESTING
==================================================

Treat testing as part of implementation.

Do not leave it until the end.

Add tests alongside modules.

Use:

UNIT TESTS
- domain logic
- normalization
- deduplication
- calculations
- utilities

PARSER FIXTURE TESTS
- saved HTML
- saved JSON
- saved XHR/API responses

ADAPTER TESTS
- source request creation
- source parsing
- normalization

DATABASE TESTS
- repository behavior
- constraints
- transactions

PIPELINE TESTS
- raw → normalized

INDEX TESTS
- deterministic synthetic datasets

API TESTS
- success cases
- invalid input
- error handling

INTEGRATION TESTS
- subsystem boundaries

E2E TESTS
- representative end-to-end workflow

Do NOT repeatedly hit production airline websites during unit tests.

Use deterministic saved fixtures.

==================================================
NO FAKE IMPLEMENTATION
==================================================

Do not mark a feature complete if it contains only:

pass

TODO

NotImplementedError

dummy return values

fake successful responses

hard-coded output

unless the placeholder is explicitly required because an external input
such as official statistical weights has not yet been supplied.

If something cannot yet be implemented, document it explicitly.

==================================================
NO TEST CHEATING
==================================================

Never:

- delete failing tests
- weaken assertions
- skip tests merely to obtain green status
- hard-code outputs matching fixtures
- catch all exceptions to hide failures

Fix the implementation.

==================================================
IMPLEMENTATION STRATEGY
==================================================

Do NOT attempt random changes across the repository.

Follow the implementation roadmap in docs.

Implement milestone by milestone.

Before beginning a milestone:

1. read its architecture documentation
2. inspect related code
3. identify dependencies
4. identify required tests
5. confirm existing interfaces

Then implement.

After each milestone:

1. run formatter
2. run lint
3. run type checking
4. run relevant tests
5. inspect failures
6. fix regressions
7. inspect git diff
8. update progress documentation

==================================================
LONG-RUNNING TASK STATE
==================================================

This is a long-horizon implementation task.

Create or maintain:

docs/progress.md
docs/implementation-status.md
docs/decisions.md
docs/test-status.md

Do NOT overwrite approved architecture documentation unnecessarily.

Use these files for implementation state.

progress.md should contain something like:

[x] repository foundation
[x] canonical models
[ ] scraping core
[ ] source adapter 1
[ ] persistence pipeline
[ ] scheduling
[ ] index engine
[ ] API
[ ] dashboard integration
[ ] backtesting
[ ] production verification

Before context compaction or before stopping:

update these files with:

- completed work
- incomplete work
- files changed
- tests run
- failures remaining
- architectural decisions
- exact next action

The next Claude session should be able to continue only by reading repository state.

==================================================
PARALLEL WORK / SUBAGENTS
==================================================

Use subagents when useful for independent analysis.

Examples:

Agent 1:
scraping core and source adapters

Agent 2:
database and persistence review

Agent 3:
index-engine implementation/review

Agent 4:
API architecture and tests

Agent 5:
testing and architecture compliance review

However:

DO NOT allow different subagents to invent competing architectures.

The main agent owns architectural consistency.

Subagents should operate inside existing documented boundaries.

==================================================
QUALITY STANDARD
==================================================

This should look like an industry-grade codebase.

Optimize for:

- clear module boundaries
- maintainability
- observability
- reliability
- testability
- readability
- typed interfaces
- deterministic behavior
- auditability
- extensibility
- minimal coupling
- explicit dependencies
- safe failure behavior

Avoid:

- god classes
- giant modules
- circular imports
- business logic in API routes
- direct DB calls scattered everywhere
- global mutable state
- duplicated parsing logic
- magic numbers
- hard-coded configuration
- broad `except Exception`
- unnecessary microservices
- premature distributed systems

==================================================
DOCUMENTATION
==================================================

Keep documentation synchronized with implementation.

Where appropriate document:

- package responsibilities
- public interfaces
- environment setup
- database migration workflow
- scraper source onboarding
- scheduler usage
- local development
- testing
- API usage
- deployment
- common failure modes

Do not replace useful architecture docs with autogenerated noise.

==================================================
SOURCE ONBOARDING STANDARD
==================================================

A new airline/OTA should be addable primarily by introducing a new source adapter.

It should NOT require modifying every downstream subsystem.

The architecture should support:

new source
   ↓
adapter
   ↓
canonical AirfareQuote
   ↓
existing pipeline

Validate that this remains true during implementation.

==================================================
FIRST REAL SOURCES
==================================================

Follow the priority order specified in docs.

Do not attempt all airline/OTA sources simultaneously.

Implement and thoroughly validate the first representative sources.

Use them to stabilize the framework before adding more adapters.

==================================================
LOCAL DEVELOPMENT
==================================================

The project should be easy for another developer to run.

Provide working commands for:

environment setup
database startup
migrations
API startup
worker/scheduler startup
tests
lint
typecheck

If Docker Compose is part of the architecture, ensure it actually works.

==================================================
VERIFICATION LOOP
==================================================

For every major feature:

implement
   ↓
run test
   ↓
failure?
   ├── yes → diagnose → fix → rerun
   └── no
        ↓
integration test
        ↓
inspect diff
        ↓
continue

Do not consider code complete because it compiles.

==================================================
FINAL VERIFICATION
==================================================
REFERENCE BRANCH COMPARISON

Before finishing:

- compare current implementation against the reference branch
- ensure any clearly useful feature/component has either:
  - been appropriately reused/adapted, or
  - been intentionally rejected with a documented reason
- ensure no important frontend capability was accidentally lost
- ensure reused code follows the current architecture
- ensure no stale API contracts from the reference branch remain
Before declaring the entire task complete:

1. inspect the complete repository tree

2. compare implementation against ps.md

3. compare implementation against docs/

4. verify every architectural package has its intended responsibility

5. identify unused skeleton modules

6. ensure there are no parallel duplicate architectures

7. search for:
   TODO
   FIXME
   pass
   NotImplementedError
   placeholder
   mock production behavior

8. run formatting

9. run linting

10. run type checking

11. run all unit tests

12. run integration tests

13. run API tests

14. run database tests

15. run index tests

16. run scraper fixture tests

17. run build/startup checks

18. verify migrations from a clean database

19. verify API startup

20. verify worker/scheduler startup

21. verify at least one complete pipeline:

source fixture/mock permitted source response
        ↓
scrape
        ↓
raw observation
        ↓
normalization
        ↓
database
        ↓
index calculation
        ↓
API response

22. inspect final git diff

23. remove debug code

24. remove dead code

25. update implementation documentation

==================================================
ARCHITECTURE COMPLIANCE REVIEW
==================================================

Before finishing, perform a final adversarial review.

Ask:

- Did we actually follow docs/?
- Did we accidentally invent another architecture?
- Can individual scraper sources fail independently?
- Can a parser change without affecting index logic?
- Can raw data be replayed?
- Can index values be traced back to observations?
- Are jobs idempotent?
- Can we detect stale sources?
- Can parsers be tested offline?
- Can a new airline be added using only an adapter?
- Can another developer understand the repository?
- Is anything unnecessarily complex for SIH?
- Is anything critical missing?
- Will the project demo reliably?

Fix issues found during this review.

==================================================
IMPORTANT GIT RULES
==================================================

Never:

git reset --hard
git clean -fd
git push --force
rewrite shared git history

without explicit permission.

Do not discard existing user work.

Inspect git status frequently.

==================================================
FINAL RESPONSE
==================================================

When the implementation is genuinely complete, provide:

1. implementation summary

2. architecture implemented

3. major modules completed

4. repository tree summary

5. database implementation

6. scraper implementation

7. sources implemented

8. index-engine implementation

9. API implementation

10. scheduler/orchestration implementation

11. observability implementation

12. tests added

13. test results

14. commands needed to run the project

15. known limitations

16. requirements still dependent on external official data

17. remaining TODOs, if any

18. architecture deviations, if any, and why

19. exact next recommended engineering milestone

==================================================
BEGIN
==================================================

Start by reading:

@ps.md

and ALL relevant documents under:

/home/logan78/Desktop/airfare-index-bot/docs

Then inspect the current codebase.

DO NOT modify code until you have mapped the approved architecture to
the existing repository and understand the implementation order.

After that, begin implementing according to the documented roadmap.

Continue autonomously through the implementation milestones.

Do not stop after producing a plan.

The objective is a working, tested implementation of the approved
SIH 26056 architecture.