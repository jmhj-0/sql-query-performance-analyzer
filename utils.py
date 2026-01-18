from typing import Union
import logging

logger = logging.getLogger(__name__)


def parse_version(version: str) -> Union[float, int]:
    """Parse version string to float or int."""
    if version == 'latest':
        return float('inf')
    try:
        return float(version)
    except ValueError:
        # Assume major.minor, take major
        return int(version.split('.')[0])


def setup_logging(level: str = 'INFO') -> None:
    """Setup logging configuration."""
    logging.basicConfig(
        level=getattr(logging, level.upper()),
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )