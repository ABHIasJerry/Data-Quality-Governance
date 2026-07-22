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

###########################################################################################

import pandas as pd
from itertools import zip_longest


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
    unmatched_s = []  # leftover source values with no match, to pair up later

    # 1. Walk source values, find a matching target value anywhere.
    for sv, sn in zip(s_vals, s_norm):
        if sn is None:
            # A blank source cell can't match anything - its own blank/blank row.
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
            # Don't write this yet - queue it so it can be paired side by
            # side with a leftover target value instead of getting its own
            # row now and the target leftover getting a separate row later
            # (which is what caused unmatched rows to land far below the
            # real data, out of alignment with the other columns).
            unmatched_s.append(sv)

    # 2. Collect any target values that were never matched to a source value.
    unmatched_t = [
        ("" if tn is None else tv)
        for tv, tn, used in zip(t_vals, t_norm, t_used)
        if not used
    ]

    # 3. Pair leftover source and target values side by side, row for row,
    #    instead of stacking them as separate trailing rows.
    for su, tu in zip_longest(unmatched_s, unmatched_t, fillvalue=""):
        rows.append((su, tu, "FALSE"))

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

########################################################################################

import pandas as pd
from itertools import zip_longest


def _normalize(v):
    """Convert a cell value to a comparable string, or None if blank/NaN.

    Handles a few common cross-file formatting mismatches so that values
    which are really "the same" don't get marked as unmatched just because
    they were typed/exported differently:
      - Whole-number floats vs ints (1.0 vs 1), including when they arrive
        as numeric-looking strings ("007", "7.0", "1,000").
      - Trailing decimal zeros (19.50 vs 19.5).
      - Leading zeros in numeric strings (e.g. zero-padded codes: "007" vs 7).
      - Case differences in text ("Alice" vs "alice").
    """
    if pd.isna(v) or v == "":
        return None

    s = str(v).strip()
    if s == "":
        return None

    # Try to treat it as a number - handles ints, floats, and numeric
    # strings with leading zeros, thousands separators, or a trailing ".0".
    try:
        f = float(s.replace(",", ""))
        if f.is_integer():
            return str(int(f))
        # Canonical decimal form, trimmed of trailing zeros (19.50 -> "19.5")
        return ("%f" % f).rstrip("0").rstrip(".")
    except ValueError:
        pass

    # Not numeric - fall back to case-insensitive text comparison.
    return s.lower()


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
    unmatched_s = []  # leftover source values with no match, to pair up later

    # 1. Walk source values, find a matching target value anywhere.
    for sv, sn in zip(s_vals, s_norm):
        if sn is None:
            # A blank source cell can't match anything - its own blank/blank row.
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
            # Don't write this yet - queue it so it can be paired side by
            # side with a leftover target value instead of getting its own
            # row now and the target leftover getting a separate row later
            # (which is what caused unmatched rows to land far below the
            # real data, out of alignment with the other columns).
            unmatched_s.append(sv)

    # 2. Collect any target values that were never matched to a source value.
    unmatched_t = [
        ("" if tn is None else tv)
        for tv, tn, used in zip(t_vals, t_norm, t_used)
        if not used
    ]

    # 3. Pair leftover source and target values side by side, row for row,
    #    instead of stacking them as separate trailing rows.
    for su, tu in zip_longest(unmatched_s, unmatched_t, fillvalue=""):
        rows.append((su, tu, "FALSE"))

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

######################################################################################################
# deleted the duplicates : 
"""
Here is exactly how duplicates are currently handled:

Source Duplicates (More in Source than Target): Captured perfectly. If a value appears 3 times in Source but only 1 time in Target, the first one matches (TRUE), and the next two are printed inline as unmatched (FALSE with a blank target cell).

Target Duplicates (More in Target than Source): Currently ignored. Because we removed the "target dumping" to make the columns flat, if a value appears 3 times in your Target file but only 1 time in your Source file, the extra 2 Target duplicates are completely erased from the final report.

"""



import pandas as pd


def _normalize(v):
    """Convert a cell value to a comparable string, or None if blank/NaN.

    Handles a few common cross-file formatting mismatches so that values
    which are really "the same" don't get marked as unmatched just because
    they were typed/exported differently:
      - Whole-number floats vs ints (1.0 vs 1), including when they arrive
        as numeric-looking strings ("007", "7.0", "1,000").
      - Trailing decimal zeros (19.50 vs 19.5).
      - Leading zeros in numeric strings (e.g. zero-padded codes: "007" vs 7).
      - Case differences in text ("Alice" vs "alice").
    """
    if pd.isna(v) or v == "":
        return None

    s = str(v).strip()
    if s == "":
        return None

    # Try to treat it as a number - handles ints, floats, and numeric
    # strings with leading zeros, thousands separators, or a trailing ".0".
    try:
        f = float(s.replace(",", ""))
        if f.is_integer():
            return str(int(f))
        # Canonical decimal form, trimmed of trailing zeros (19.50 -> "19.5")
        return ("%f" % f).rstrip("0").rstrip(".")
    except ValueError:
        pass

    # Not numeric - fall back to case-insensitive text comparison.
    return s.lower()


def _match_column(s_vals, t_vals):
    """Pair up equal values between a source column and a target column."""
    s_norm = [_normalize(v) for v in s_vals]
    t_norm = [_normalize(v) for v in t_vals]
    t_used = [False] * len(t_norm)

    rows = []

    # 1. Walk source values, find a matching target value anywhere.
    for sv, sn in zip(s_vals, s_norm):
        if sn is None:
            # A blank source cell can't match anything - its own blank/blank row.
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
            # Output the unmatched source value inline immediately,
            # rather than queuing it for the bottom.
            rows.append((sv, "", "FALSE"))

    # 2. TARGET DUMPING REMOVED
    # Any target values (including duplicates) that were never matched 
    # are simply ignored and will no longer cascade at the bottom of the column.

    return rows


def generate_full_comparison_report(source_path, target_path, output_path):
    # 1. Load the datasets
    df_src = pd.read_csv(source_path, encoding="utf-8", encoding_errors="ignore")
    df_tgt = pd.read_csv(target_path, encoding="utf-8", encoding_errors="ignore")

    all_source_cols = df_src.columns
    all_target_cols = df_tgt.columns
    # Preserve order of columns
    all_cols = list(dict.fromkeys(list(all_source_cols) + list(all_target_cols)))

    # 2. Build each column's report data independently
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
            # We enforce length limits based on Source length to prevent Target columns 
            # from stretching the table if they happen to be longer.
            vals = [("" if pd.isna(v) else v) for v in df_tgt[col].tolist()][:len(df_src)]
            report_columns[col] = ("target_only", vals)
            col_lengths[col] = len(vals)

    max_len = max(col_lengths.values()) if col_lengths else 0

    final_columns = {}
    for col in all_cols:
        kind, data = report_columns[col]
        if kind == "both":
            s_col = [r[0] for r in data] + [""] * (max_len - len(data))
            t_col = [r[1] for r in data] + [""] * (max_len - len(data))
            # Pad rows beyond this column's real data with a blank status
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
if __name__ == "__main__":
    generate_full_comparison_report("source.csv", "target.csv", "report.csv")

################################################################################################

# restored the duplicates: Because this script evaluates every column completely independently from the others, it does not keep "Row 5 of Column A" tied to "Row 5 of Column B".

#If you want to capture 100% of your data (including every single duplicate in the Target file), we must add those extra Target values back to the bottom of their respective columns.

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


def _match_column(s_vals, t_vals):
    """Pair up equal values between a source column and a target column."""
    s_norm = [_normalize(v) for v in s_vals]
    t_norm = [_normalize(v) for v in t_vals]
    t_used = [False] * len(t_norm)

    rows = []

    # 1. Walk source values, match 1-to-1 with target values.
    for sv, sn in zip(s_vals, s_norm):
        if sn is None:
            # A blank source cell gets its own FALSE row
            rows.append(("", "", "FALSE"))
            continue

        match_idx = None
        for j, tn in enumerate(t_norm):
            if not t_used[j] and tn == sn:
                match_idx = j
                break

        if match_idx is not None:
            # Match found! (Handles duplicates 1-to-1)
            t_used[match_idx] = True
            rows.append((sv, t_vals[match_idx], "TRUE"))
        else:
            # Unmatched Source Value (or extra Source duplicate)
            rows.append((sv, "", "FALSE"))

    # 2. Collect Unmatched Target Values (or extra Target duplicates)
    # We MUST append these so you do not lose row counts/data, even if it 
    # causes varying lengths at the bottom of the sheet.
    for used, tv, tn in zip(t_used, t_vals, t_norm):
        if not used:
            if tn is not None:
                rows.append(("", tv, "FALSE"))

    return rows


def generate_full_comparison_report(source_path, target_path, output_path):
    # 1. Load the datasets
    df_src = pd.read_csv(source_path, encoding="utf-8", encoding_errors="ignore")
    df_tgt = pd.read_csv(target_path, encoding="utf-8", encoding_errors="ignore")

    all_source_cols = df_src.columns
    all_target_cols = df_tgt.columns
    all_cols = list(dict.fromkeys(list(all_source_cols) + list(all_target_cols)))

    report_columns = {}
    col_lengths = {}

    # 2. Build each column independently
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

    # Calculate absolute max length across all lists to ensure safe padding
    max_len = max(col_lengths.values()) if col_lengths else 0

    # 3. Assemble and pad the final DataFrame
    final_columns = {}
    for col in all_cols:
        kind, data = report_columns[col]
        if kind == "both":
            s_col = [r[0] for r in data] + [""] * (max_len - len(data))
            t_col = [r[1] for r in data] + [""] * (max_len - len(data))
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
if __name__ == "__main__":
    generate_full_comparison_report("source.csv", "target.csv", "report.csv")
