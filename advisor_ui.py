import os, sys, datetime, csv
from advisor_engine import InfinispanDRCAdvisor

def run_ui():
    C = {'E': '\033[0m', 'B': '\033[94m', 'P': '\033[95m', 'BOLD': '\033[1m'}
    theme = {}


    # Load Severity Configuration from kcs/
    conf_path = os.path.join("kcs", "severity_config.csv")
    if os.path.exists(conf_path):
        with open(conf_path, mode='r', encoding='utf-8-sig') as f:
            reader = csv.DictReader(f)
            reader.fieldnames = [n.strip() for n in reader.fieldnames]
            for row in reader:
                theme[row['criticality'].strip().upper()] = {
                    'color': row['color'].strip(),
                    'label': row['label'].strip(),
                    'count': 0
                }

    path = sys.argv[1] if len(sys.argv) > 1 else input("YAML Path: ")
    with open(path) as f:
        engine = InfinispanDRCAdvisor()
        engine.load_content(f.read())
        results = engine.analyze()

        for r in results:
            print("=" * 65)
            print(f"RESOURCE: {C['B']}{r['name']}{C['E']} (Infinispan)")
            print(f"  Versions:")
            print(f"    Operator:   {r['operator']}")
            print(f"    Operand:    {r['operand']}")
            print(f"  Replicas:     {r['replicas']}")
            print(f"  Exposed:      {r['exposed']}")
            print(f"  Encryption:   {r['encryption']}")
            print(f"  QoS Class:    {r['qos']}")
            print(f"  Cross-Site:   {r['xsite']}")
            print(f"  Target Heap:  {r['heap']}  Off-Heap: {r['off_heap']}\n")

            for fnd in r['findings']:
                crit = fnd.get('crit', 'INFO').upper()
                msg = fnd.get('ref', '')

                if crit in theme:
                    theme[crit]['count'] += 1


                color = theme.get(crit, {}).get('color', '97')
                print(f"  \033[{color}m[!] [{crit}] {msg}{C['E']}")
            print("-" * 65)

        now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        print(f"\n{C['BOLD']}{C['P']}FINAL SUMMARY - {now}{C['E']}")
        for k in theme:
            conf = theme[k]
            print(f"{C['P']}  {conf['label'] + ':':<22} \033[{conf['color']}m{conf['count']}{C['E']}")
        print(f"{C['P']}" + "=" * 65 + f"{C['E']}")

if __name__ == "__main__":
    run_ui()