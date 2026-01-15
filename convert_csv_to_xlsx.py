import pandas as pd

# filepath: convert_csv_to_xlsx.py
csv_path = "leads.csv"
xlsx_path = "/mnt/c/Users/Filip/Desktop/leads.xlsx"

df = pd.read_csv(csv_path)
df.to_excel(xlsx_path, index=False)