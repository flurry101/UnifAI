import subprocess
import time
import sys

def run_step(cmd, desc):
    print(f"\n{'='*50}\nStarting: {desc}\n{'='*50}")
    start = time.time()
    result = subprocess.run(cmd, shell=True)
    duration = time.time() - start
    if result.returncode != 0:
        print(f"\n[ERROR] {desc} failed with return code {result.returncode}")
        sys.exit(1)
    print(f"\n[SUCCESS] {desc} completed in {duration:.2f} seconds.")

if __name__ == "__main__":
    print("Starting Full Lane 5 Validation")
    
    # Run the 21K corpus indexing
    run_step(".venv\\Scripts\\python scripts/dataset/lane5_index.py", "Lane 5 21K Corpus Indexing")
    
    # Run the Synthetic V2 Evaluation
    run_step(".venv\\Scripts\\python scripts/dataset/lane5_retrieval_evaluation.py", "Lane 5 Synthetic V2 Retrieval Evaluation")
    
    print("\nALL VALIDATION STEPS COMPLETED SUCCESSFULLY.")
