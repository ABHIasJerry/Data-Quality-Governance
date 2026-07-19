import pandas as pd

def generate_full_comparison_report(source_path, target_path, output_path):
    # 1. Load the datasets
    df_src = pd.read_csv(source_path, encoding="utf-8", encoding_errors="ignore")
    df_tgt = pd.read_csv(target_path, encoding="utf-8", encoding_errors="ignore")

    # 2. Align rows by index (handles row mismatches)
    max_len = max(len(df_src), len(df_tgt))
    df_src = df_src.reindex(range(max_len))
    df_tgt = df_tgt.reindex(range(max_len))

    # 3. Initialize the report
    report = pd.DataFrame()
    
    # 4. Process Columns
    all_source_cols = df_src.columns
    all_target_cols = df_tgt.columns
    
    # Get the union of all column names to ensure we include everything
    all_cols = set(all_source_cols) | set(all_target_cols)

    for col in all_cols:
        # If the column exists in both, we perform the match comparison
        if col in all_source_cols and col in all_target_cols:
            s_vals = df_src[col]
            t_vals = df_tgt[col]
            
            # Add Source and Target columns
            report[f"SOURCE_{col}"] = s_vals.fillna("")
            report[f"TARGET_{col}"] = t_vals.fillna("")
            
            # Apply your specific logic:
            match_status = []
            for s, t in zip(s_vals, t_vals):
                # Check if either value is blank or NaN
                if pd.isna(s) or s == "" or pd.isna(t) or t == "":
                    match_status.append("NOT FOUND")
                elif str(s) == str(t):
                    match_status.append("TRUE")
                else:
                    match_status.append("FALSE")
            
            report[f"MATCH_{col}"] = match_status
            
        # If column exists only in Source
        elif col in all_source_cols:
            report[f"SOURCE_{col}"] = df_src[col].fillna("")
            
        # If column exists only in Target
        elif col in all_target_cols:
            report[f"TARGET_{col}"] = df_tgt[col].fillna("")

    # 5. Save to CSV
    report.to_csv(output_path, index=False)
    print(f"Report successfully generated at: {output_path}")

# Usage
generate_full_comparison_report('source.csv', 'target.csv', 'report.csv')
