import os
import logging
from dotenv import load_dotenv
load_dotenv()

from src.kaggle_client import get_authenticated_api, download_and_extract_metadata, push_notebook_to_kaggle, check_kernel_status
from src.agent import generate_eda_code
from src.builder import assemble_notebook

# Put your personal Gemini key directly here just for this dry run
TEST_GEMINI_KEY = "AQ.Ab8RN6IbwRgQpM7MRssq5_gKgCl8peG0ij7ivHP1opS96LVDKQ"

print("1. Searching for latest CSV datasets on Kaggle...")
api = get_authenticated_api()
datasets = api.dataset_list(sort_by='updated', file_type='csv', max_size=30000000)

dataset_ref = None
metadata = None

# Loop through the newest datasets until we find one that actually works
for ds in datasets:
    print(f"   Trying dataset: {ds.ref}")
    try:
        metadata = download_and_extract_metadata(ds.ref)
        dataset_ref = ds.ref
        print("   -> Success! Downloaded and extracted.")
        break  # We found a working dataset, exit the loop!
    except Exception as e:
        print(f"   -> Skipping {ds.ref} due to Kaggle error: {e}")

if not dataset_ref:
    print("Could not find any working datasets right now. Try again later.")
    exit()

print("\n2. Metadata preview:\n", metadata[:300], "...\n")

print("3. Generating EDA code via Gemini...")
code = generate_eda_code(metadata, dataset_ref, TEST_GEMINI_KEY)
print("   Generated code length:", len(code), "characters")

print("4. Assembling Jupyter Notebook...")
notebook_path = assemble_notebook(code, dataset_ref, "local_test_user")
print(f"   Notebook saved at: {notebook_path}")

print("5. Pushing private kernel to Kaggle to test execution...")
kernel_slug = push_notebook_to_kaggle(notebook_path, dataset_ref, "local_test_user")
print(f"   Pushed: {kernel_slug}. Waiting for Kaggle runner to execute code...")

status, error_log = check_kernel_status(kernel_slug)
print(f"   Execution finished with status: {status}")
if status == "error":
    print("   Error log:\n", error_log)