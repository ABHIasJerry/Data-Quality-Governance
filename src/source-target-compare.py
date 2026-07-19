import pandas as pd
import numpy as np

def generate_comparison_report(source_path, target_path, output_path, join_key):
    # Load the datasets
    source = pd.read_csv(source_path)
    target = pd.read_csv(target_path)

    # Perform an outer merge to handle row mismatches
    merged = pd.merge(source, target, on=join_key, how='outer', suffixes=('_SOURCE', '_TARGET'))

    report = pd.DataFrame()
    report['ID_KEY'] = merged[join_key]

    # Iterate through common columns to compare
    common_cols = [c for c in source.columns if c in target.columns and c != join_key]
    
    for col in common_cols:
        src_col = f"{col}_SOURCE"
        tgt_col = f"{col}_TARGET"
        
        # Fill missing values with "not found" for the report
        s_vals = merged[src_col].fillna("not found")
        t_vals = merged[tgt_col].fillna("not found")
        
        # Determine Match Status
        # If either side is "not found", it cannot be a match
        match_status = np.where(
            (s_vals == "not found") | (t_vals == "not found"), 
            "not found", 
            np.where(s_vals == t_vals, "matched", "not-matched")
        )
        
        # Create report columns with clear file indication
        report[f"{col}_MATCH_STATUS"] = match_status
        report[src_col] = s_vals
        report[tgt_col] = t_vals

    # Save to CSV
    report.to_csv(output_path, index=False)
    print(f"Report generated successfully at: {output_path}")

# Usage
generate_comparison_report('source.csv', 'target.csv', 'comparison_report.csv', join_key='ID')
