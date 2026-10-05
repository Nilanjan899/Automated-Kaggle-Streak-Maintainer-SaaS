import os
from dotenv import load_dotenv
from src.kaggle_client import get_authenticated_api, download_and_extract_metadata
from src.agent import generate_eda_code
from src.builder import assemble_notebook

# Load your local environment variables
load_dotenv()

# We'll use your personal Gemini key for this local run
TEST_GEMINI_KEY = os.environ.get("TEST_GEMINI_KEY")

def main():
    print("1. Searching Kaggle for the latest CSV dataset...")
    api = get_authenticated_api()
    datasets = api.dataset_list(sort_by='updated', file_type='csv', max_size=30000000)

    dataset_ref = None
    metadata = None

    # Resilient loop to find a working dataset
    for ds in datasets:
        print(f"   Trying dataset: {ds.ref}")
        try:
            metadata = download_and_extract_metadata(ds.ref)
            dataset_ref = ds.ref
            print("   -> Success! Downloaded and extracted metadata.")
            break
        except Exception as e:
            print(f"   -> Skipping {ds.ref} due to Kaggle error: {e}")

    if not dataset_ref:
        print("\nCould not find any working datasets right now. Try again later.")
        return

    print("\n2. Generating Python EDA Code via Gemini (gemini-2.5-flash)...")
    code = generate_eda_code(metadata, dataset_ref, TEST_GEMINI_KEY)
    print(f"   Generated {len(code)} characters of Python code.")

    print("\n3. Assembling Jupyter Notebook...")
    
    # We will save it in a neat "output_notebooks" folder
    output_folder = "output_notebooks"
    os.makedirs(output_folder, exist_ok=True)
    
    # Re-using your builder module to stitch the notebook together
    # It will save as output_notebooks/workspace_local_test_user/automated_eda.ipynb
    notebook_path = assemble_notebook(code, dataset_ref, "local_test_user")
    
    # Move it cleanly to our output folder for easy access
    final_path = os.path.join(output_folder, f"EDA_{dataset_ref.split('/')[-1]}.ipynb")
    os.rename(notebook_path, final_path)
    
    print("\n==================================================")
    print(f"🎉 SUCCESS! Notebook saved at: {final_path}")
    print("==================================================")
    print("You can now open this file directly in VS Code or Jupyter Lab!")

if __name__ == "__main__":
    main()