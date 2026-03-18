import os, sys, datetime, csv
from advisor_engine import DRCAdvisor

def run_ui():
    C = {'E': '\033[0m', 'B': '\033[94m', 'P': '\033[95m', 'BOLD': '\033[1m'}
    theme = {}


    # Load Severity Configuration
    conf_path = os.path.join("kcs", "severity_config.csv")
    if os.path.exists(conf_path):
        with open(conf_path, mode='r', encoding='utf-8-sig') as f:
            reader = csv.DictReader(f)
            reader.fieldnames = [n.strip() for n in reader.fieldnames]
            for row in reader:
                # Ensure keys are UPPERCASE for consistent matching
                theme[row['criticality'].strip().upper()] = {
                    'color': row['color'].strip(),
                    'label': row['label'].strip(),
                    'count': 0
                }
    # Determine the title color from the CSV, fallback to Blue (94)
    title_color = theme.get('TITLE', {}).get('color', '94')

    path = sys.argv[1] if len(sys.argv) > 1 else input("YAML Path: ")
    with open(path) as f:
        engine = DRCAdvisor()
        engine.load_content(f.read())
        results = engine.analyze()

        print(f"\033[{title_color}m" + "=" * 65)
        print(" DRC ADVISOR REPORT")
        print(f" Generated: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"\033[{title_color}m" + "=" * 65)

        for r in results:
            print("=" * 65)
            # Display as Namespace / Name for clarity
            resource_path = f"{C['P']}{r['namespace']}{C['E']} / {C['B']}{r['name']}{C['E']}"
            print(f"RESOURCE: {resource_path} (Infinispan)")            
            print(f"  Versions:     Operator: {r['operator']} / Operand: {r['operand']}")
            print(f"  Replicas:     {r['replicas']}  Exposed: {r['exposed']}")
            print(f"  Encryption:   {r['encryption']}")
            print(f"  QoS Class:    {r['qos']}")
            print(f"  Target Heap:  {r['heap']}\n")

            # --- THE FIX: Parsing the dictionary findings ---
            for fnd in r.get('findings', []):
                # Extract the severity and message
                crit = fnd.get('crit', 'NOTICE').upper()
                msg = fnd.get('ref', 'Unknown Finding')

                # Increment counter in the theme dictionary
                if crit in theme:
                    theme[crit]['count'] += 1
                else:
                    # If crit not in theme (like INFO), count as NOTICE or create entry
                    if 'NOTICE' in theme: theme['NOTICE']['count'] += 1


                # Get color or default to white
                color = theme.get(crit, {}).get('color', '97')
                print(f"  \033[{color}m[!] [{crit}] {msg}{C['E']}")


            # Handle dependencies header if it exists
            if r.get('dependencies'):
                print(f"\n  Dependencies: {', '.join(r['dependencies'])}")

            print("-" * 65)

        # Final Summary
        now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        print(f"\n{C['BOLD']}{C['P']}FINAL SUMMARY - {now}{C['E']}")
        for k in theme:
          if k.upper() == "TITLE":
            continue
          conf = theme[k]
          print(f"{C['P']}  {conf['label'] + ':':<22} \033[{conf['color']}m{conf['count']}{C['E']}")
        print("=" * 65)

if __name__ == "__main__":
    run_ui()