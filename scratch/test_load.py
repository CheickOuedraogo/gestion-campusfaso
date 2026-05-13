import pandas as pd
import os

def detect_separator(filepath):
    try:
        with open(filepath, 'r', encoding='utf-8', errors='replace') as f:
            for line in f:
                line = line.strip()
                if line:
                    sc = line.count(';')
                    co = line.count(',')
                    print(f"Line: {line} | ; : {sc} | , : {co}")
                    return ';' if sc >= co else ','
    except Exception as e:
        print(f"Error in detect: {e}")
    return ','

def load_file(filepath):
    ext = os.path.splitext(filepath)[1].lower()
    if ext in ('.xlsx', '.xls'):
        df = pd.read_excel(filepath, dtype=str, keep_default_na=False)
    elif ext == '.csv':
        sep = detect_separator(filepath)
        print(f"Detected sep: {sep}")
        df = pd.read_csv(filepath, sep=sep, dtype=str, encoding='utf-8', keep_default_na=False)
    else:
        raise ValueError(f"Format non supporté : {ext}")

    print(f"Raw columns: {list(df.columns)}")
    df.columns = [col.strip().lstrip('\ufeff') for col in df.columns]
    print(f"Cleaned columns: {list(df.columns)}")
    return df

if __name__ == "__main__":
    pv_path = "/home/juju5302/Bureau/stage/gestion-campusfaso/test_data/pv_test.csv"
    if os.path.exists(pv_path):
        print(f"Testing {pv_path}")
        load_file(pv_path)
    else:
        print("PV test file not found")
