"""Q04 independent work-type and remote sections; real preview still blocked."""
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from components.analytics_views import pending_page
pending_page("Q04")
