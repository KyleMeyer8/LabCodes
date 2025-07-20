import argparse
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
import numpy as np
import sys
import re
from scipy.stats import f_oneway, ttest_ind

def excel_col_to_idx(col):
    col = col.upper()
    total = 0
    for c in col:
        if not ('A' <= c <= 'Z'):
            raise ValueError(f"Invalid Excel column: {col}")
        total = total * 26 + (ord(c) - ord('A') + 1)
    return total - 1

def expand_column_indices(arg_list, data):
    indices = []
    for item in arg_list:
        m = re.match(r'^([A-Za-z]+):([A-Za-z]+)$', item)
        if m:
            start_idx = excel_col_to_idx(m.group(1))
            end_idx = excel_col_to_idx(m.group(2)) + 1
            indices.extend(range(start_idx, end_idx))
        elif re.match(r'^[A-Za-z]+$', item):
            indices.append(excel_col_to_idx(item))
        elif re.match(r'^(\d+):(\d+)$', item):
            m = re.match(r'^(\d+):(\d+)$', item)
            start, end = int(m.group(1)), int(m.group(2))
            indices.extend(range(start, end))
        elif re.match(r'^\d+$', item):
            indices.append(int(item))
        else:
            print(f"Error: Invalid column identifier: '{item}'", file=sys.stderr)
            sys.exit(1)
    if not all(0 <= idx < len(data.columns) for idx in indices):
        print(f"Error: Column index out of range. Data has {len(data.columns)} columns.", file=sys.stderr)
        sys.exit(1)
    return [data.columns[idx] for idx in indices]

def parse_grouped_columns(args, data):
    records = []
    i = 0
    n = len(args)
    group_order = []
    while i < n:
        group = args[i]
        group_order.append(group)
        i += 1
        col_args = []
        while i < n and re.match(r'^\d+(:\d+)?$|^[A-Za-z]+(:[A-Za-z]+)?$', args[i]):
            col_args.append(args[i])
            i += 1
        if not col_args:
            print(f"Error: No column indices specified for group '{group}'", file=sys.stderr)
            sys.exit(1)
        cols = expand_column_indices(col_args, data)
        for col in cols:
            for val in data[col].dropna():
                records.append({'Group': group, 'Value': val})
    return pd.DataFrame(records), group_order

def get_palette(palette_arg):
    if not palette_arg:
        return None
    if ',' in palette_arg:
        return [c.strip() for c in palette_arg.split(',')]
    return palette_arg

def get_significance_asterisks(p):
    if p < 0.001:
        return '***'
    elif p < 0.01:
        return '**'
    elif p < 0.05:
        return '*'
    else:
        return ''

def filter_outliers_iqr(series):
    # Finds values NOT considered outliers, using the 1.5*IQR rule[1][4].
    q1 = series.quantile(0.25)
    q3 = series.quantile(0.75)
    iqr = q3 - q1
    lower_bound = q1 - 1.5 * iqr
    upper_bound = q3 + 1.5 * iqr
    return series[(series >= lower_bound) & (series <= upper_bound)]

def add_significance_bar(ax, x1, x2, y, p_value, h=0.05):
    ax.plot([x1, x1, x2, x2], [y, y+h, y+h, y], lw=1.5, c='black')
    text = get_significance_asterisks(p_value)
    if text:
        ax.text((x1 + x2)/2, y + h, text, ha='center', va='bottom', color='black', fontsize=14)

def main():
    parser = argparse.ArgumentParser(description='Grouped boxplot from CSV, with outlier-filtered ANOVA and significance annotation')
    parser.add_argument('file', type=str, help='CSV file path')
    parser.add_argument('columns', nargs='+', help='Groups and their column indices/ranges')
    parser.add_argument('--title', type=str, default=None, help='Plot title')
    parser.add_argument('--xlabel', type=str, default=None, help='X-axis label')
    parser.add_argument('--ylabel', type=str, default=None, help='Y-axis label')
    parser.add_argument('--palette', type=str, default=None, help='Comma separated colors or palette name')
    args = parser.parse_args()

    data = pd.read_csv(args.file)
    palette = get_palette(args.palette)
    df_long, group_order = parse_grouped_columns(args.columns, data)
    if df_long.empty:
        print("Error: No data to plot.", file=sys.stderr)
        sys.exit(1)

    # Get non-outlier data for stats, but keep original data for plotting
    nonoutlier_data = {}
    for group in group_order:
        vals = df_long[df_long['Group'] == group]['Value']
        nonoutlier_data[group] = filter_outliers_iqr(vals)

    # Remove groups that are empty after outlier removal
    group_data = [ser for ser in [nonoutlier_data[g] for g in group_order] if len(ser)]
    clean_order = [g for g in group_order if len(nonoutlier_data[g])]

    if len(group_data) < 2:
        print("Not enough groups left after removing outliers for statistical analysis.", file=sys.stderr)
        sys.exit(1)

    # One-way ANOVA (on non-outlier data)
    f_stat, p_anova = f_oneway(*group_data)
    print(f"ANOVA F-statistic: {f_stat:.3f}, p-value: {p_anova:.3g}")
    if p_anova < 0.05:
        print("There is a significant difference between groups (ANOVA p < 0.05).")
    else:
        print("No significant difference between groups (ANOVA p >= 0.05).")

    # Pairwise t-tests (on non-outlier data)
    # Pairwise t-tests (on non-outlier data)
    pairs = []
    p_values = []
    for i in range(len(clean_order)):
        for j in range(i + 1, len(clean_order)):
            g1 = clean_order[i]
            g2 = clean_order[j]
            vals1 = nonoutlier_data[g1]
            vals2 = nonoutlier_data[g2]
            if len(vals1) > 1 and len(vals2) > 1:
                tstat, p = ttest_ind(vals1, vals2, equal_var=False)
                pairs.append((i, j))
                p_values.append(p)

    # Print all pairwise p-values
    print("\nPairwise p-values (t-tests, corrected for outlier removal):")
    for (i, j), p in zip(pairs, p_values):
        g1, g2 = clean_order[i], clean_order[j]
        stars = get_significance_asterisks(p)
        print(f"{g1} vs {g2}: p = {p:.3g} {stars}")

    # For plotting significance bars only for significant results (<0.05)
    sig_pairs = [((i, j), p) for (i, j), p in zip(pairs, p_values) if p < 0.05]



    # Plot all data for boxplot, but stats are done only on non-outlier data.
    plt.figure(figsize=(10,6))
    ax = sns.boxplot(x='Group', y='Value', data=df_long, palette=palette, order=group_order)

    plt.xlabel(args.xlabel or "Group")
    plt.ylabel(args.ylabel or "Value")
    plt.title(args.title or "Box Plot with Outlier-filtered ANOVA and Significant Bars")

    # Add only significant bars
    if sig_pairs:
        y_offset = df_long['Value'].max() * 0.05
        box_max = df_long.groupby('Group')['Value'].max().reindex(group_order).values
        line_offsets = [y_offset * (idx+1) for idx in range(len(sig_pairs))]
        for n, ((i, j), p) in enumerate(sig_pairs):
            y = max(box_max[i], box_max[j]) + line_offsets[n]
            add_significance_bar(ax, i, j, y, p, h=y_offset*0.4)

    plt.tight_layout()
    plt.show()

if __name__ == '__main__':
    main()

#Stars: * for p < 0.05, ** for p < 0.01, *** for p < 0.001, otherwise not significant
#python script.py data.csv "Group A" A1 A2 "Group B" B1 B2 "Group C" C1
#optional arguments:
#--title "title"
#--xlabel "label"
#--ylabel "label"
#--palette "colors in order left to right separated by comma"
#python boxplus.py data.csv "Empty 24hr" A F K Q "KaiA 24hr" W AC AI AO "KaiB 24hr" AU BA BG BM "KaiC 24hr" BS BY CE CK