This script takes arguments in the form of amino acids for a certain PDB file and mutates each residue to the other 19 amino acids to find the stability of each single mutation


You need 2 files within the same directory:
1. Original structure of protein in .pdb format
2. single_mutation.py

***If running this code again, first clear directory of all files generated from the last run***

To execute:
python single_mutation.py --pdb_file <original PDB file> --residues <chain ID:residue #:WT amino acid>...
Example:
python single_mutation.py --pdb_file KaiCII_EA.pdb --residues A:468:R
Note: 
You can put as many residues in as you want

--Execute loopyloop.py with the parameters below for each script. The 2nd line of each step is how to run the script on the command line. This is the order of operations and what it gives you:--

What does each function do?

run_foldx_command(command)
This runs all the foldx commands on the command line for the repair, building models, and stability calculations

repair_pdb(base_pdb_name)
This first repairs the WT PDB model to minimize free energy so that the only difference in the calculated protein forces is due to the mutations
Output: <original WT model name>_Repair.pdb and <original WT model name>_Repair.fxout
Errors:
1. PDB file that should be generated was not generated
2. Generic function didn't work because returncode was not 0

make_mutation_list(residues)
This makes the list of mutations (called individual_list.txt) for foldx to make all the mutation models. It looks at the residue arguments you gave it and lists the other 19 natural amino acids to mutate to. There is 1 mutation per line in the pattern of <WT amino acid><chain ID><residue #><mutation amino acid> and each line is terminated by a semicolon
Output: individual_list.txt
Errors:
1. The number of mutations in the individual_list.txt is not divisible by 19, meaning there are not the right number of mutations in the list

get_mutation_names(mutation_file="individual_list.txt")
This gets the names of each mutation from each line of the individual_list.txt in order to use it later to organize all the files foldx makes

file_key(filename)
This first groups file names into whether they have a mutation code in the file name or not to separate the WT from the mutant files

rename_pdb_files(repaired_pdb, mutation_names)
This renames all the mutant files to include their mutation codes so it's easy to see which mutation goes with which file
Note: This will only rename files to names that do not already exist. If you are redoing a run of this code, clear out all past PDB models except for the WT first
Errors: 
1. There are a different number of PDB files and mutation numbers so the files can't be renamed properly

run_mutations(repaired_pdb)
This runs the foldx command (through run_foldx_command(command)) to build mutant PDB models for each mutation. That means there will be 1 new PDB file for each mutation in the individual_list.txt with the specified residue mutated accordingly
Output: mutant PDB files

run_foldx_stability(base_pdb_name, max retries=3, retry_delay=5)
This runs the foldx command (through run_foldx_command(command)) to calculate the stability for each PDB file. When running this function for many PDB files, some computers get random errors. So each file that results in an error is retried up to 3 times
Output: stability files for each PDB in the form of .fxout files
Errors:
1. No file names matching the needed file pattern found in the current directory
2. Retrying stability calculations/number of retries has reached the maximum number
3. Which files need to be retried

subtract_fields(file_pattern)
This reads the stability files for the mutants and WT and subtracts the free energy values to get the delta delta G (DDG) value for each mutant. It then outputs all the mutations, their source files, and their DDG in an easy to read table that is first grouped by amino acid number and then sorted by DDG from high to low
Output: ddgcalcoutput.txt
Errors:
1. Can't get mutation code from the file name. Either the file was named incorrectly or there are extra files in the directory that have not been cleared since the last run of this code

main()
This handles all the arguments and the base file name and runs all the functions while displaying what function is in progress along with generic error codes
