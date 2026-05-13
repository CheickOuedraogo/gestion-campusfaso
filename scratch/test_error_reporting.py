import pandas as pd
import os
import re

# Mock detect_separator for testing
def detect_separator(filepath):
    return ';'

# The updated load_file logic (copied for testing)
def load_file(filepath):
    ext = os.path.splitext(filepath)[1].lower()
    try:
        if ext == '.csv':
            sep = detect_separator(filepath)
            try:
                df = pd.read_csv(filepath, sep=sep, dtype=str, encoding='utf-8', keep_default_na=False)
            except pd.errors.ParserError as e:
                msg = str(e)
                match = re.search(r"line (\d+)", msg)
                line_data = ""
                if match:
                    line_num = int(match.group(1))
                    try:
                        with open(filepath, 'r', encoding='utf-8', errors='replace') as f:
                            for i, line in enumerate(f, 1):
                                if i == line_num:
                                    line_data = f"\n\n👉 CONTENU DE LA LIGNE {line_num} :\n{line.strip()}"
                                    break
                    except:
                        pass
                
                raise ValueError(
                    f"Erreur de structure dans le CSV.\n"
                    f"Message : {msg}{line_data}\n\n"
                    f"Vérifiez s'il n'y a pas des '{sep}' en trop ou manquants dans cette ligne."
                )
        return df
    except Exception as e:
        if isinstance(e, ValueError): raise e
        raise ValueError(f"Erreur lors de la lecture du fichier : {e}")

# Create a corrupted CSV
test_csv = "test_corrupt.csv"
with open(test_csv, "w") as f:
    f.write("col1;col2;col3\n")
    f.write("val1;val2;val3\n")
    f.write("err1;err2;err3;err4\n") # Extra column here (line 3)

try:
    load_file(test_csv)
except ValueError as e:
    print(f"Caught expected error:\n{e}")

os.remove(test_csv)
