from logger import logger

from ingestion.ingest import ingest
from processing.transform import transform
from analytics.quality_check import quality_check
from analytics.build_gold import build_gold
from processing.build_silver import build_silver

logger.info("[1/5] INGESTION")
ingest()

logger.info("[2/5] TRANSFORMATION")
transform()

logger.info("[3/5] DATA QUALITY")
quality_check()

logger.info("[4/5] SILVER")
build_silver()

logger.info("[5/5] GOLD")
build_gold()

logger.info("PIPELINE: SUCCESS")
