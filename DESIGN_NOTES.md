# Assumptions, Design Notes, and Open Questions

This document captures design assumptions and questions that would normally be clarified
in a real production environment, but are left implicit in the technical task.

---

## 1. Service Catalog semantics (Jira, Salesforce, Zoom, etc.)

The Service Catalog defines:

- `Software & Licensing / SaaS Platform Access (Jira/Salesforce)` with SLA 8 hours.
- `Software & Licensing / Other Software Issue` with SLA 24 hours.

Open questions I would clarify in production:

- Is `SaaS Platform Access (Jira/Salesforce)` intended to be generic for all core SaaS tools
  (Jira, Salesforce, Zoom, Slack, etc.), or is it literally scoped to Jira and Salesforce only?
- How should incidents for SaaS products that are not explicitly named in the catalog be handled?
  - Should they reuse the same request type (and SLA) as Jira/Salesforce?
  - Or should they fall under a generic bucket such as `Other Software Issue` until the catalog is extended?
- Who owns the Service Catalog and how are new applications (e.g. Zoom) added with their own
  request types and SLAs?

### Concrete assumptions for this task

- Incidents that explicitly mention Jira or Salesforce (including outages like "Jira is down")
  are mapped to:
  - `request_category`: `Software & Licensing`
  - `request_type`: `SaaS Platform Access (Jira/Salesforce)`
  - `sla_unit` / `sla_value`: as defined in the catalog (`hours`, `8`).

- For the "Zoom not working" request, the long description says:
  > "Camera isn't detected in Zoom."

  I treat this as an endpoint/device/configuration issue (camera, drivers, permissions),
  not as a SaaS availability or access problem. Zoom is not explicitly mentioned in the Service
  Catalog, and the issue description is about the local camera rather than Zoom itself being down
  or an access-provisioning request.

  Therefore, I classify it as:
  - `request_category`: `Software & Licensing`
  - `request_type`: `Other Software Issue`
  - `sla_unit` / `sla_value`: `hours`, `24`.

This is consistent with the catalog as written and avoids overloading
`SaaS Platform Access (Jira/Salesforce)` with unrelated products.

---

## 2. Idempotency and repeated runs

The task does not define behavior for repeated pipeline runs. In reality, I would clarify:

- Should the pipeline be idempotent with respect to helpdesk requests (e.g. never re-classify
  the same ticket twice)?
- Should we avoid re-sending the same report multiple times, or is resending acceptable?

In this implementation:

- I added a simple SQLite-based report log that tracks which Excel reports have been sent.
- On startup, the pipeline:
  - Scans the `output/` directory.
  - Collects all Excel reports that are not yet logged as sent.
  - If unsent reports exist, it sends them all in a single email and does not:
    - call the Helpdesk API, or
    - call the LLM.
- Only when there are no unsent reports does the pipeline fetch fresh data and classify tickets.

In a real system, I would additionally consider idempotency at the level of ticket IDs and
potentially store classification status in a database.

---

## 3. Pre-filled fields vs Service Catalog as source of truth

The task states:

> Using LLM API, assign the request_category, request_type, and sla fields that are empty/zero.

Open questions:

- What if a ticket already has a category/request type or SLA that does not match the current Service Catalog?

For this technical task I assume:

- The LLM only fills fields that are empty or zero.
- Existing non-empty values are treated as authoritative and are not overwritten.
- SLA values are taken from the catalog when a catalog match exists; otherwise, a best-effort SLA is chosen.

In production, I would likely add:

- Validation to detect discrepancies between existing classifications and the Service Catalog.
- Reporting to highlight conflicting SLAs or outdated categories.

---

## 4. Error handling and degradation strategy

The task does not define behavior when external services fail:

- Helpdesk API unavailable or returning errors.
- Service Catalog endpoint unreachable.
- LLM API timing out or returning invalid JSON.

In this implementation:

- External calls are wrapped in project-specific exceptions (e.g. `HelpdeskAPIError`, `ServiceCatalogError`,
  `LLMClassificationError`).
- Failures are logged with enough context (URLs, IDs, batch indices).
- For LLM classification:
  - If a batch fails, the error is logged.
  - The raw requests in that batch are still carried forward to the Excel report so that the pipeline
    remains usable, but they are not artificially filled with guessed data.

In a real system, I would align with stakeholders on a clear degradation policy:

- Whether to persist “raw” tickets without classification.
- Whether to partially send reports with only successfully classified tickets.
- When to fail fast vs. continue with partial data.

---

## 5. Classification quality and validation

The task does not define any explicit quality metrics (accuracy, precision) or manual review process.

In production I would expect:

- A way to store both original and proposed classifications.
- A sampling process (e.g. reviewing 5–10% of tickets) for manual validation.
- Feedback loops to adjust prompts, refine rules, or update the Service Catalog.

The current implementation focuses on:

- Deterministic mapping to the Service Catalog via a strict prompt.
- Ensuring the LLM always returns a valid JSON structure that can be parsed and mapped
  into domain models.

The clean architecture (domain / application / infrastructure / entrypoint) makes it straightforward
to introduce additional validation or post-processing layers later.

---

## 6. Excel report structure and scope

The task specifies:

- Output must be a `.xlsx` file.
- Headers should be bold.
- Columns should be auto-fitted.
- Sorting: `request_category` (asc), `request_type` (asc), `short_description` (asc).

Open questions for a production system:

- Should we include timestamps (ticket creation time, classification time) in the report?
- Should we show both the original SLA (if present) and the normalized SLA from the catalog?
- Do we need technical fields such as:
  - LLM model name and version.
  - LLM response time.
  - A success flag for classification.

For the technical task I kept the Excel report focused on:

- `raw_id`
- `request_category`
- `request_type`
- `short_description`
- `sla_value`
- `sla_unit`

with basic formatting and the requested sorting.

---

## 7. Security and confidentiality

The solution uses an external LLM (Gemini) and sends real ticket text to an external API.

In this repository:

- All credentials (Helpdesk API, LLM API key, SMTP password) are loaded from environment
  variables and not committed to the repository.
- The pipeline can be fully configured via `.env`/environment.

In a real environment, I would clarify:

- Whether it is allowed to send raw ticket content (which may contain PII or sensitive business data)
  to an external LLM provider.
- Whether we need to anonymize or mask certain fields (e.g. email addresses, names, internal IDs)
  before sending them to the LLM.
- Whether full ticket payloads may be logged, or only minimal metadata should be stored in logs.

---

## 8. LLM behavior and configuration

The task does not specify requirements for determinism or reproducibility of classifications.

In this implementation:

- The prompt enforces a strict JSON schema and instructs the model to:
  - Use category/request_type names verbatim from the Service Catalog.
  - Always return the exact SLA from the catalog for the chosen request type (including 0).
  - Prefer specific request types over generic “Other … Issue” buckets when a clear match exists.

The design assumes that:

- LLM parameters (temperature, max tokens, etc.) can be tuned per environment.
- The LLM client (Gemini 2.5 Pro in this implementation) can be swapped for another provider
  without changing the domain or application layers.

This keeps LLM-specific concerns isolated in the infrastructure layer, as per the clean architecture.