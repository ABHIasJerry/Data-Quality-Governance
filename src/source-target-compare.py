import pandas as pd
import numpy as np

def compare_csvs_with_summary(source_path, target_path, output_path):
    # 1. Load the datasets
    df_src = pd.read_csv(source_path)
    df_tgt = pd.read_csv(target_path)

    # 2. Identify common columns
    common_cols = [c for c in df_src.columns if c in df_tgt.columns]
    
    # 3. Sort to align rows (handling row mismatches)
    df_src_sorted = df_src.sort_values(by=common_cols).reset_index(drop=True)
    df_tgt_sorted = df_tgt.sort_values(by=common_cols).reset_index(drop=True)

    # Pad shorter file
    max_len = max(len(df_src_sorted), len(df_tgt_sorted))
    df_src_sorted = df_src_sorted.reindex(range(max_len))
    df_tgt_sorted = df_tgt_sorted.reindex(range(max_len))

    # 4. Initialize Report and status tracking
    report = pd.DataFrame()
    row_status = np.array(["matched"] * max_len)

    for col in common_cols:
        s_vals = df_src_sorted[col].fillna("not found")
        t_vals = df_tgt_sorted[col].fillna("not found")

        # Determine individual match status
        match_status = np.where(
            (s_vals == "not found") | (t_vals == "not found"), 
            "not found", 
            np.where(s_vals == t_vals, "matched", "not-matched")
        )

        # Build report columns
        report[f"{col}_SOURCE"] = s_vals
        report[f"{col}_TARGET"] = t_vals
        report[f"{col}_MATCH"] = match_status

        # Update global row status
        # If any column is "not-matched", row is "not-matched"
        row_status = np.where(match_status == "not-matched", "not-matched", row_status)
        # If row isn't "not-matched" but has a "not found", make it "not found"
        row_status = np.where((match_status == "not found") & (row_status != "not-matched"), "not found", row_status)

    # 5. Add the summary column
    report["OVERALL_ROW_STATUS"] = row_status

    # Save to CSV
    report.to_csv(output_path, index=False)
    print(f"Report generated successfully: {output_path}")

# Usage
compare_csvs_with_summary('source.csv', 'target.csv', 'final_report.csv')
