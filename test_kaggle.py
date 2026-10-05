import os
import sys
import json
from dotenv import load_dotenv

# 1. FORCE LOAD .ENV FIRST (override=True ensures it overwrites any existing system variables)
load_dotenv(override=True)

username = os.environ.get("KAGGLE_USERNAME")
key = os.environ.get("KAGGLE_KEY")

print("--- DIAGNOSTIC TEST START ---")
print(f"Python Version: {sys.version.split()[0]}")

if not username or not key:
    print("❌ ERROR: KAGGLE_USERNAME or KAGGLE_KEY not found in .env!")
    sys.exit(1)

print(f"Credentials loaded from .env -> User: {username}, Key: {key[:3]}...{key[-3:]}")

# 2. IMPORT KAGGLE ONLY AFTER ENV VARS ARE SET
import kaggle
from kaggle.api.kaggle_api_extended import KaggleApi

print(f"Kaggle SDK Version: {kaggle.__version__}")

api = KaggleApi()
api.authenticate()

# --- TEST 1: GET REQUEST (Authentication Check) ---
print("\n--- TEST 1: GET REQUEST (Token Validity Check) ---")
try:
    # Attempting to fetch your own profile/kernels
    api.kernels_list(user=username, page_size=1)
    print("✅ GET Request Successful! Your API token is 100% valid and active.")
except Exception as e:
    print(f"❌ GET Request Failed: {e}")
    print("\nCONCLUSION FOR TEST 1: Your API token is invalid, expired, or has a typo.")
    print("ACTION: Generate a brand new token on Kaggle and update your .env file.")
    sys.exit(1)

# --- TEST 2: POST REQUEST (Account Permission Check) ---
print("\n--- TEST 2: POST REQUEST (Push Permission Check) ---")
folder = "dummy_workspace"
os.makedirs(folder, exist_ok=True)
with open(os.path.join(folder, "test.ipynb"), "w") as f:
    f.write('{"cells": [], "metadata": {}, "nbformat": 4, "nbformat_minor": 5}')

slug = "diagnostic-test-123"
metadata = {
    "id": f"{username}/{slug}",
    "title": slug,
    "code_file": "test.ipynb",
    "language": "python",
    "kernel_type": "notebook",
    "is_private": "true"
}
with open(os.path.join(folder, "kernel-metadata.json"), "w") as f:
    json.dump(metadata, f)

try:
    api.kernels_push(folder)
    print("✅ POST Request Successful! The block is cleared.")
except Exception as e:
    print(f"❌ POST Request Failed: {e}")
    print("\nCONCLUSION FOR TEST 2: The API token is perfect, but Kaggle is actively blocking your account from creating kernels.")
    print("POSSIBLE CAUSES:")
    print("1. Phone verification is glitched on Kaggle's end (try re-verifying).")
    print("2. The account is too new and is on a silent cooldown.")
    print("3. The account has been flagged by Kaggle's automated anti-spam system.")