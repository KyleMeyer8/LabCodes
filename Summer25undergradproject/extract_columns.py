import os
import csv
import sys
import re

def extract_column_from_csv(file_path, column_name):
    """Extract a column from a CSV file given the column header."""
    values = []
    with open(file_path, newline='', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        if column_name not in reader.fieldnames:
            return None  # Column not found
        for row in reader:
            values.append(row[column_name])
    return values

def clean_header(header, delete_pattern):
    # if pattern like delete_*_this, replace with capturing group
    match = re.fullmatch(delete_pattern, header)
    if match:
        return match.group(1)
    return header

def pattern_from_template(template):
    # Convert template like delete_*_this to regex like r'delete_(.*)_this'
    # Escape all regex characters except for the * representing the capturing group
    parts = template.split('*')
    if len(parts) != 2:
        return None # not a valid simple pattern
    pre, post = map(re.escape, parts)
    return re.compile(f'^{pre}(.*){post}$')

def main(start_dir, column_name, pattern_template=""):
    # Find all CSV files
    csv_files = []
    for root, dirs, files in os.walk(start_dir):
        for file in files:
            if file.lower().endswith('.csv') and file != 'data.csv':
                csv_files.append(os.path.join(root, file))

    # Extract columns
    data_dict = {}
    max_len = 0
    for file_path in csv_files:
        col = extract_column_from_csv(file_path, column_name)
        if col is not None:
            file_key = os.path.splitext(os.path.basename(file_path))[0]
            data_dict[file_key] = col
            max_len = max(max_len, len(col))
        else:
            print(f"Warning: Column '{column_name}' not found in {file_path}")

    headers = list(data_dict.keys())
    if pattern_template and '*' in pattern_template:
        header_re = pattern_from_template(pattern_template)
        if header_re is not None:
            new_headers = [
                (header_re.fullmatch(h).group(1) if header_re.fullmatch(h) else h)
                for h in headers
            ]
        else:
            print("Invalid pattern template for header cleaning.")
            sys.exit(1)
    else:
        new_headers = headers

    rows = []
    for i in range(max_len):
        row = []
        for h in headers:
            row.append(data_dict[h][i] if i < len(data_dict[h]) else "")
        rows.append(row)

    # Write to data.csv
    with open('data.csv', 'w', newline='', encoding='utf-8') as out_file:
        writer = csv.writer(out_file)
        writer.writerow(new_headers)
        writer.writerows(rows)

    print("Extracted columns written to data.csv.")

if __name__ == "__main__":
    if len(sys.argv) not in (3, 4):
        print("Usage: python extract_columns.py <starting_directory> <column_name> [header_delete_pattern]")
        print("Example: python extract_columns.py ./ mycol 'delete_*_this'")
        sys.exit(1)
    pattern_template = sys.argv[3] if len(sys.argv) == 4 else ""
    main(sys.argv[1], sys.argv[2], pattern_template)

#usage:
#python extract_columns.py /path/to/start/directory "ColumnHeader" "delete_*_this"
#it will extract all columns with the given header from all .csv files in the given directory and all directories within
#* is whatever part of the header string you DO NOT want to delete
