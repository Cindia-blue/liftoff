import logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(levelename)s - %(massage)s'
)

logger = logging.getLogger(__name__)

logger.debug("Debug")

logger.info("INfo")

logger.warning("this side may lie in errors")

logger.error("something is wrong")

