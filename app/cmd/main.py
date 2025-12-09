from __future__ import annotations
import logging
from app.cmd.pipeline import pipeline


def logging_conf() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s - %(message)s",
    )

def main() -> None:
    logging_conf()
    pipeline()

if __name__ == "__main__":
    main()