from __future__ import annotations
from app.domain.helpdesk import HelpdeskRequest
from app.domain.service_catalog import ServiceCatalog
import logging


logger = logging.getLogger(__name__)

def fill_helpdesk_sla(requests: list[HelpdeskRequest], catalog: ServiceCatalog) -> None:
    """Fill missing SLA fields in-place using the Service Catalog.

        For each request that has both ``request_category`` and ``request_type`` set,
        this function looks up an exact (category, request_type) match in the Service
        Catalog and fills SLA fields that are missing.

        A field is considered missing when:
        - ``sla_unit`` is None or an empty/whitespace string
        - ``sla_value`` is None or 0

        Existing non-missing SLA values are not overwritten.
        """

    logger.info(
        "Filling missing SLA for %d requests using Service Catalog",
        len(requests),
    )

    filled_requests = 0
    filled_unit_count = 0
    filled_value_count = 0
    unknown_pair_count = 0
    skipped_already_has_sla_count = 0
    sample_logged = 0
    sample_limit = 5

    # Build (category, request_type) -> (unit, value) index from catalog
    sla_index: dict[tuple[str, str], tuple[str, int]] = {}
    for cat in catalog.categories:
        for req_type in cat.requests:
            sla_index[(cat.name, req_type.name)] = (req_type.sla.unit, req_type.sla.value)

    for req in requests:
        if not req.request_category or not req.request_type:
            continue

        key = (req.request_category, req.request_type)
        if key not in sla_index:
            # don't warn for each request. Count and summarize.
            unknown_pair_count += 1
            continue

        missing_unit = req.sla_unit is None or not req.sla_unit.strip()
        missing_value = req.sla_value is None or req.sla_value == 0

        if not (missing_unit or missing_value):
            # track already-set SLA to see how much requests were did
            skipped_already_has_sla_count += 1
            continue

        unit, value = sla_index[key]

        changed = False

        # fill only missing parts; do not overwrite existing non-missing values
        if missing_unit:
            req.sla_unit = unit
            filled_unit_count += 1
            changed = True

        if missing_value:
            req.sla_value = value
            filled_value_count += 1
            changed = True

        if changed:
            filled_requests += 1

            # log only first N examples at INFO
            if sample_logged < sample_limit:
                logger.info(
                    "[part 4] SLA derived from Service Catalog for request %s: category=%r type=%r -> %r %r",
                    req.id,
                    req.request_category,
                    req.request_type,
                    req.sla_value,
                    req.sla_unit,
                )
                sample_logged += 1

            logger.debug(
                "Derived SLA from Service Catalog for request %s: unit=%r value=%r",
                req.id,
                req.sla_unit,
                req.sla_value,
            )

    # log summary if SLA was set from service catalog
    logger.info(
        "[part 4] SLA derivation summary: filled_requests=%d filled_unit=%d filled_value=%d "
        "unknown_pairs=%d skipped_already_has_sla=%d",
        filled_requests,
        filled_unit_count,
        filled_value_count,
        unknown_pair_count,
        skipped_already_has_sla_count,
    )

    # show a warning if there were unknown pairs
    if unknown_pair_count > 0:
        logger.warning(
            "[part 4] SLA could not be derived for %d request(s) due to unknown (category, type) pairs",
            unknown_pair_count,
        )