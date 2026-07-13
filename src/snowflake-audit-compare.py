import pandas as pd

def compare_metadata_reports(old_file, new_file):
    # Load the CSVs
    df_old = pd.read_csv(old_file)
    df_new = pd.read_csv(new_file)

    # Define the key that identifies a unique column within a table
    # Schema + Table + Column name provides a unique identifier
    key = ['database_name', 'schema_name', 'table_name', 'column_name']

    # Merge the two dataframes
    # outer join captures everything in both files
    comparison = pd.merge(df_old, df_new, on=key, how='outer', suffixes=('_old', '_new'), indicator=True)

    # 1. Identify New Columns
    added = comparison[comparison['_merge'] == 'right_only']
    
    # 2. Identify Dropped Columns
    dropped = comparison[comparison['_merge'] == 'left_only']

    # 3. Identify Changed Metadata (e.g., data type or nullability changed)
    # We look for rows where the data exists in both, but columns differ
    changed = comparison[comparison['_merge'] == 'both'].copy()
    
    # Filter for columns that actually have differences
    diff_mask = False
    for col in df_old.columns:
        if col not in key:
            diff_mask |= (changed[f'{col}_old'] != changed[f'{col}_new'])
    
    changed = changed[diff_mask]

    # Display results
    print(f"--- Comparison Report ---")
    print(f"Added columns: {len(added)}")
    print(f"Dropped columns: {len(dropped)}")
    print(f"Metadata changes: {len(changed)}")

    # Optionally save to a CSV
    if not (added.empty and dropped.empty and changed.empty):
        with pd.ExcelWriter("metadata_diff.xlsx") as writer:
            added.to_excel(writer, sheet_name='Added', index=False)
            dropped.to_excel(writer, sheet_name='Dropped', index=False)
            changed.to_excel(writer, sheet_name='Changed', index=False)
        print("Detailed differences saved to 'metadata_diff.xlsx'")

if __name__ == "__main__":
    # Replace these with your actual filenames
    compare_metadata_reports("snowflake_metadata_20260713_090000.csv", 
                             "snowflake_metadata_20260713_211408.csv")
