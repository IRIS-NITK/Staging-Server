import os
import sys

suffix = sys.argv[1]
current_path = os.path.dirname(os.path.abspath(__file__))
config_path = os.path.join(current_path, "configs", f"dev-{suffix}.conf")

if os.path.exists(config_path):
    os.remove(config_path)
