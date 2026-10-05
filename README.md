# Automated Kaggle Streak Maintainer (AI SaaS)

An autonomous, multi-tenant Serverless SaaS that fetches daily datasets, performs professional-grade Exploratory Data Analysis (EDA) using Google's Gemini models, and publishes the resulting Jupyter notebooks directly to Kaggle.

Built to maintain Kaggle activity streaks and generate high-quality open-source data science content autonomously.

## Key Features

* **Multi-Tenant Architecture:** Powered by Firebase Firestore, allowing multiple users to run independent daily pipelines from a single cloud execution.
* **AI-Powered Code Generation:** Leverages Google's `gemini-3.8-flash` (with a dynamic fallback queue) to write comprehensive, multi-cell Python EDA code.
* **Autonomous Self-Healing:** If Kaggle's execution engine (Papermill) throws a Python error, the agent reads the stack trace, rewrites the code to fix the bug, and redeploys the notebook automatically.
* **Resilient Dataset Hunting:** Dynamically scans the Kaggle API for fresh CSV datasets, gracefully skipping broken or inaccessible data.
* **Advanced EDA Enforcement:** Prompt engineering forces the LLM to separate numeric/categorical data to prevent crashes on advanced algorithms like Isolation Forests, PCA, and VIF.
* **100% Serverless:** Orchestrated via GitHub Actions cron jobs, costing $0 to host and run.

## How It Works (Under the Hood)

This system operates on a scheduled daily heartbeat without any human intervention.

1. **The Brain (main.py):** GitHub Actions triggers the workflow. The script securely injects Firebase credentials from GitHub Secrets and connects to Firestore.
2. **User Loop:** It queries the database for all active users and loops through them, dynamically swapping Kaggle and Gemini API keys into the environment variables for each iteration.
3. **Dataset Acquisition:** The Kaggle API is polled for recently updated CSV datasets (under 30MB). The metadata and schema are extracted.
4. **Code Generation:** The dataset schema is fed into a sophisticated Gemini prompt. The AI acts as an Expert Data Scientist, writing alternating Markdown explanations and Python code blocks.
5. **Assembly (builder.py):** The raw LLM output is parsed and assembled into a valid `.ipynb` JSON structure, injecting Kaggle's required `python3` kernel metadata.
6. **Deployment:** The notebook is pushed to Kaggle publicly.
7. **Execution Tracking:** The script polls Kaggle's backend. If successful, the loop moves to the next user. If an error occurs, the AI Self-Healing sequence is initiated.

## Tech Stack

* **Language:** Python 3.12
* **Cloud Database:** Firebase Firestore (NoSQL)
* **LLM Engine:** Google GenAI SDK (Gemini 3.8 Flash)
* **Integration:** Kaggle API, nbformat
* **Automation:** GitHub Actions

## Setup & Installation (For Admins)

If you want to host your own instance of this SaaS:

1. **Clone the repository:**
   ```bash
   git clone [https://github.com/YOUR_GITHUB_USERNAME/kaggle-streak-maintainer-saas.git](https://github.com/YOUR_GITHUB_USERNAME/kaggle-streak-maintainer-saas.git)
   cd kaggle-streak-maintainer-saas
   ```

2. **Install Dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

3. **Firebase Setup:**
   * Create a Firestore database.
   * Create a `users` collection.
   * Add documents with fields: `is_active` (boolean), `kaggle_username`, `kaggle_key`, and `gemini_key`.
   * Generate a Service Account Key JSON file. 

4. **GitHub Actions Configuration:**
   * Add your Firebase Service Account JSON contents as a GitHub Secret named `FIREBASE_SERVICE_ACCOUNT`.
   * The workflow will now automatically run daily at midnight UTC via `.github/workflows/eda_worker.yml`.

## How to Use (For Users)

If you are a user looking to be added to the platform:
1. Generate a **Kaggle API Token** (`kaggle.json` from your Kaggle Account Settings).
2. Generate a **Gemini API Key** from Google AI Studio.
3. Provide these keys to the platform admin to be added to the database. The bot will automatically publish an EDA notebook to your account every 24 hours.

---
*Disclaimer: This tool is intended for educational purposes, open-source data science contributions, and workflow automation.*
