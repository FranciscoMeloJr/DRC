import os, sys, datetime, csv, json
from advisor_engine import DRCAdvisor

def analise_yaml(file_path=None):
    theme = {}

    # Load Severity Configuration
    conf_path = os.path.join("kcs", "severity_config.csv")
    if os.path.exists(conf_path):
        with open(conf_path, mode='r', encoding='utf-8-sig') as f:
            reader = csv.DictReader(f)
            reader.fieldnames = [n.strip() for n in reader.fieldnames]
            for row in reader:
                # Store labels and initialize counts
                theme[row['criticality'].strip().upper()] = {
                    'label': row['label'].strip(),
                    'count': 0
                }

    # --- PARAMETER HANDLING ---
    if not file_path:
        file_path = sys.argv[1] if len(sys.argv) > 1 else input("Enter full YAML File Path: ")

    if not os.path.isfile(file_path):
        return json.dumps({"error": f"File not found at {file_path}"}, indent=4)

    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            engine = DRCAdvisor()
            engine.load_content(f.read())
            results = engine.analyze(False)

            # Process findings to update summary counts
            for r in results:
                for fnd in r.get('findings', []):
                    crit = fnd.get('crit', 'NOTICE').upper()
                    if crit in theme:
                        theme[crit]['count'] += 1
                    elif 'NOTICE' in theme:
                        theme['NOTICE']['count'] += 1

            # Prepare the final data structure
            output_data = {
                "report_metadata": {
                    "source_file": os.path.basename(file_path),
                    "full_path": os.path.abspath(file_path),
                    "generated_at": datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                },
                "analysis_results": results,
                "summary": {
                    conf['label']: conf['count'] for k, conf in theme.items() if k != "TITLE"
                }
            }

            return json.dumps(output_data, indent=4)

    except Exception as e:
        return json.dumps({"error": f"An error occurred: {str(e)}"}, indent=4)

if __name__ == "__main__":
    # Execute the renamed function and print the JSON result
    print(analise_yaml())
