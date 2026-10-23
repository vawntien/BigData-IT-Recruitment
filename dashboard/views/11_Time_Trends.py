"""Q08 separate timestamp-basis layout; no implicit artifact reading."""
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from components.analytics_views import pending_page
pending_page("Q08")
