# Automated Ticket Attribution

Project implements a small automation pipeline that simulates
automatic classification of IT helpdesk tickets based on an IT Service Catalog.

The goal is to:
- Fetch raw helpdesk requests.
- Fetch the Service Catalog.
- Use an LLM to classify tickets into `request_category`, `request_type`, and `sla`.
- Export the final dataset to an Excel report.
- Send the report via email.
- **PS**. Don’t fetch data or call the LLM if there are any unsent reports; resend all unsent reports instead.

---
## Assumptions and open questions

In a real production setup I would clarify a few points about the Service Catalog:

- Whether `SaaS Platform Access (Jira/Salesforce)` is meant to be **generic for all core SaaS tools** or strictly for Jira/Salesforce only.
- How we want to classify incidents for other SaaS products like Zoom, Slack, etc.:
  - Should they reuse the same SaaS request type and SLA?
  - Or should they fall under a more generic `Other Software Issue` until the catalog is extended?
- Who owns the Service Catalog and how new applications (e.g. Zoom) are added with their own request types and SLAs.

For this technical task I assumed:
- For the "Zoom not working" request, the long description says "Camera isn't detected in Zoom".
  I treat this as an endpoint/device/configuration issue (camera/drivers/permissions),
  not as a SaaS availability or access problem. Since Zoom is not explicitly mentioned
  in the Service Catalog and the issue is about the local camera rather than Zoom being
  down or access provisioning, I classify it as `Software & Licensing / Other Software Issue`
  with the corresponding SLA (24 hours).
---
## Tech Stack

- Python 3.10

---
## Project Structure

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