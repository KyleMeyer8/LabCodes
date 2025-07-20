import pandas as pd
import os

def convert_xlsx_to_csv(start_dir):
    for root, dirs, files in os.walk(start_dir):
        for file in files:
            if file.lower().endswith('.xlsx'):
                xlsx_path = os.path.join(root, file)
                try:
                    excel_data = pd.read_excel(xlsx_path, sheet_name=None, engine='openpyxl')
                    for sheet_name, df in excel_data.items():
                        base = os.path.splitext(file)[0]
                        csv_filename = f"{base}_{sheet_name}.csv"
                        csv_path = os.path.join(root, csv_filename)
                        df.to_csv(csv_path, index=False)
                        print(f"Converted: {xlsx_path} [{sheet_name}] -> {csv_path}")
                except Exception as e:
                    print(f"Failed to convert {xlsx_path}: {e}")

if __name__ == "__main__":
    start_directory = input("Enter the starting directory: ").strip()
    if not os.path.isdir(start_directory):
        print("Invalid directory!")
    else:
        convert_xlsx_to_csv(start_directory)

#usage
#python excel_to_csv.py
#it will ask what directory(folder) you want to start in and it will act on all .xlsx files in the directory and all other directories within