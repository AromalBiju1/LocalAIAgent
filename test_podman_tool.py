import sys
import os

# Ensure src is in path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

try:
    from src.tools.podman_tool import PodmanTool
    print("Imported PodmanTool")
    tool = PodmanTool()
    print(f"Instantiated {tool.name}")
except Exception as e:
    print(f"ERROR: {e}")
