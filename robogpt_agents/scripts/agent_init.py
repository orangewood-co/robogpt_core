#!/usr/bin/env python3
import sys
import traceback
import logging
import prompt  #type: ignore

logging.basicConfig(
    level=logging.ERROR,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def main():
    try:
        prompt.main()
    except Exception as ex:
        logger.error(f"Error in agent initialization: {ex}")
        logger.error(traceback.format_exc())
        sys.exit(1)

if __name__ == "__main__":
    main()