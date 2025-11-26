"""Debug script to inspect registered routes in the FastMCP app."""
import sys
import os

# Add src to path so we can import server
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from server import app

print("=== Inspecting FastMCP App Routes ===\n")

# Check if app has routes attribute
if hasattr(app, 'routes'):
    print(f"Total routes: {len(app.routes)}\n")
    for route in app.routes:
        print(f"Path: {route.path}")
        if hasattr(route, 'methods'):
            print(f"  Methods: {route.methods}")
        if hasattr(route, 'name'):
            print(f"  Name: {route.name}")
        print()
else:
    print("App doesn't have 'routes' attribute")
    print(f"App type: {type(app)}")
    print(f"App attributes: {dir(app)}")
