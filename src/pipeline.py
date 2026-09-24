from logger import logger

from ingestion.ingest import ingest
from processing.transform import transform
from analytics.quality_check import quality_check
from analytics.build_gold import build_gold

logger.info("=" * 40)
logger.info("DATA LAKE PIPELINE")
logger.info("=" * 40)

logger.info("[1/4] INGESTION")
ingest()

logger.info("[2/4] TRANSFORMATION")
transform()

logger.info("[3/4] DATA QUALITY")
quality_check()

logger.info("[4/4] GOLD")
build_gold()

logger.info("PIPELINE: SUCCESS")