"""
Synthetic B2B Telemetry & ETL Pipeline Orchestrator

Executes the 5-stage data simulation pipeline that populates `capstone.db`:
  - `01_generate_crm.py`: Creates realistic target accounts, buying committees, and CRM opportunities.
  - `02_generate_baseline_traffic.py`: Simulates baseline multi-channel web, email, and social traffic.
  - `03_simulate_abm_journeys.py`: Injects intentional ABM anomalies (stalls, fatigue, cross-dept spikes).
  - `04_etl_load.py`: Transforms raw CSV/JSON event feeds into relational SQLite tables.
  - `05_create_indices.py`: Adds covering B-tree indexes for fast analytical query execution.
"""

import subprocess
import sys
import os
import time

def run_script(script_name):

    script_path = os.path.join(os.path.dirname(__file__), script_name)
    print(f"\n{'='*50}\nRunning {script_name}...\n{'='*50}")
    start_time = time.time()
    
    result = subprocess.run([sys.executable, script_path])
    
    if result.returncode != 0:
        print(f"\n[ERROR] {script_name} failed with exit code {result.returncode}")
        sys.exit(result.returncode)
        
    elapsed = time.time() - start_time
    print(f"\n[SUCCESS] {script_name} completed in {elapsed:.2f} seconds.")

def main():
    print("Starting Modular Data Generation Pipeline...\n")
    
    scripts = [
        "01_generate_crm.py",
        "02_generate_baseline_traffic.py",
        "03_simulate_abm_journeys.py",
        "04_etl_load.py",
        "05_create_indices.py"
    ]
    
    for script in scripts:
        run_script(script)
        
    print("\n" + "="*50)
    print("PIPELINE COMPLETE! Database is ready to use.")
    print("="*50)

if __name__ == "__main__":
    main()
