import pandas as pd


def _normalize(v):
    """Convert a cell value to a comparable string, or None if blank/NaN."""
    if pd.isna(v) or v == "":
        return None

    s = str(v).strip()
    if s == "":
        return None

    try:
        f = float(s.replace(",", ""))
        if f.is_integer():
            return str(int(f))
        return ("%f" % f).rstrip("0").rstrip(".")
    except ValueError:
        pass

    return s.lower()


def generate_row_comparison_report(source_path, target_path, output_path, key_cols):
    # 1. Load datasets and fill NAs with empty strings for clean processing
    df_src = pd.read_csv(source_path, encoding="utf-8", encoding_errors="ignore").fillna("")
    df_tgt = pd.read_csv(target_path, encoding="utf-8", encoding_errors="ignore").fillna("")

    all_source_cols = df_src.columns
    all_target_cols = df_tgt.columns
    
    # Validate keys exist in both files
    for k in key_cols:
        if k not in all_source_cols or k not in all_target_cols:
            raise ValueError(f"Key column '{k}' must exist in both Source and Target files.")

    # Preserve original column order without duplicates
    all_cols = list(dict.fromkeys(list(all_source_cols) + list(all_target_cols)))

    # 2. Map Target rows by their composite key to handle matching (and duplicates natively)
    target_unmatched_indices = {}
    for idx, row in df_tgt.iterrows():
        # Create a normalized tuple of the key columns to serve as a reliable matching ID
        key = tuple(_normalize(row.get(k, "")) for k in key_cols)
        if key not in target_unmatched_indices:
            target_unmatched_indices[key] = []
        target_unmatched_indices[key].append(idx)

    aligned_pairs = []  # Will store tuples of (source_index, target_index)

    # 3. Match Source rows to Target rows using the composite key
    for idx, row in df_src.iterrows():
        key = tuple(_normalize(row.get(k, "")) for k in key_cols)
        
        # If the key exists in target and hasn't been fully used up by duplicates
        if key in target_unmatched_indices and len(target_unmatched_indices[key]) > 0:
            tgt_idx = target_unmatched_indices[key].pop(0)
            aligned_pairs.append((idx, tgt_idx))
        else:
            # Source row has no match in target
            aligned_pairs.append((idx, None))

    # 4. Collect leftover Target rows that had no match in Source
    for key, indices in target_unmatched_indices.items():
        for tgt_idx in indices:
            aligned_pairs.append((None, tgt_idx))

    # 5. Initialize the output dictionary
    final_columns = {}
    for col in all_cols:
        if col in all_source_cols and col in all_target_cols:
            final_columns[f"SOURCE_{col}"] = []
            final_columns[f"TARGET_{col}"] = []
            final_columns[f"MATCH_{col}"] = []
        elif col in all_source_cols:
            final_columns[f"SOURCE_{col}"] = []
        else:
            final_columns[f"TARGET_{col}"] = []

    # 6. Populate the final dataset row-by-row
    for src_idx, tgt_idx in aligned_pairs:
        # Extract the actual series data if the index exists, else None
        src_row = df_src.iloc[src_idx] if src_idx is not None else None
        tgt_row = df_tgt.iloc[tgt_idx] if tgt_idx is not None else None

        for col in all_cols:
            in_src = col in all_source_cols
            in_tgt = col in all_target_cols

            sv = src_row[col] if (in_src and src_row is not None) else ""
            tv = tgt_row[col] if (in_tgt and tgt_row is not None) else ""

            if in_src and in_tgt:
                # If one side is missing entirely (unmatched row), MATCH is FALSE.
                if src_idx is None or tgt_idx is None:
                    match_status = "FALSE"
                else:
                    # Both rows exist, compare the specific column values
                    match_status = "TRUE" if _normalize(sv) == _normalize(tv) else "FALSE"

                final_columns[f"SOURCE_{col}"].append(sv)
                final_columns[f"TARGET_{col}"].append(tv)
                final_columns[f"MATCH_{col}"].append(match_status)
                
            elif in_src:
                final_columns[f"SOURCE_{col}"].append(sv)
            else:
                final_columns[f"TARGET_{col}"].append(tv)

    # 7. Export the structurally perfect table
    report = pd.DataFrame(final_columns)
    report.to_csv(output_path, index=False)
    print(f"Report successfully generated at: {output_path}")


# Usage - Define your two unique identifier columns here!
if __name__ == "__main__":
    # Example: Using "ID" and "Date" as the composite key to link rows together.
    my_key_columns = ["Column_1_Name", "Column_2_Name"] 
    
    generate_row_comparison_report(
        source_path="source.csv", 
        target_path="target.csv", 
        output_path="report.csv", 
        key_cols=my_key_columns
    )
