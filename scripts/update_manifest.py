"""
Update MANIFEST.json with SHA-256 hashes of all model files.
Run after training or modifying any .pkl files.
"""
import hashlib
import json
import os

MODEL_DIR = os.path.join(os.path.dirname(__file__), '..', 'pomodoro', 'ml', 'models')
MANIFEST_PATH = os.path.join(MODEL_DIR, 'MANIFEST.json')

MODEL_FILES = ['routine_suggestion.pkl', 'scaler.pkl', 'poly_features.pkl']

manifest = {}
for filename in MODEL_FILES:
    filepath = os.path.join(MODEL_DIR, filename)
    if os.path.exists(filepath):
        with open(filepath, 'rb') as f:
            manifest[filename] = hashlib.sha256(f.read()).hexdigest()
        print(f"  {filename}: {manifest[filename][:16]}...")
    else:
        print(f"  {filename}: not found (skipping)")

with open(MANIFEST_PATH, 'w') as f:
    json.dump(manifest, f, indent=4)

print(f"Manifest written to {MANIFEST_PATH}")
