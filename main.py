import os
import time
import logging
import firebase_admin
from firebase_admin import credentials, firestore
from google.cloud.firestore_v1.base_query import FieldFilter

# Import your existing pipeline functions
from src.kaggle_client import download_and_extract_metadata, push_notebook_to_kaggle, check_kernel_status
from src.agent import generate_eda_code, fix_code_with_llm
from src.builder import assemble_notebook

# 1. Initialize Firebase
try:
    cred = credentials.Certificate("serviceAccountKey.json")
    firebase_admin.initialize_app(cred)
    db = firestore.client()
    print("✅ Successfully connected to Firebase Firestore.")
except Exception as e:
    print(f"❌ Firebase initialization failed: {e}")
    exit(1)

def run_pipeline_for_user(user_id: str, user_data: dict):
    # Dynamically set environment variables so the Kaggle SDK authenticates as THIS user
    os.environ["KAGGLE_USERNAME"] = user_data.get("kaggle_username", "").strip()
    os.environ["KAGGLE_KEY"] = user_data.get("kaggle_key", "").strip()
    gemini_key = user_data.get("gemini_key", "").strip()
    
    print(f"\n==================================================")
    print(f"🚀 Starting Pipeline for User: {os.environ['KAGGLE_USERNAME']} ({user_id})")
    print(f"==================================================")
    
    # Instantiate API inside the loop so it grabs the fresh os.environ keys for the current user
    from kaggle.api.kaggle_api_extended import KaggleApi
    try:
        api = KaggleApi()
        api.authenticate()
    except Exception as e:
        print(f"   ❌ Authentication failed for {user_id}. Skipping. Error: {e}")
        return

    print("   1. Searching for latest CSV datasets on Kaggle...")
    datasets = api.dataset_list(sort_by='updated', file_type='csv', max_size=30000000)
    dataset_ref, metadata = None, None

    # Resilient Dataset Hunting
    for ds in datasets:
        print(f"      Trying dataset: {ds.ref}")
        try:
            metadata = download_and_extract_metadata(ds.ref)
            dataset_ref = ds.ref
            print("      -> Success! Downloaded and extracted metadata.")
            break
        except Exception as e:
            print(f"      -> Skipping {ds.ref} due to Kaggle error: {e}")

    if not dataset_ref:
        print("   ❌ Could not find any working datasets. Skipping user.")
        return

    print("   2. Generating EDA code via Gemini...")
    code_content = generate_eda_code(metadata, dataset_ref, gemini_key)
    
    if "Failed to generate" in code_content:
        print("   ❌ Gemini API failed. Skipping user.")
        return

    print("   3. Assembling Jupyter Notebook...")
    notebook_path = assemble_notebook(code_content, dataset_ref, user_id)
    
    print("   4. Pushing public notebook to Kaggle...")
    try:
        kernel_slug = push_notebook_to_kaggle(notebook_path, dataset_ref, user_id)
        
        print(f"   5. Tracking execution status for {kernel_slug}...")
        status, error_log = check_kernel_status(kernel_slug)
        
        if status == 'complete':
            print(f"   🎉 SUCCESS! Notebook published at: https://www.kaggle.com/{kernel_slug}")
            
        elif 'error' in status:
            print(f"   ⚠️ Notebook failed with error. Attempting AI self-healing...")
            # Print the last 300 chars of the error to the terminal to see what the AI will read
            print(f"      Error snippet: {str(error_log)[-300:] if error_log else 'No error log retrieved.'}")
            
            # 6. TRIGGER THE SELF-HEALING LOOP
            print("   6. Prompting Gemini to fix the code...")
            fixed_code = fix_code_with_llm(code_content, error_log, gemini_key)
            
            print("   7. Re-assembling and pushing fixed notebook...")
            fixed_notebook_path = assemble_notebook(fixed_code, dataset_ref, user_id)
            fixed_kernel_slug = push_notebook_to_kaggle(fixed_notebook_path, dataset_ref, user_id)
            
            print(f"   8. Tracking execution status for fixed notebook ({fixed_kernel_slug})...")
            final_status, final_error = check_kernel_status(fixed_kernel_slug)
            
            if final_status == 'complete':
                print(f"   🎉 SELF-HEAL SUCCESS! Notebook published at: https://www.kaggle.com/{fixed_kernel_slug}")
            else:
                print(f"   ❌ Self-heal failed. Status: {final_status}. Giving up.")
                if final_error:
                    print(f"      Final Error snippet: {str(final_error)[-300:]}")
                
        else:
            print(f"   ⚠️ Notebook finished with status: {status}")
            
    except Exception as e:
        print(f"   ❌ Failed to push or track notebook: {e}")

def main():
    print("\nFetching active users from database...")
    
    # Using FieldFilter to prevent the UserWarning
    users_ref = db.collection('users').where(filter=FieldFilter('is_active', '==', True)).stream()
    
    active_users = []
    for doc in users_ref:
        active_users.append((doc.id, doc.to_dict()))
        
    print(f"Found {len(active_users)} active user(s). Beginning batch execution...\n")
    
    for user_id, user_data in active_users:
        try:
            run_pipeline_for_user(user_id, user_data)
        except Exception as e:
            # If one user's pipeline completely crashes, this try-except ensures 
            # the loop continues to the next user instead of killing the server.
            logging.error(f"Critical pipeline failure for user {user_id}: {e}")
            
    print("\n==================================================")
    print("🏁 ALL USER JOBS COMPLETED.")
    print("==================================================")

if __name__ == "__main__":
    main()