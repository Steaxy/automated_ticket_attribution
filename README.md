# Automated Ticket Attribution

Project implements a small automation pipeline that simulates
automatic classification of IT helpdesk tickets based on an IT Service Catalog.

## Features / Pipeline overview

- Fetch helpdesk requests from the webhook endpoint using API key + secret.
- Fetch the Service Catalog (YAML) from a remote URL.
- Batch requests to the LLM (configurable batch size, default 30).
- Let the LLM fill `request_category`, `request_type`, `sla_unit`, `sla_value` based on the Service Catalog.
- Generate a sorted Excel report with basic formatting.
- Send the report via SMTP to the configured recipient, including a link to the codebase.
- Track sent reports in a SQLite database and resend any unsent reports from the `output/` directory
  before calling the Helpdesk API or the LLM.
- Log all key steps via Python `logging` and provide a simple terminal progress indicator (spinner).
- Covered by unit tests (pytest) and static checks (ruff, mypy).

---
## Assumptions and open questions

This project makes a few pragmatic assumptions about the Service Catalog and LLM behavior.
For a detailed discussion (including Jira vs Zoom classification, idempotency, error handling,
and security considerations), see [`DESIGN_NOTES.md`](DESIGN_NOTES.md).

In short:

- `SaaS Platform Access (Jira/Salesforce)` is treated as specific to Jira and Salesforce,
  not as a generic bucket for all SaaS tools.
- Jira/Salesforce incidents (including outages like "Jira is down") are mapped to
  `Software & Licensing / SaaS Platform Access (Jira/Salesforce)` with the catalog SLA (8 hours).
- Zoom is not present in the Service Catalog. For the "Zoom not working" request, the long
  description says "Camera isn't detected in Zoom". I treat this as an endpoint/device/configuration
  issue (camera/drivers/permissions) rather than a SaaS availability or access problem, so it is
  classified as `Software & Licensing / Other Software Issue` with SLA 24 hours.
---
## Tech Stack

- Python 3.10
- Google Gemini 2.5 Pro (LLM for classification)
- Clean Architecture (domain / application / infrastructure / entrypoint)

---
## Structure

```text
automated_ticket_attribution/
  app/
    cmd/
        main.py             # run app
    domain/                 # models
    infrastructure/         # integrations
    application/            # use-cases
    shared/
    config.py
  tests/
  output/
  requirements.txt
  requirements-dev.txt
  LICENSE
  Makefile
  README.md
```
---
## Setup

### prod
```bash
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```
### dev
```bash
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -r requirements-dev.txt
```
### local .env
```bash
HELPDESK_API_URL
HELPDESK_API_KEY
HELPDESK_API_SECRET
SERVICE_CATALOG_URL
LLM_MODEL_NAME
LLM_API_KEY
LLM_BATCH_SIZE
LLM_DELAY_BETWEEN_BATCHES
EMAIL_SMTP_HOST
EMAIL_SMTP_PORT
EMAIL_USE_TLS
EMAIL_USERNAME
EMAIL_PASSWORD
EMAIL_SENDER
EMAIL_RECIPIENT
CANDIDATE_NAME
REPORT_LOG_DB_PATH
```
--- 
## How to Run

From the project root:

```bash
make run        # run the app
make test       # run unit tests (pytest)
make lint       # lint with ruff
make type-check # static type checking with mypy
make excel      # build example excel file
```
## License

Source-available, non-commercial.  
You can read and run this code for evaluation, but you may not use it in production
or for commercial purposes without my written permission.