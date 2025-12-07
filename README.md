# Automated Ticket Attribution

Project implements a small automation pipeline that simulates
automatic classification of IT helpdesk tickets based on an IT Service Catalog.

The goal is to:
- Fetch raw helpdesk requests from a webhook.
- Fetch the Service Catalog.
- Use an LLM to classify tickets into `request_category`, `request_type`, and `sla`.
- Export the final dataset to an Excel report.
- Prepare the report to be sent via email.

---

## Tech Stack

- Python 3.10

---

## Project Structure

```text
automated_ticket_attribution/
  app/
    __init__.py
    config.py
    domain/
      __init__.py
      models.py
    infrastructure/
      __init__.py
      helpdesk_client.py
    application/
      __init__.py
      services.py           # use-cases
  main.py                   # run the project
  requirements.txt
  README.md
