import time
import logging
from google import genai

import time
import logging
from google import genai

import time
import logging
from google import genai

import time
import logging
from google import genai

def generate_eda_code(metadata: str, dataset_ref: str, api_key: str) -> str:
    client = genai.Client(api_key=api_key)
    
    # =========================================================================
    # 1. DYNAMIC MODEL DISCOVERY
    # =========================================================================
    try:
        candidate_models = []
        # Query Google's servers for every model currently active
        for model in client.models.list():
            name = getattr(model, 'name', '')
            
            # Isolate the cheapest tier ("flash") and exclude specialized vision/audio endpoints
            if "flash" in name and not any(x in name for x in ["image", "tts", "audio", "vision"]):
                clean_name = name.replace("models/", "")
                candidate_models.append(clean_name)
                
        # Sort descending so newer versions (3.8) are prioritized before older (3.5)
        candidate_models.sort(reverse=True)
        preferred_model = 'gemini-3.8-flash'
        if preferred_model in candidate_models:
            candidate_models.remove(preferred_model)
            candidate_models.insert(0, preferred_model)
        
    except Exception as e:
        logging.warning(f"Could not dynamically list models: {e}")
        candidate_models = []
        
    # Failsafe: If the listing API is down, use our known reliable defaults
    if not candidate_models:
        candidate_models = ['gemini-3.8-flash', 'gemini-3.5-flash']
        
    print(f"   -> Dynamic model queue mapped: {candidate_models}")

    # =========================================================================
    # 2. THE PROMPT
    # =========================================================================
    prompt = f"""
    You are an expert Data Scientist. Write an Exploratory Data Analysis (EDA) notebook.
    
    Here is the exact schema and sample data of the CSV files in this dataset:
    {metadata}
    
    CRITICAL FILE LOADING INSTRUCTIONS (EXACT MATCHING):
    Kaggle's directory structure varies, so you must dynamically find the paths. 
    Map the filenames provided in the metadata to their dynamic paths using a dictionary, then ONLY load files by explicitly checking their names.
    
    Example:
    ```python
    import os
    import pandas as pd
    import numpy as np
    
    file_paths = {{}}
    for dirname, _, filenames in os.walk('/kaggle/input'):
        for filename in filenames:
            if filename.endswith('.csv'):
                file_paths[filename] = os.path.join(dirname, filename)
                
    # Strictly load files by matching the metadata filenames
    if 'city_name.csv' in file_paths:
        df_city = pd.read_csv(file_paths['city_name.csv'])
    ```
    
    CRITICAL ALGORITHM RULES (PREVENT CRASHES):
    1. Isolation Forest, PCA, VIF, and Correlation Matrices CANNOT handle strings/object types. 
    2. Before using these algorithms, you MUST explicitly filter for numeric columns using `df.select_dtypes(include=[np.number])`.
    3. Machine learning models will also crash on missing values. You must handle NaNs (e.g., using `.dropna()` or `.fillna()`) on the numeric subset before fitting models like Isolation Forest.
    
    EDA REQUIREMENTS:
    Select the most relevant analyses from the following list based on the provided metadata context. You MUST include Multivariate Analysis, Outlier Analysis, and an Orthogonality Check.
    
    1. Dataset Structure & Metadata (Shape, types, uniques, duplicates)
    2. Missingness Analysis (Counts, heatmap, mechanism, imputation strategies)
    3. Univariate Analysis (Distributions, summary stats, outliers)
    4. Bivariate Analysis (Correlations, scatterplots, Chi-square/ANOVA)
    5. Multicollinearity & Orthogonality (VIF, collinear pairs, orthogonality check)
    6. Feature Engineering Possibilities (Interactions, binning, text/date features)
    7. Scaling & Normalization suggestions
    8. Outlier & Anomaly Detection (IQR, Z-score, Isolation Forest)
    9. Frequency & Cardinality Analysis
    10. Statistical Tests (Normality, Independence)
    11. Dimensionality Reduction (PCA, t-SNE potential)
    12. Target Variable Analysis (if a clear target exists)
    13. Data Quality Checks (Consistency, integrity, noise)
    14. Visualization Suite (Heatmaps, Boxplots, KDEs, Pairplots, Barplots)
    
    OUTPUT FORMATTING:
    Structure your response as a Jupyter Notebook. 
    - Write explanatory text in Markdown.
    - Write all executable Python code inside standard ```python code blocks.
    - Break the code up logically. Do not put all code in one giant block. Alternating markdown and code is required.
    - Use try-except blocks gracefully.
    """
    
    # =========================================================================
    # 3. THE TIERED FALLBACK ENGINE
    # =========================================================================
    max_retries = 3
    
    for model_name in candidate_models:
        print(f"   -> Knocking on {model_name}...")
        
        for attempt in range(max_retries):
            try:
                response = client.models.generate_content(
                    model=model_name,
                    contents=prompt
                )
                return response.text.strip()
                
            except Exception as e:
                err_str = str(e)
                
                # TRIGGER 1: Traffic Jam. Wait 15s and retry this exact same model.
                if "503" in err_str or "429" in err_str:
                    logging.warning(f"{model_name} is busy (503/429). Retrying in 15s... (Attempt {attempt+1}/{max_retries})")
                    time.sleep(15)
                    continue
                    
                # TRIGGER 2: Obsolete Model. Break retry loop instantly and jump to the next model in the queue.
                elif "404" in err_str or "NOT_FOUND" in err_str or "403" in err_str:
                    logging.warning(f"{model_name} is deprecated or unavailable. Falling back to next model.")
                    break
                    
                # TRIGGER 3: Unknown Crash. Break retry loop and jump to the next model.
                else:
                    logging.warning(f"Unexpected error with {model_name}: {err_str}. Trying next model.")
                    break
                    
    logging.error("Exhausted all available models in the queue.")
    return "Failed to generate code due to complete API failure."
def fix_code_with_llm(bad_code: str, error_log: str, api_key: str) -> str:
    """The self-correction loop trigger with retry logic."""
    client = genai.Client(api_key=api_key)
    
    prompt = f"""
    The following python code for a Kaggle notebook failed during execution.
    
    Code:
    {bad_code}
    
    Kaggle Error Log:
    {error_log}
    
    Fix the python code so it runs successfully. 
    Return ONLY the corrected python code. No explanations.
    """
    
    max_retries = 3
    for attempt in range(max_retries):
        try:
            response = client.models.generate_content(
                model='gemini-3.8-flash',
                contents=prompt
            )
            return response.text.replace("```python", "").replace("```", "").strip()
            
        except Exception as e:
            if "503" in str(e) or "429" in str(e):
                logging.warning(f"Gemini API busy. Retrying in 15 seconds... (Attempt {attempt+1}/{max_retries})")
                time.sleep(15)
            else:
                raise e
                
    return bad_code