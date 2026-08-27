import sys
import os

# Add root directory to sys.path
root_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if root_dir not in sys.path:
    sys.path.insert(0, root_dir)

from dashboard import app

# Expose WSGI handler for Vercel
handler = app
app = app

if __name__ == "__main__":
    app.run()
