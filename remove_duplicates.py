import re
import shutil
import os

# ==============================
# CONFIG
# ==============================
input_file = "herbalapp/views.py"
backup_file = "herbalapp/views_backup.py"
output_file = "herbalapp/views_cleaned.py"

# ==============================
# BACKUP ORIGINAL FILE
# ==============================
if not os.path.exists(input_file):
    print(f"❌ Error: {input_file} not found!")
    exit(1)

shutil.copy2(input_file, backup_file)
print(f"✅ Backup created: {backup_file}")

# ==============================
# READ ORIGINAL FILE
# ==============================
with open(input_file, "r", encoding="utf-8") as f:
    lines = f.readlines()

# ==============================
# PROCESS FUNCTIONS
# ==============================
functions_seen = {}
new_lines = []
i = 0

while i < len(lines):
    line = lines[i]
    match = re.match(r"^(\s*)def (\w+)\(", line)
    if match:
        indent, func_name = match.groups()
        if func_name in functions_seen:
            # Duplicate found – comment out this function
            print(f"⚠️ Duplicate function '{func_name}' at line {i+1}, marking for review")
            new_lines.append(f"{indent}# ⚠️ DUPLICATE – MARKED FOR REVIEW\n")
            # Comment out all lines of this function until next top-level def or EOF
            i += 1
            while i < len(lines):
                next_line = lines[i]
                # stop if new top-level function starts (no indent)
                if re.match(r"^def \w+\(", next_line):
                    break
                new_lines.append(f"# {next_line}" if next_line.strip() else next_line)
                i += 1
            continue  # skip increment at bottom
        else:
            # First occurrence – keep
            functions_seen[func_name] = i
    new_lines.append(line)
    i += 1

# ==============================
# WRITE CLEANED FILE
# ==============================
with open(output_file, "w", encoding="utf-8") as f:
    f.writelines(new_lines)

print(f"✅ Done! Duplicates marked in '{output_file}'")
print("ℹ️ Review the cleaned file before replacing your original views.py")

