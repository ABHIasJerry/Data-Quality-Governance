import pandas as pd
import numpy as np

def compare_csvs_strict(source_path, target_path, output_path):
    # 1. Load the datasets
    df_src = pd.read_csv(source_path)
    df_tgt = pd.read_csv(target_path)

    # 2. Identify common columns
    common_cols = [c for c in df_src.columns if c in df_tgt.columns]
    
    # 3. Sort to align rows
    df_src_sorted = df_src.sort_values(by=common_cols).reset_index(drop=True)
    df_tgt_sorted = df_tgt.sort_values(by=common_cols).reset_index(drop=True)

    # Pad shorter file
    max_len = max(len(df_src_sorted), len(df_tgt_sorted))
    df_src_sorted = df_src_sorted.reindex(range(max_len))
    df_tgt_sorted = df_tgt_sorted.reindex(range(max_len))

    # 4. Initialize Report
    report = pd.DataFrame()
    row_status = np.array(["matched"] * max_len)

    for col in common_cols:
        # Get data keeping NaNs as is
        s_vals = df_src_sorted[col]
        t_vals = df_tgt_sorted[col]

        # Determine Match Status
        # If either is null, status is "not found"
        # If both are null, status is "matched" (or "not found" based on your preference)
        # Using pd.isna() to detect nulls/blanks accurately
        is_s_null = s_vals.isna()
        is_t_null = t_vals.isna()
        
        match_status = np.where(
            is_s_null | is_t_null, 
            "not found", 
            np.where(s_vals == t_vals, "matched", "not-matched")
        )

        # Build columns: Ensure nulls stay empty in the output
        report[f"{col}_SOURCE"] = s_vals.where(s_vals.notna(), "")
        report[f"{col}_TARGET"] = t_vals.where(t_vals.notna(), "")
        report[f"{col}_MATCH"] = match_status

        # Update global row status
        row_status = np.where(match_status == "not-matched", "not-matched", row_status)
        row_status = np.where((match_status == "not found") & (row_status != "not-matched"), "not found", row_status)

    # 5. Add the summary column
    report["OVERALL_ROW_STATUS"] = row_status

    # Save to CSV
    # na_rep='' ensures that any remaining internal NaNs are written as empty strings
    report.to_csv(output_path, index=False, na_rep='')
    print(f"Report generated successfully: {output_path}")

# Usage
compare_csvs_strict('source.csv', 'target.csv', 'final_report.csv')
