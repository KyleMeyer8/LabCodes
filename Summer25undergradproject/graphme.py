import argparse
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
import sys
import re

def parse_args():
    parser = argparse.ArgumentParser(description='Flexible grouped plotting script (supports column index ranges).')
    parser.add_argument('file', type=str, help='Path to CSV file')
    parser.add_argument('graph_type', type=str, choices=['scatter', 'box', 'violin', 'bar', 'histogram'], help='Type of graph to plot')
    parser.add_argument('columns', nargs='+', help='Columns for plotting (by index range for grouped plots)')
    parser.add_argument('--title', type=str, default=None, help='Plot title')
    parser.add_argument('--xlabel', type=str, default=None, help='X-axis label')
    parser.add_argument('--ylabel', type=str, default=None, help='Y-axis label')
    parser.add_argument('--palette', type=str, default=None, help='Color palette or comma-separated list of colors')
    return parser.parse_args()

def excel_col_to_idx(col):
    """
    Convert Excel-like column letter (e.g. 'A', 'AA') to 0-based index.
    """
    col = col.upper()
    total = 0
    for c in col:
        if not ('A' <= c <= 'Z'):
            raise ValueError(f"Invalid Excel column: {col}")
        total = total * 26 + (ord(c) - ord('A') + 1)
    return total - 1

def expand_column_indices(arg_list, data):
    """
    Accepts:
      - integer ('3')
      - range of integers ('2:6', selects 2–5)
      - Excel letter ('A', 'B', 'AA')
      - Excel letter range ('A:C', 'AA:AD')
    Returns field names.
    """
    indices = []
    for item in arg_list:
        # Excel-style range like 'A:C'
        m = re.match(r'^([A-Za-z]+):([A-Za-z]+)$', item)
        if m:
            start_idx = excel_col_to_idx(m.group(1))
            end_idx = excel_col_to_idx(m.group(2)) + 1
            indices.extend(range(start_idx, end_idx))
        # Excel-style single ('AA')
        elif re.match(r'^[A-Za-z]+$', item):
            indices.append(excel_col_to_idx(item))
        # Integer range like '2:5'
        elif re.match(r'^(\d+):(\d+)$', item):
            m = re.match(r'^(\d+):(\d+)$', item)
            start, end = int(m.group(1)), int(m.group(2))
            indices.extend(range(start, end))
        # Single integer
        elif re.match(r'^\d+$', item):
            indices.append(int(item))
        else:
            print(f"Error: Invalid column identifier: '{item}'. Must be index, Excel letter, or range.", file=sys.stderr)
            sys.exit(1)
    if not all(0 <= idx < len(data.columns) for idx in indices):
        print(f"Error: Column index out of range. Data has {len(data.columns)} columns.", file=sys.stderr)
        sys.exit(1)
    return [data.columns[idx] for idx in indices]


def parse_grouped_columns(args, data):
    """For box/bar/histogram: [GroupName colRange1 colRange2 ... GroupName2 colRange3 ...] e.g. 'A' 0:3 5 'B' 3:5"""
    records = []
    i = 0
    n = len(args)
    while i < n:
        group = args[i]
        i += 1
        col_args = []
        while i < n and re.match(r'^(\d+(:\d+)?|\d+)$', args[i]):
            col_args.append(args[i])
            i += 1
        if not col_args:
            print(f"Error: No column indices specified for group '{group}'", file=sys.stderr)
            sys.exit(1)
        cols = expand_column_indices(col_args, data)
        for col in cols:
            for val in data[col].dropna():
                records.append({'Group': group, 'Value': val})
    return pd.DataFrame(records)

def get_palette(palette_arg):
    """Parse palette argument for seaborn."""
    if not palette_arg:
        return None
    if ',' in palette_arg:
        return [c.strip() for c in palette_arg.split(',')]
    return palette_arg  # Named palette

def main():
    args = parse_args()
    data = pd.read_csv(args.file)
    graph_type = args.graph_type
    columns = args.columns
    palette = get_palette(args.palette)

    plt.figure(figsize=(10, 6))

    if graph_type == 'scatter':
        if len(columns) != 2:
            print('Scatter plot requires exactly 2 columns by names or indices.', file=sys.stderr)
            sys.exit(1)
        # Support both index and name for scatter plot
        col_indices = []
        for col in columns:
            if re.match(r"^\d+$", col):
                idx = int(col)
                if idx < 0 or idx >= len(data.columns):
                    print(f"Error: Column index {idx} out of range.", file=sys.stderr)
                    sys.exit(1)
                col_indices.append(data.columns[idx])
            elif col in data.columns:
                col_indices.append(col)
            else:
                print(f"Error: Column '{col}' not found.", file=sys.stderr)
                sys.exit(1)
        colors = None
        if palette:
            if isinstance(palette, list):
                colors = palette if len(palette) == 2 else palette[0]
            else:
                colors = palette
        plt.scatter(data[col_indices[0]], data[col_indices[1]], c=colors)
        plt.xlabel(args.xlabel or col_indices[0])
        plt.ylabel(args.ylabel or col_indices[1])
        plt.title(args.title or f"Scatter plot of {col_indices[0]} vs {col_indices[1]}")
    elif graph_type == 'box':
        df_long = parse_grouped_columns(columns, data)
        if df_long.empty:
            print("Error: No data to plot.", file=sys.stderr)
            sys.exit(1)
        sns.boxplot(x='Group', y='Value', data=df_long, palette=palette)
        plt.xlabel(args.xlabel or "Group")
        plt.ylabel(args.ylabel or "Value")
        plt.title(args.title or "Box Plot")
    elif graph_type == 'violin':
        col_indices = expand_column_indices(columns, data)
        sns.violinplot(data=data[col_indices], palette=palette)
        plt.xlabel(args.xlabel or "Column")
        plt.ylabel(args.ylabel or "Value")
        plt.title(args.title or "Violin plot for selected columns")
    elif graph_type == 'bar':
        df_long = parse_grouped_columns(columns, data)
        if df_long.empty:
            print("Error: No data to plot.", file=sys.stderr)
            sys.exit(1)
        group_means = df_long.groupby('Group')['Value'].mean().reset_index()
        sns.barplot(x='Group', y='Value', data=group_means, palette=palette)
        plt.xlabel(args.xlabel or "Group")
        plt.ylabel(args.ylabel or "Mean Value")
        plt.title(args.title or "Bar Plot (Mean Value)")
    elif graph_type == 'histogram':
        df_long = parse_grouped_columns(columns, data)
        if df_long.empty:
            print("Error: No data to plot.", file=sys.stderr)
            sys.exit(1)
        for idx, (group, group_df) in enumerate(df_long.groupby('Group')):
            color = None
            if palette:
                if isinstance(palette, list):
                    color = palette[idx % len(palette)]
                else:
                    color = palette
            sns.histplot(group_df['Value'], label=group, kde=False, bins=20, alpha=0.5, color=color)
        plt.xlabel(args.xlabel or "Value")
        plt.ylabel(args.ylabel or "Frequency")
        plt.title(args.title or "Grouped Histogram")
        plt.legend(title="Group")
    else:
        print('Unsupported graph type.', file=sys.stderr)
        sys.exit(1)

    plt.tight_layout()
    plt.show()

if __name__ == '__main__':
    main()

#use:
#python script.py data.csv scatter ColX ColY
#python script.py data.csv box "Group A" A1 A2 "Group B" B1 B2 "Group C" C1
# these column headers can either be #s or excel letters, just remember that column 1 is column 0
#python graphme.py violindata.csv violin areaA12 areaB12 areaC12
#python script.py data.csv bar "label" Col1 "label2" Col3
#python script.py data.csv histogram "label" A1 "label2" B1
#optional arguments:
#--title "title"
#--xlabel "label"
#--ylabel "label"
#--palette "colors in order left to right separated by comma"