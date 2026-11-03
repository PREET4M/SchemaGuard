# SchemaGuard

### Know what breaks before it ships.

SchemaGuard is a local-first database migration rehearsal and
application compatibility verification tool. It helps developers
understand whether a proposed database migration will break the
application queries and data expectations they have explicitly
configured --- before the change reaches deployment.

A migration can execute successfully and still break an application. For
example, removing a database column may be valid SQL, but an older
version of the application may still query that column. SchemaGuard is
designed to expose this kind of compatibility failure by rehearsing the
migration against an isolated copy of a SQLite database and then testing
application query contracts against the migrated schema.

> **Scope:** The current MVP targets SQLite databases. It is a developer
> verification tool, not a production database service, migration
> manager, automatic fixer, or guarantee that every application
> behaviour is safe.

------------------------------------------------------------------------

## The problem

Database migrations change the structure or contents of a database. A
migration may run without a SQL execution error while still making an
application incompatible with the resulting schema.

Examples include:

-   An older application version still queries a column that the
    migration removes.
-   A migration drops a table that is still used by a background job.
-   A new constraint conflicts with existing records.
-   A migration changes data in a way that row counts alone cannot
    reveal.
-   Old and new application versions temporarily coexist during a
    rolling deployment.
-   A rollback cannot reconstruct data that has already been deleted.

Syntax validation and successful migration execution do not, by
themselves, establish application compatibility.

## What SchemaGuard does

SchemaGuard brings several checks into one rehearsal workflow:

1.  Inspects the original SQLite database without modifying it.
2.  Creates a disposable database copy using SQLite's backup API.
3.  Analyses the proposed migration for potentially destructive SQL
    operations.
4.  Executes the migration against the isolated copy.
5.  Replays supplied old- and new-application query contracts against
    the migrated database.
6.  Runs configured data invariants.
7.  Compares the database schema before and after the migration.
8.  Compares selected data properties, including table row counts.
9.  Produces a deterministic, evidence-backed result and downloadable
    reports.

The original database is not the migration execution target.

## How it works

``` text
 SQLite database + proposed migration
                 |
                 v
       Inspect original database
                 |
                 v
      Create isolated database copy
                 |
                 v
       Analyse proposed migration
                 |
                 v
     Execute migration on the copy
                 |
                 v
     +-----------+------------+
     |           |            |
     v           v            v
 Query-contract  Invariant   Schema and
   replay         checks     data comparison
     |           |            |
     +-----------+------------+
                 |
                 v
       Evidence-backed results
                 |
                 v
       JSON and Markdown reports
```

If migration execution fails, post-migration checks are recorded as not
run/skipped rather than being reported as passed.

## Example: a migration succeeds but an old query breaks

Imagine an application has a `users` table with an `email` column.

A developer proposes this migration:

``` sql
ALTER TABLE users DROP COLUMN email;
```

The migration may execute successfully. However, an older application
version may still run this query:

``` sql
SELECT id, name, email
FROM users
WHERE id = 1;
```

After the migration, the query fails because `users.email` no longer
exists.

SchemaGuard is designed to make this failure visible:

-   The migration execution result is reported separately.
-   The old application query contract is marked as failed.
-   The database error and failed contract are shown.
-   The schema diff identifies the removed column.
-   The finding contributes to the overall severity.
-   The result is included in the downloadable evidence report.

This is the central demonstration: **successful migration execution does
not necessarily mean application compatibility.**

## What a developer provides

A rehearsal uses the following inputs:

  -----------------------------------------------------------------------
  Input                               Description
  ----------------------------------- -----------------------------------
  SQLite database                     A supplied `.db`, `.sqlite`, or
                                      `.sqlite3` file, or the built-in
                                      demo database

  Proposed migration                  SQLite migration SQL to rehearse

  Old application contracts           Read-only SQL queries representing
                                      existing application expectations

  New application contracts           Optional read-only SQL queries
                                      representing the updated
                                      application

  Data invariants                     Optional read-only SQL checks that
                                      should return zero violating rows
  -----------------------------------------------------------------------

The MVP does not automatically discover every database query in an
application codebase. Developers provide the query contracts and
invariants they want checked.

## What the developer gets

After a rehearsal, SchemaGuard is designed to present a results view
containing:

-   **Migration execution status** --- whether the migration ran
    successfully on the isolated copy.
-   **Application compatibility** --- the results of configured old- and
    new-application query contracts.
-   **Failed query evidence** --- contract name, query status, database
    error and result metadata where available.
-   **Data invariant results** --- whether each configured invariant
    returned zero rows, one or more violating rows, or an execution
    error.
-   **Schema diff** --- changes to tables, columns, types, nullability,
    primary keys, defaults, indexes and foreign keys.
-   **Data comparison** --- table row counts and selected before/after
    data properties.
-   **Static SQL findings** --- potentially destructive or suspicious
    operations identified during migration analysis.
-   **Evidence-backed severity** --- a transparent categorical result
    derived from configured checks.
-   **Downloadable reports** --- machine-readable JSON and
    human-readable Markdown.

### Reports

Each report is intended to include:

-   Run identifier and timestamp
-   Database filename (not its absolute local path)
-   Migration summary and execution status
-   Static analysis findings
-   Schema differences
-   Old/new query contract results
-   Invariant results
-   Data comparison
-   Severity explanation
-   Known limitations

The JSON report is intended for machine-readable use. The Markdown
report is intended for developer review and sharing.

## Severity and interpretation

SchemaGuard uses deterministic rules rather than an opaque
machine-learning prediction.

  -----------------------------------------------------------------------
  Severity                            Meaning
  ----------------------------------- -----------------------------------
  **CRITICAL**                        Migration execution failed, or a
                                      configured old-application query
                                      contract failed

  **HIGH**                            A configured data invariant failed,
                                      or a material destructive
                                      schema/data change requires review

  **MODERATE**                        A potentially risky static finding
                                      or new-application contract failure
                                      requires review

  **LOW**                             No configured checks failed
  -----------------------------------------------------------------------

A numerical prioritisation score may be shown as secondary information
if implemented. It is a heuristic, not a probability, accuracy measure,
or calibrated estimate.

**A LOW result does not mean the migration is guaranteed safe.** It
means no configured checks failed. SchemaGuard can only evaluate the
migration, query contracts and invariants that were supplied and
successfully checked.

## Core capabilities

### 1. Isolated migration rehearsal

-   Opens the original database read-only.
-   Creates a unique temporary working copy using SQLite's backup API.
-   Executes the proposed migration on the copy, not the original.
-   Captures execution status and SQLite errors.
-   Cleans up temporary resources after the rehearsal.

### 2. Static SQL analysis

Uses SQLGlot with the SQLite dialect to parse migration statements and
identify potentially destructive operations, including supported cases
of:

-   `DROP TABLE`
-   `DROP COLUMN`
-   `DELETE`
-   `UPDATE` without a `WHERE` clause
-   `ALTER TABLE`

Static findings are warnings for human review, not automatic proof that
an operation is incorrect. SQLite execution remains the authority on
whether a migration actually runs.

### 3. Application query contracts

Query contracts represent SQL expectations of application versions:

-   `OLD_APP` --- queries used by the existing application that should
    remain executable after the migration.
-   `NEW_APP` --- queries expected by the updated application.

The MVP permits read-only `SELECT` and supported `WITH ... SELECT`
contracts. Query execution is restricted using SQL checks and SQLite's
authorizer. Results record contract status, errors, elapsed time and
result column names. Full result rows are not stored or displayed by
default.

A passing query means it executed; it does not prove that its returned
values are semantically correct or that every application dependency has
been tested.

### 4. Data invariants

An invariant is a read-only SQL query that should return zero rows.

-   **PASS:** the query executes and returns zero rows.
-   **FAIL:** the query executes and returns one or more rows.
-   **ERROR:** the query cannot execute.

For example, this invariant identifies users with missing email values:

``` sql
SELECT id
FROM users
WHERE email IS NULL;
```

The report records the number of violating rows rather than exposing
potentially sensitive row contents.

### 5. Schema and data comparison

The schema comparison covers:

-   Tables and columns
-   Column types and nullability
-   Primary keys and defaults
-   Indexes
-   Foreign keys

The MVP data comparison includes table row counts, removed tables,
removed columns and row-count reductions. Optional deterministic hashes
may be added for selected tables if implemented and tested.

Equal row counts do not prove that data is unchanged or correct.

## Technology stack

  Layer                Technology
  -------------------- ---------------------------
  Language             Python 3.11 / 3.12
  Database             SQLite
  Database interface   Python `sqlite3`
  SQL parsing          SQLGlot
  Frontend              Next.js 16, TypeScript
  Styling               Tailwind CSS
  Icons                 Lucide React
  Data processing      Pandas
  Charts               Plotly
  Testing              Pytest
  Version control      Git and GitHub
  Frontend hosting      Vercel

The MVP uses a Next.js frontend built with TypeScript, Tailwind CSS and
Lucide React icons. The frontend provides the user interface while the
Python modules handle the database rehearsal and verification logic.

## Project architecture

``` text
schemaguard/
├── frontend/
│   ├── package.json
│   ├── next.config.ts
│   ├── tsconfig.json
│   ├── src/
│   │   ├── app/
│   │   └── components/
│   └── public/
├── requirements.txt
├── README.md
├── WORKFLOW.md
├── .gitignore
├── .python-version
├── assets/
│   └── logo.svg
├── data/
│   └── demo/
│       ├── ecommerce.db
│       ├── migrations/
│       ├── contracts/
│       └── invariants/
├── schemaguard/
│   ├── config.py
│   ├── models.py
│   ├── core/
│   │   ├── analyzer.py
│   │   ├── sandbox.py
│   │   ├── migration_runner.py
│   │   ├── schema_inspector.py
│   │   ├── schema_diff.py
│   │   ├── data_profiler.py
│   │   ├── contract_runner.py
│   │   ├── invariant_runner.py
│   │   ├── risk_engine.py
│   │   └── orchestrator.py
│   ├── reports/
│   │   ├── json_report.py
│   │   └── markdown_report.py
│   └── utils/
│       ├── sql_safety.py
│       └── file_validation.py
└── tests/
    ├── conftest.py
    ├── test_analyzer.py
    ├── test_sandbox.py
    ├── test_migration_runner.py
    ├── test_contract_runner.py
    ├── test_invariants.py
    ├── test_schema_diff.py
    ├── test_risk_engine.py
    └── test_end_to_end.py
```

The exact files may evolve during implementation. Core migration and
verification logic is kept separate from the Next.js frontend.

## Getting started

### Prerequisites

-   Node.js and npm
-   Python 3.11 or 3.12
-   Git
-   Windows, macOS or Linux environment capable of running Node.js,
    Python and SQLite

### Run locally

Clone the repository:

``` bash
git clone https://github.com/<your-username>/schemaguard.git
cd schemaguard
```

Create and activate a virtual environment.

**Windows PowerShell:**

``` powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

**macOS / Linux:**

``` bash
python3 -m venv .venv
source .venv/bin/activate
```

Install dependencies:

``` bash
python -m pip install --upgrade pip
pip install -r requirements.txt
```

Install the frontend dependencies and launch the application:

``` bash
cd frontend
npm install
npm run dev
```

Open the local URL printed in the terminal (typically
`http://localhost:3000`).

> These are the intended setup commands for the project. They assume the
> corresponding application files and dependencies have been implemented
> in the repository.

## Demo scenarios

The project includes a synthetic e-commerce database scenario intended
to demonstrate the main behaviours without requiring real customer data.

  -----------------------------------------------------------------------
  Scenario                Example                 Expected behaviour
  ----------------------- ----------------------- -----------------------
  Safe additive migration Add nullable            Migration executes; old
                          `users.phone`           query remains
                                                  executable

  Breaking migration      Remove `users.email`    Migration may execute;
                                                  old query referencing
                                                  `email` fails

  Invalid migration       Invalid `ALTER TABLE`   Execution failure is
                          statement               recorded;
                                                  post-migration checks
                                                  are not marked passed

  Invariant violation     Create a controlled     Invariant reports one
                          orphaned order          or more violations

  Original database       Hash database before    Original database hash
  immutability            and after rehearsal     remains identical
  -----------------------------------------------------------------------

The demo must show actual SQLite execution and actual test results.
Expected outcomes must not be hardcoded into the application.

## Security and data handling

Database files and SQL supplied to the tool are treated as untrusted
input.

The MVP is designed with the following safeguards:

-   Never execute a migration against the original uploaded database.
-   Open the original database read-only.
-   Use SQLite's backup API to create the rehearsal copy.
-   Use a unique temporary directory for each run.
-   Disable SQLite extension loading where supported.
-   Reject or deny `ATTACH` and `DETACH`.
-   Reject dangerous schema pragmas such as `writable_schema`.
-   Restrict query contracts and invariants to read-only operations.
-   Apply a default upload limit of 25 MB.
-   Validate that uploaded files are actually readable SQLite databases.
-   Do not accept user-controlled destination paths.
-   Close database connections and clean temporary files, including on
    error.
-   Avoid displaying full database rows, local absolute paths or stack
    traces in the UI.
-   Do not commit uploaded databases, credentials or private data.

**Security limitation:** A temporary SQLite copy and SQLite authorizer
are not equivalent to a hardened operating-system sandbox for hostile
code. The hackathon MVP is a local/demo-oriented developer tool, not a
hardened multi-user execution service. Do not use it to process
confidential production databases.

## Testing

Run the test suite from the project root:

``` bash
pytest -q
```

The planned tests cover:

-   Database validation and sandbox isolation
-   Original database immutability
-   Temporary resource cleanup
-   Static SQL analysis
-   Migration execution and failure handling
-   Read-only query contract enforcement
-   Data invariant evaluation
-   Schema and data comparison
-   Severity calculation
-   End-to-end safe, breaking and invalid migration scenarios

A feature should not be considered complete just because code has been
generated. Its acceptance criteria and tests must be run and verified.

## Deployment

The frontend deployment target is [Vercel](https://vercel.com/).

Connect the GitHub repository to Vercel and configure the project to use
the `frontend` directory as its root directory. Uploaded files and
temporary data should be treated according to the configured backend
storage behaviour. Keep the demo database small and synthetic, and do
not promise persistent rehearsal history.

## Current scope and limitations

The MVP deliberately focuses on a narrow, testable problem.

**Included in the MVP scope**

-   SQLite databases only
-   Local-first rehearsal workflow
-   Isolated migration execution
-   SQL static analysis
-   Supplied old/new application query contracts
-   Supplied read-only data invariants
-   Schema and selected data comparison
-   Deterministic severity and evidence reporting
-   JSON and Markdown report generation
-   Next.js 16 frontend built with TypeScript
-   Tailwind CSS styling and Lucide React icons

**Not included in the MVP**

-   PostgreSQL, MySQL or other database engines
-   Automatic discovery of all application database queries
-   Production database connections or credentials
-   Automatic production deployment or rollback
-   Automatic SQL repair
-   AI chatbot or ML-based risk prediction
-   Authentication
-   Billing, team collaboration or hosted run history
-   GitHub Actions / CI integration

These are possible future directions, not claims about current
functionality.

## Roadmap

Potential future extensions, subject to validation and implementation:

-   Support for additional database engines through separate execution
    adapters.
-   Application repository analysis to help discover query dependencies.
-   CI integration to rehearse migrations during pull requests.
-   Integration with existing migration-management workflows.
-   More expressive expected-result contracts for semantic data checks.
-   Team review, policy and audit capabilities.

## Why no machine learning?

SchemaGuard's core verdict is deterministic. It is based on SQL
analysis, actual SQLite execution, configured query contracts,
invariants and schema/data comparisons.

The MVP does not have a validated labelled dataset of migration failures
from which to train a meaningful risk predictor. Introducing an opaque
ML score would make the result harder to explain without establishing
that it is more reliable.

## Project positioning

SchemaGuard complements rather than replaces tools such as Flyway,
Liquibase or Atlas.

Those tools manage database migration workflows. SchemaGuard's MVP
focuses on rehearsing a proposed SQLite migration on an isolated copy
and checking whether supplied application query contracts and data
invariants still hold afterward.

It does not claim to detect every possible migration bug, guarantee zero
data loss, replace migration-management tools, support every SQL
dialect, or prove complete application compatibility.

------------------------------------------------------------------------

## The idea in one sentence

**SchemaGuard helps developers find configured application compatibility
and data integrity failures before a database migration reaches
deployment --- by rehearsing the change on an isolated copy and
reporting evidence of what passed and what broke.**

------------------------------------------------------------------------

## Contributing

Contributions, bug reports and suggestions are welcome. If you report a
bug, include:

-   The SQLite version and Python version.
-   A minimal synthetic database or reproducible scenario.
-   The migration SQL used.
-   The relevant query contract or invariant.
-   The observed error and expected behaviour.

Never attach production databases, credentials or confidential customer
data to an issue.

## License

A license has not yet been specified. Add a `LICENSE` file before
presenting the project as open source.

------------------------------------------------------------------------

```{=html}
<p align="center">
```
`<strong>`{=html}SchemaGuard --- Know what breaks before it
ships.`</strong>`{=html}
```{=html}
</p>
```
