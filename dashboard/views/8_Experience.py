"""Q02 layout; no real data access without per-query preview authorization."""
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from components.analytics_views import pending_page
pending_page("Q02")
