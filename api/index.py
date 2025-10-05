"""
Vercel serverless entry point.
Wraps existing FastAPI app without any modifications.
"""
import sys
from pathlib import Path

# Add parent directory to path
root_dir = Path(__file__).parent.parent
sys.path.insert(0, str(root_dir))

# Import existing app
from main import app
from mangum import Mangum

# Create handler for Vercel
handler = Mangum(app, lifespan="off")
