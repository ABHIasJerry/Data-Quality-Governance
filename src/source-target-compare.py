import pandas as pd
from collections import Counter


def _normalize(v):
    """Convert a cell value to a comparable string.

    Returns None for blank/NaN values. Handles the common pandas gotcha
    where a whole-number column gets upcast to float (e.g. 1 -> 1.0)
    after NaNs are introduced, which would otherwise break string
    comparisons like "1" != "1.0".
    """
    if pd.isna(v) or v == "":
        return None
    if isinstance(v, float) and v.is_integer():
        return str(int(v))
    return str(v).strip()


def generate_full_comparison_report(source_path, target_path, output_path):
    # 1. Load the datasets
    df_src = pd.read_csv(source_path, encoding="utf-8", encoding_errors="ignore")
    df_tgt = pd.read_csv(target_path, encoding="utf-8", encoding_errors="ignore")

    # NOTE: we deliberately do NOT reindex/pad the source and target
    # dataframes to a common length before comparing. Doing that forces
    # pandas to introduce NaNs into short numeric columns, which upcasts
    # them from int to float (1 -> 1.0) and breaks string matching.
    # Matching is now done directly against each column's own values.

    report_columns = {}
    max_len = max(len(df_src), len(df_tgt))

    all_source_cols = df_src.columns
    all_target_cols = df_tgt.columns
    all_cols = set(all_source_cols) | set(all_target_cols)

    for col in all_cols:
        if col in all_source_cols and col in all_target_cols:
            s_vals = df_src[col]
            t_vals = df_tgt[col]

            # Lookup of every normalized value present anywhere in the
            # target column / source column, so row order doesn't matter.
            target_norm_counts = Counter(
                n for n in (_normalize(v) for v in t_vals) if n is not None
            )

            match_status = []
            for s in s_vals:
                s_norm = _normalize(s)
                if s_norm is None:
                    match_status.append("FALSE")
                elif s_norm in target_norm_counts:
                    match_status.append("TRUE")
                else:
                    match_status.append("FALSE")

            # Pad the shorter side with blanks for display, WITHOUT
            # letting pandas upcast dtypes (convert to plain lists first).
            s_list = [("" if pd.isna(v) else v) for v in s_vals.tolist()]
            t_list = [("" if pd.isna(v) else v) for v in t_vals.tolist()]
            s_list += [""] * (max_len - len(s_list))
            t_list += [""] * (max_len - len(t_list))
            match_status += ["FALSE"] * (max_len - len(match_status))

            report_columns[f"SOURCE_{col}"] = s_list
            report_columns[f"TARGET_{col}"] = t_list
            report_columns[f"MATCH_{col}"] = match_status

        elif col in all_source_cols:
            s_list = [("" if pd.isna(v) else v) for v in df_src[col].tolist()]
            s_list += [""] * (max_len - len(s_list))
            report_columns[f"SOURCE_{col}"] = s_list

        elif col in all_target_cols:
            t_list = [("" if pd.isna(v) else v) for v in df_tgt[col].tolist()]
            t_list += [""] * (max_len - len(t_list))
            report_columns[f"TARGET_{col}"] = t_list

    report = pd.DataFrame(report_columns)
    report.to_csv(output_path, index=False)
    print(f"Report successfully generated at: {output_path}")


# Usage
generate_full_comparison_report('source.csv', 'target.csv', 'report.csv')
