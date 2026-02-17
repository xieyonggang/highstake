import os
import glob
import sys

# Mimic the logic in agent_engine.py
# Assuming this script is run from server/ root

# Assuming agent_engine.py location
agent_engine_path = "app/services/agent_engine.py"
abs_path = os.path.abspath(agent_engine_path)
print(f"Simulated agent_engine path: {abs_path}")

base_dir = os.path.dirname(os.path.dirname(abs_path))
print(f"base_dir: {base_dir}")

resources_dir = os.path.join(base_dir, "resources")
print(f"resources_dir: {resources_dir}")

common_assets_dir = os.path.join(resources_dir, "common_assets")
print(f"common_assets_dir: {common_assets_dir}")

moderator_pattern = os.path.join(common_assets_dir, "moderator*.wav")
print(f"moderator_pattern: {moderator_pattern}")

moderator_files = glob.glob(moderator_pattern)
print(f"Found files: {moderator_files}")

if moderator_files:
    moderator_files.sort()
    selected_file = moderator_files[0]
    rel_path = os.path.relpath(selected_file, resources_dir)
    rel_path = rel_path.replace(os.sep, '/')
    audio_url = f"/api/resources/{rel_path}"
    print(f"Audio URL: {audio_url}")
else:
    print("No files found!")
