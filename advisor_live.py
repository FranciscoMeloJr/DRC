import subprocess, sys, os, datetime
from advisor_engine import InfinispanDRCAdvisor

def run_live_audit():
    try:
        print("\033[94m[i] Fetching Infinispan clusters via 'oc get -A'...\033[0m")
        cmd = ["oc", "get", "infinispan", "-A", "-o", "yaml"]
        raw_yaml = subprocess.run(cmd, capture_output=True, text=True, check=True).stdout
    except:
        print("\033[91m[!] Failed to connect to OpenShift. Run 'oc login' first.\033[0m")
        sys.exit(1)

    engine = InfinispanDRCAdvisor()
    engine.load_content(raw_yaml)
    results = engine.analyze()

    C = {'E': '\033[0m', 'B': '\033[94m', 'P': '\033[95m', 'BOLD': '\033[1m'}
    summary = {"CRITICAL": 0, "IMPORTANT": 0, "WARNING": 0, "NOTICE": 0}

    for r in results:
        print("=" * 65)
        print(f"RESOURCE: {C['P']}{r['namespace']}{C['E']} / {C['B']}{r['name']}{C['E']}")
        print(f"  Operand: {r['operand']}  QoS: {r['qos']}  Heap: {r['heap']}\n")

        for fnd in r['findings']:
            crit = fnd['crit'].upper()
            if crit in summary: summary[crit] += 1
            color = "91" if crit == "CRITICAL" else "93" if crit == "IMPORTANT" else "97"
            print(f"  \033[{color}m[!] [{crit}] {fnd['ref']}{C['E']}")
        print("-" * 65)

    now = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    print(f"\n{C['BOLD']}FINAL CLUSTER SUMMARY - {now}{C['E']}")
    for k, v in summary.items():
        print(f"  {k:<15}: {v}")

if __name__ == "__main__":
    run_live_audit()