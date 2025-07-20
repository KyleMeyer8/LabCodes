import os
import argparse
import subprocess
import sys
from rich.console import Console
import glob
import re
import time
from tabulate import tabulate


console = Console()

def run_foldx_command(command):
    """run a FoldX command and return detailed output"""
    try:
        result = subprocess.run(command, check=True, capture_output=True, text=True)
        return result
    except subprocess.CalledProcessError as err:
        return err

def repair_pdb(base_pdb_name):
    pdb_file = f"{base_pdb_name}.pdb"
    cmd = ['foldx', '--command=RepairPDB', f'--pdb={pdb_file}']
    result = run_foldx_command(cmd)
    returncode = result.returncode
    repaired_file = f"{base_pdb_name}_Repair.pdb"
    if not os.path.exists(repaired_file):
        raise FileNotFoundError("Repaired PDB not generated")
    if returncode != 0:
        console.log(f"[red]RepairPDB failed for {pdb_file}[/red]")
    if returncode ==0:
        console.log(f"[green]Repaired PDB: {repaired_file}[/green]")
    return repaired_file

def make_mutation_list(residues):
    amino_acids = ['A', 'C', 'D', 'E', 'F', 'G', 'H', 'I', 'K', 'L', 'M', 'N', 'P', 'Q', 'R', 'S', 'T', 'V', 'W', 'Y']
    mutations = []
    for chain, pos, wt in residues:
        for aa in amino_acids:
            if aa != wt:
                mutations.append(f"{wt}{chain}{pos}{aa};\n")
    with open("individual_list.txt", "w") as file:
        file.writelines(mutations)
    num_lines = len(mutations)
    if num_lines % 19 != 0:
        raise ValueError(f"Number of mutations ({num_lines}) is not correct.")
    console.log("[green]Mutation list created: individual_list.txt[/green]")

def get_mutation_names(mutation_file="individual_list.txt"):
    mutation_names = []
    with open(mutation_file) as f:
        for line in f:
            line = line.strip().rstrip(';')
            if line:
                mutation_names.append(line)
    return mutation_names

"""separate the WT from the mutant files"""
def file_key(filename):
    match = re.search(r'_(\d+)\.pdb$', filename)
    if match:
        return int(match.group(1))
    else:
        return -1

"""rename mutation files generated as the mutation rather than just numerically"""
def rename_pdb_files(repaired_pdb, mutation_names):
    base = os.path.splitext(repaired_pdb)[0]
    pdb_files = glob.glob(f"{base}_*.pdb")
    pdb_files = sorted(pdb_files, key=file_key)
    if len(pdb_files) != len(mutation_names):
        print("Warning: PDB files and mutation names are not equal!")
        return
    for pdb_file, mutation in zip(pdb_files, mutation_names):
        new_name = f"{base}_{mutation}.pdb"
        print(f"Renaming {pdb_file} -> {new_name}")
        os.rename(pdb_file, new_name)

"""generate mutated models based on the mutation in the mutation list"""
def run_mutations(repaired_pdb):
    cmd = ['foldx', '--command=BuildModel', f'--pdb={repaired_pdb}', '--mutant-file=individual_list.txt', '--numberOfRuns=1', '--out-pdb=true']
    result = run_foldx_command(cmd)
    console.log(f"BuildModel stdout:\n{result.stdout}")
    console.log(f"BuildModel stderr:\n{result.stderr}")
    mutation_names = get_mutation_names("individual_list.txt")
    rename_pdb_files(repaired_pdb, mutation_names)
    console.log("[green]Mutant Structures Generated[/green]")

"""stability calculations need retry capabilities because it'll get random errors on different computers"""
def run_foldx_stability(base_pdb_name, max_retries=3, retry_delay=5):
    file_pattern = f"{base_pdb_name}_Repair*.pdb"
    matching_files = glob.glob(file_pattern)
    if not matching_files:
        console.print(f"[red]No files found matching the pattern: {file_pattern}[/red]")
        return None
    error_files = []
    for pdb_file in matching_files:
        console.log(f"Running stability calculation for: {pdb_file}")
        success = False
        for attempt in range(max_retries):
            cmd = ['foldx', '--command=Stability', f'--pdb={pdb_file}']
            result = run_foldx_command(cmd)
            if result.returncode == 0:
                console.log(f"[green]Stability calculation completed for {pdb_file}[/green]")
                success = True
                break
            else:
                console.print(f"[yellow]Error running stability calculation for {pdb_file} (Attempt {attempt + 1}/{max_retries}):[/yellow]")
                if attempt < max_retries - 1:
                    console.print(f"Retrying in {retry_delay} seconds...")
                    time.sleep(retry_delay)
        if not success:
            error_files.append(pdb_file)
    if error_files:
        console.print("[red]The following files failed stability calculation after retries:[/red]")
        for f in error_files:
            console.print(f"[red]{f}[/red]")
        return False
    else:
        console.log("[green]All stability calculations finished successfully[/green]")
        return True

def subtract_fields(file_pattern):
    file1 = f"{file_pattern}_Repair_0_ST.fxout"
    file2_list = sorted(glob.glob(f"{file_pattern}_Repair_*_0_ST.fxout"))
    individual_list_file = "individual_list.txt"
    output_file = "ddgcalcoutput.txt"
    if not file2_list:
        print(f"No files found matching the pattern: {file2_list}")
        return
    individual_lines = []
    with open(individual_list_file, 'r') as ind_list:
        for line in ind_list:
            if line.strip():
                cleaned_line = line.strip().rstrip(';')
                individual_lines.append(cleaned_line)
    results = []
    headers = ["Mutation", "Source File", "Stability (DDG)"]
    mutation_lookup = {}
    for mut in individual_lines:
        mutation_lookup[mut] = mut
    for file2 in file2_list:
        if file2.endswith("Repair_0_ST.fxout"):
            continue
        match = re.search(r'([A-Z]{2}\d{1,3}[A-Z])', file2)
        if not match:
            print(f"Warning: Could not extract mutation code from filename: {file2}")
            continue
        mutation_code = match.group(1)
        individual_text = mutation_lookup.get(mutation_code, mutation_code)
        with open(file1, 'r') as f1, open(file2, 'r') as f2:
            for line1, line2 in zip(f1, f2):
                fields1 = line1.strip().split()
                fields2 = line2.strip().split()
                if len(fields1) < 2 or len(fields2) < 2:
                    print(f"Skipping line due to insufficient fields in {file2}: {line1.strip()} or {line2.strip()}")
                    continue
                try:
                    value1 = float(fields1[1])
                    value2 = float(fields2[1])
                    result = value2 - value1
                    results.append([individual_text, file2, result])
                except ValueError:
                    print(f"Skipping line due to non-numeric value in {file2}: {line1.strip()} or {line2.strip()}")
        console.log(f"[cyan]Processed {file2}[/cyan]")
#"""grouping results first by amino acid number and then sorting by DDG within each group"""
    groups = {}
    for row in results:
        mutation = row[0]
        match = re.match(r'^([A-Z]{2})(\d{1,3})([A-Z])$', mutation)
        if match:
            num = int(match.group(2))
            groups.setdefault(num, []).append(row)
        else:
            print(f"Warning: Could not extract number from mutation '{mutation}' - using 0")
            groups.setdefault(0, []).append(row)
    sorted_groups = sorted(groups.items(), key=lambda x: x[0])
    final_results = []
    for num, group_rows in sorted_groups:
        sorted_group = sorted(group_rows, key=lambda x: -x[2])
        final_results.extend(sorted_group)
    formatted_results = [[row[0], row[1], f"{row[2]:.4f}"] for row in final_results]
    column_widths = [len(header) for header in headers]
    for row in formatted_results:
        for i, cell in enumerate(row):
            column_widths[i] = max(column_widths[i], len(cell))
    bottom_line = ["-" * width for width in column_widths]
    with open(output_file, 'w') as out:
        out.write(tabulate(formatted_results, headers=headers, tablefmt="plain") + "\n")
        out.write("  ".join(bottom_line) + "\n")
    console.log(f"[cyan]All results written to {output_file}[/cyan]")
    console.log("[green]DDG calculations completed[/green]")

def main():
    parser = argparse.ArgumentParser(description='FoldX Comprehensive Mutagenesis')
    parser.add_argument('--pdb_file', required=True, help='Input PDB file')
    parser.add_argument('--residues', required=True, nargs='+', help='Residues in ChainID:Position:WT format (e.g., A:214:E)')
    args = parser.parse_args()
    base_pdb_name = os.path.splitext(os.path.basename(args.pdb_file))[0]
    if not os.path.exists(f"{base_pdb_name}.pdb"):
        console.print(f"[red]Error: PDB file {base_pdb_name}.pdb not found![/red]")
        sys.exit(1)
    if not os.path.splitext(os.path.basename(args.pdb_file))[1] == ".pdb":
        console.print(f"[red]Error: This is not a .pdb file![/red]")
        sys.exit(1)
    residues = []
    for res in args.residues:
        try:
            chain, pos, wt = res.split(':')
            if len(wt) != 1 or not wt.isalpha():
                raise ValueError
            residues.append((chain, pos, wt))
        except ValueError:
            console.print(f"[red]Invalid residue format: {res}. Use ChainID:Position:WT (e.g., A:123:R)[/red]")
            sys.exit(1)
    try:
        with console.status("[bold magenta]Repairing PDB...[/bold magenta]", spinner="dots"):
            repaired_pdb = repair_pdb(base_pdb_name)
        if not os.path.exists(repaired_pdb):
            console.print(f"[red]Repaired PDB file not found: {repaired_pdb}[/red]")
            sys.exit(1)
        with console.status("[bold magenta]Generating mutation list...[/bold magenta]", spinner="dots"):
            make_mutation_list(residues)
        with console.status("[bold magenta]Building mutated models...[/bold magenta]", spinner="dots"):
            run_mutations(repaired_pdb)
        with console.status("[bold magenta]Running stability calculations...[/bold magenta]", spinner="dots"):
            run_foldx_stability(base_pdb_name)
        with console.status("[bold magenta]Running DDG calculations...[/bold magenta]", spinner="dots"):
            subtract_fields(base_pdb_name)
    except Exception as e:
        console.print(f"[red]Critical error: {str(e)}[/red]")
        sys.exit(1)

if __name__ == "__main__":
    console.log("[bold blue]Starting FoldX mutation workflow[/bold blue]")
    main()
    console.log("[bold green]All calculations finished[/bold green]")

# Usage:
# python single_mutation.py --pdb_file your_protein.pdb --residues chainID:aminoacid#:WTaminoacid