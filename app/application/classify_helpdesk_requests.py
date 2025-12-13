from __future__ import annotations
import logging
from typing import Protocol, Mapping
from app.domain.helpdesk import HelpdeskRequest
from app.domain.service_catalog import ServiceCatalog
from app.application.llm_classifier import LLMClassificationResult, LLMClassificationError
from app.application.classify_helpdesk_requests_progress import _batches_progress
from collections.abc import Sequence
from app.application.service_catalog_matcher import ServiceCatalogMatcher


logger = logging.getLogger(__name__)

class RequestClassifier(Protocol):
    def classify_batch(
        self,
        requests: Sequence[HelpdeskRequest],
        service_catalog: ServiceCatalog,
    ) -> Mapping[str, LLMClassificationResult]:
        ...


def classify_requests(
        classifier: RequestClassifier,
        service_catalog: ServiceCatalog,
        requests_: Sequence[HelpdeskRequest],
        batch_size: int,
        examples_to_log: int = 3,
) -> list[HelpdeskRequest]:
    if not requests_:
        logger.info("[part 3 and 4] No helpdesk requests provided; skipping LLM step")
        return []

    matcher = ServiceCatalogMatcher(service_catalog)

    classified_requests: list[HelpdeskRequest] = []
    logged_examples = 0

    for _, _, batch_start, _, batch in _batches_progress(requests_, batch_size):
        try:
            batch_results = classifier.classify_batch(batch, service_catalog)
        except LLMClassificationError as exc:
            logger.error(
                "LLM batch classification failed for requests %d..%d: %s",
                batch_start,
                batch_start + len(batch) - 1,
                exc,
            )
            # if the batch call fails, still include the raw requests in Excel
            classified_requests.extend(batch)
            continue

        # compute end index once
        batch_end_index = batch_start + len(batch) - 1
        logger.info(
            "[part 3 and 4] LLM batch classified %d requests (index %d..%d)",
            len(batch),
            batch_start,
            batch_end_index,
        )

        set_category_count = 0
        set_type_count = 0
        missing_result_count = 0
        rejected_pair_count = 0

        for req in batch:
            id = req.id or ""
            result = batch_results.get(id)

            if result is None:
                missing_result_count += 1
                classified_requests.append(req)
                continue

            # resolve to canonical catalog strings using both current + LLM suggestion
            candidate_category = req.request_category or result.request_category
            candidate_type = req.request_type or result.request_type
            resolved = matcher.resolve(candidate_category, candidate_type)

            if resolved is None:
                # do not write non-catalog values (avoid breaking SLA lookup later)
                rejected_pair_count += 1
            else:
                # write back canonical catalog casing/spaces
                if not req.request_category:
                    req.request_category = resolved.request_category
                    set_category_count += 1

                if not req.request_type:
                    req.request_type = resolved.request_type
                    set_type_count += 1

            if logged_examples < examples_to_log:
                logger.info(
                    # log both raw and resolved for check canonicalization
                    "[part 3 and 4] LLM result for %s: raw_category=%r raw_type=%r resolved=%r",
                    req.id,
                    result.request_category,
                    result.request_type,
                    None if resolved is None else (resolved.request_category, resolved.request_type),
                )
                logged_examples += 1

            classified_requests.append(req)

        # log summary if SLA was set from service catalog
        logger.info(
            "[part 3] Applied LLM classification: categories_set=%d types_set=%d missing_results=%d rejected_pairs=%d (batch %d..%d)",
            set_category_count,
            set_type_count,
            missing_result_count,
            rejected_pair_count,
            batch_start,
            batch_end_index,
        )

    return classified_requests