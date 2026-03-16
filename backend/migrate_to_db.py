import pandas as pd
import sqlite3
import os

DATA_DIR = r"c:\Users\dgods\Documents\stuff\ibm_hacks\data"
DB_PATH = os.path.join(DATA_DIR, "mineralwatch.db")

def migrate():
    print(f"Starting migration to {DB_PATH}...")
    conn = sqlite3.connect(DB_PATH)
    
    # 1. USGS Data
    print("Migrating USGS data...")
    usgs_path = os.path.join(DATA_DIR, "Semiconductor_Minerals_USGS_Map_With_HTS.xlsx")
    df_usgs = pd.read_excel(usgs_path)
    df_usgs.to_sql("usgs_minerals", conn, if_exists="replace", index=False)
    
    # 2. EDGAR Data
    print("Migrating EDGAR data...")
    edgar_path = os.path.join(DATA_DIR, "edgar_mineral_results.xlsx")
    xl_edgar = pd.ExcelFile(edgar_path)
    
    sheets = xl_edgar.sheet_names
    for sheet in sheets:
        print(f"  - Processing sheet: {sheet}")
        df = xl_edgar.parse(sheet)
        table_name = "edgar_" + sheet.lower().replace(" ", "_").replace("-", "_")
        df.to_sql(table_name, conn, if_exists="replace", index=False)
    
    # 3. USITC Data
    print("Migrating USITC trade data...")
    usitc_path = os.path.join(DATA_DIR, "usitc_clean.xlsx")
    df_usitc = pd.read_excel(usitc_path)
    df_usitc.to_sql("trade_data", conn, if_exists="replace", index=False)
    
    print("Creating indices...")
    cursor = conn.cursor()
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_edgar_details_company ON edgar_filing_details (Company)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_edgar_details_mineral ON edgar_filing_details (Mineral)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_trade_mineral ON trade_data (Mineral)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_trade_country ON trade_data (Country)")
    
    conn.commit()
    conn.close()
    print("Migration complete!")

if __name__ == "__main__":
    migrate()
