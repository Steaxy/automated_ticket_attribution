from __future__ import annotations
import logging
from typing import Tuple
from app.domain.helpdesk import HelpdeskRequest
from collections.abc import Iterator, Sequence


logger = logging.getLogger(__name__)

# display progress for batches when classify_requests in terminal
def _batches_progress(
        requests_: Sequence[HelpdeskRequest],
        batch_size: int,
) -> Iterator[Tuple[int, int, int, int, list[HelpdeskRequest]]]:
    """Yield batches of requests together with progress metadata.

        Splits the incoming list of requests into batches of size
        ``batch_size`` and logs an info-level message for each batch before it is
        processed by the LLM classifier.

        If there are no requests, logs that the LLM step is skipped and returns
        without yielding anything.
        """

    total_requests = len(requests_)
    if total_requests == 0:
        logger.info("[part 3 and 4] No requests to classify; skipping LLM step")
        return

    total_batches = (total_requests + batch_size - 1) // batch_size

    for batch_index, batch_start in enumerate(range(0, total_requests, batch_size)):
        batch: list[HelpdeskRequest] = list(
            requests_[batch_start: batch_start + batch_size]
        )
        batch_end = batch_start + len(batch) - 1

        logger.info(
            "[part 3 and 4] Sending batch %d/%d to LLM "
            "(%d requests, index %d..%d)...",
            batch_index + 1,
            total_batches,
            len(batch),
            batch_start,
            batch_end,
        )

        yield batch_index, total_batches, batch_start, batch_end, batch