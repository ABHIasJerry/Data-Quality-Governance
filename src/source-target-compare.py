import pandas as pd
import numpy as np

def compare_csvs_positional(source_path, target_path, output_path):
    # Load the datasets
    df_src = pd.read_csv(source_path)
    df_tgt = pd.read_csv(target_path)

    # Ensure files have the same number of rows for positional comparison
    # If they differ, we pad the shorter one with empty rows
    max_rows = max(len(df_src), len(df_tgt))
    
    # Reindex to match the max length to avoid errors during alignment
    df_src = df_src.reindex(range(max_rows))
    df_tgt = df_tgt.reindex(range(max_rows))

    # Initialize the report DataFrame
    report = pd.DataFrame()

    # Identify common columns
    common_cols = [c for c in df_src.columns if c in df_tgt.columns]

    for col in common_cols:
        # Get data and fill missing values with a placeholder
        s_vals = df_src[col].fillna("not found")
        t_vals = df_tgt[col].fillna("not found")

        # Determine Match Status
        # We define a match only if both values exist and are equal
        match_status = np.where(
            (s_vals == "not found") | (t_vals == "not found"), 
            "not found", 
            np.where(s_vals == t_vals, "matched", "not-matched")
        )

        # Add columns to report in the specific order requested
        report[f"{col}_SOURCE"] = s_vals
        report[f"{col}_TARGET"] = t_vals
        report[f"{col}_MATCH"] = match_status

    # Save to CSV
    report.to_csv(output_path, index=False)
    print(f"Report successfully generated: {output_path}")

# Usage
compare_csvs_positional('source.csv', 'target.csv', 'final_report.csv')
