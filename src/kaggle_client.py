import os
import glob
import json
import time
import shutil
import logging
import re
import pandas as pd
from kaggle.api.kaggle_api_extended import KaggleApi

def get_authenticated_api():
    """Ensures the API is authenticated using the latest env variables."""
    api = KaggleApi()
    api.authenticate()
    return api

def fetch_latest_csv_dataset():
    api = get_authenticated_api()
    datasets = api.dataset_list(sort_by='updated', file_type='csv', max_size=30000000)
    for ds in datasets:
        return ds.ref
    return None

def download_and_extract_metadata(dataset_ref: str) -> str:
    api = get_authenticated_api()
    download_dir = f"./temp_{dataset_ref.split('/')[-1]}"
    os.makedirs(download_dir, exist_ok=True)
    
    api.dataset_download_files(dataset_ref, path=download_dir, unzip=True)
    metadata = f"Dataset Ref: {dataset_ref}\n"
    
    for file_path in glob.glob(f"{download_dir}/**/*.csv", recursive=True):
        try:
            # FIX: Added on_bad_lines='skip' to prevent crashing on messy datasets
            df = pd.read_csv(file_path, nrows=5, on_bad_lines='skip')
            file_name = os.path.basename(file_path)
            metadata += f"\n--- File: {file_name} ---\n"
            metadata += f"Columns and Dtypes:\n{df.dtypes.to_string()}\n"
            # FIX: Changed to_markdown() to to_string() to remove tabulate dependency
            metadata += f"\nSample Data:\n{df.head(3).to_string()}\n"
        except Exception as e:
            logging.warning(f"Failed to read {file_path}: {e}")
            
    shutil.rmtree(download_dir, ignore_errors=True)
    return metadata

import re
import os

import os
import json
import re

def push_notebook_to_kaggle(notebook_path: str, dataset_ref: str, user_id: str) -> str:
    """Pushes the generated notebook to Kaggle and makes it public."""
    api = get_authenticated_api()
    username = api.get_config_value(api.CONFIG_NAME_USER)
    
    # 1. Create a beautiful, human-readable title (max 50 chars)
    # Extracts "us-down-payment-assistance" -> "Us Down Payment Assistance"
    dataset_name = dataset_ref.split('/')[-1].replace('-', ' ').title()
    safe_title = f"EDA: {dataset_name}"[:50].strip()
    
    # 2. Mimic Kaggle's exact backend URL generator to prevent 403 errors
    # Lowercase, replace any non-alphanumeric character with a hyphen, and strip edges
    slug = re.sub(r'[^a-zA-Z0-9]', '-', safe_title).lower()
    slug = re.sub(r'-+', '-', slug).strip('-') # Remove double hyphens

    # 3. Create the metadata dictionary
    metadata = {
        "id": f"{username}/{slug}",
        "title": safe_title, 
        "code_file": os.path.basename(notebook_path),
        "language": "python",
        "kernel_type": "notebook",
        "is_private": "false",  # Forces the notebook to be completely public immediately
        "enable_gpu": "false",
        "enable_internet": "true",
        "dataset_sources": [dataset_ref],
        "competition_sources": [],
        "kernel_sources": []
    }
    
    # 4. Save metadata to the same folder as the notebook
    folder = os.path.dirname(notebook_path)
    metadata_path = os.path.join(folder, "kernel-metadata.json")
    with open(metadata_path, "w") as f:
        json.dump(metadata, f, indent=4)
        
    # 5. Push to Kaggle
    print(f"   Pushed: {username}/{slug}. Waiting for Kaggle runner to execute code...")
    api.kernels_push(folder)
    
    # Return the exact identifier Kaggle uses so the polling loop can track it
    return f"{username}/{slug}"

def check_kernel_status(kernel_slug: str):
    api = get_authenticated_api()
    while True:
        status_res = api.kernels_status(kernel_slug)
        
        # Cast the Enum to a lowercase string (e.g., 'kernelworkerstatus.complete' -> 'complete')
        status_str = str(getattr(status_res, 'status', 'unknown')).lower()
        
        if 'complete' in status_str or 'error' in status_str or 'cancel' in status_str:
            error_log = ""
            if "error" in status_str:
                try:
                    output = api.kernels_output(kernel_slug)
                    error_log = getattr(output, 'log', 'Unknown execution error.')
                except Exception:
                    error_log = "Could not fetch error logs."
            return status_str, error_log
            
        print(f"   Kernel {kernel_slug} is {status_str}. Waiting 30s...")
        time.sleep(30)