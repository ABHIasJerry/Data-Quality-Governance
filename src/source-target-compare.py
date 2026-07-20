import pandas as pd


def _normalize(v):
    """Convert a cell value to a comparable string, or None if blank/NaN.

    Handles the pandas gotcha where a whole-number column can get
    upcast to float (1 -> 1.0), which would otherwise break matching.
    """
    if pd.isna(v) or v == "":
        return None
    if isinstance(v, float) and v.is_integer():
        return str(int(v))
    return str(v).strip()


def _match_column(s_vals, t_vals):
    """Pair up equal values between a source column and a target column.

    - Every value in source is matched against the first not-yet-used
      equal value anywhere in target (order-independent).
    - Matched pairs are written side by side with status TRUE.
    - A source value with no match in target is written with a blank
      target cell and status FALSE.
    - A target value with no match in source is written with a blank
      source cell and status FALSE.
    - Blank/NaN cells in source are written as their own row (blank
      side by side) with status FALSE, since a blank can't "match".

    Returns a list of (source_display, target_display, status) rows.
    """
    s_norm = [_normalize(v) for v in s_vals]
    t_norm = [_normalize(v) for v in t_vals]
    t_used = [False] * len(t_norm)

    rows = []

    # 1. Walk source values, find a matching target value anywhere.
    for sv, sn in zip(s_vals, s_norm):
        if sn is None:
            rows.append(("", "", "FALSE"))
            continue

        match_idx = None
        for j, tn in enumerate(t_norm):
            if not t_used[j] and tn == sn:
                match_idx = j
                break

        if match_idx is not None:
            t_used[match_idx] = True
            rows.append((sv, t_vals[match_idx], "TRUE"))
        else:
            rows.append((sv, "", "FALSE"))

    # 2. Any target values never matched -> their own row, blank source side.
    for tv, tn, used in zip(t_vals, t_norm, t_used):
        if not used:
            if tn is None:
                rows.append(("", "", "FALSE"))
            else:
                rows.append(("", tv, "FALSE"))

    return rows


def generate_full_comparison_report(source_path, target_path, output_path):
    # 1. Load the datasets
    df_src = pd.read_csv(source_path, encoding="utf-8", encoding_errors="ignore")
    df_tgt = pd.read_csv(target_path, encoding="utf-8", encoding_errors="ignore")

    all_source_cols = df_src.columns
    all_target_cols = df_tgt.columns
    all_cols = set(all_source_cols) | set(all_target_cols)

    # 2. Build each column's report data independently (matched pairs
    #    aligned side by side), then pad every column to the same
    #    overall row count so they can sit in one wide table.
    report_columns = {}
    col_lengths = {}

    for col in all_cols:
        if col in all_source_cols and col in all_target_cols:
            rows = _match_column(df_src[col].tolist(), df_tgt[col].tolist())
            report_columns[col] = ("both", rows)
            col_lengths[col] = len(rows)

        elif col in all_source_cols:
            vals = [("" if pd.isna(v) else v) for v in df_src[col].tolist()]
            report_columns[col] = ("source_only", vals)
            col_lengths[col] = len(vals)

        elif col in all_target_cols:
            vals = [("" if pd.isna(v) else v) for v in df_tgt[col].tolist()]
            report_columns[col] = ("target_only", vals)
            col_lengths[col] = len(vals)

    max_len = max(col_lengths.values()) if col_lengths else 0

    final_columns = {}
    for col, (kind, data) in report_columns.items():
        if kind == "both":
            s_col = [r[0] for r in data] + [""] * (max_len - len(data))
            t_col = [r[1] for r in data] + [""] * (max_len - len(data))
            # Pad rows beyond this column's real data with a blank status
            # (not TRUE/FALSE) since there's no real comparison there.
            m_col = [r[2] for r in data] + [""] * (max_len - len(data))
            final_columns[f"SOURCE_{col}"] = s_col
            final_columns[f"TARGET_{col}"] = t_col
            final_columns[f"MATCH_{col}"] = m_col
        elif kind == "source_only":
            final_columns[f"SOURCE_{col}"] = data + [""] * (max_len - len(data))
        else:
            final_columns[f"TARGET_{col}"] = data + [""] * (max_len - len(data))

    report = pd.DataFrame(final_columns)
    report.to_csv(output_path, index=False)
    print(f"Report successfully generated at: {output_path}")


# Usage
generate_full_comparison_report('source.csv', 'target.csv', 'report.csv')
