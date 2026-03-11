import yaml
import re
import sys
import csv
import os
import argparse
class InfinispanDRCAdvisor:
    def setup(self, yaml_content):
        self.data = yaml.safe_load(yaml_content)
        self.reports = []
        self.kcs_map = {}
        csv_path = os.path.join("kcs", "kcs_database.csv")
        if os.path.exists(csv_path):
            try:
                with open(csv_path, mode='r') as f:
                    reader = csv.DictReader(f)
                    for row in reader:
                        self.kcs_map[row['id']] = row['reference']
            except Exception: pass
    def to_gb(self, size_str):
        if not size_str: return 0
        match = re.match(r"(\d+)([a-zA-Z]+)", str(size_str))
        if not match: return 0
        val, unit = match.groups()
        val = float(val)
        if unit.lower() == "gi": return val
        if unit.lower() == "mi": return val / 1024
        return 0
    def to_cores(self, cpu_str):
        if not cpu_str: return 0
        if str(cpu_str).endswith('m'): return float(cpu_str[:-1]) / 1000
        return float(cpu_str)
    def _get_qos(self, container):
        cpu_lim = container.get('cpu')
        mem_lim = container.get('memory')
        if not cpu_lim and not mem_lim: return "BestEffort (HOST LIMITS USED)"
        return "Burstable/Guaranteed"
    def _analyze_infinispan(self, spec, meta, labels, heap_gb):
        findings = []
        container = spec.get('container', {})
        svc_type = spec.get('service', {}).get('type', 'Unknown')
        upgrades = spec.get('upgrades', {})
        upg_type = upgrades.get('type', 'Rolling')
        jvm_opts = spec.get('extraJvmOpts', "")
        mem_raw = container.get('memory')
        cpu_raw = container.get('cpu')
        if not mem_raw or not cpu_raw:
            findings.append("CRITICAL: No container limits defined. Pod will use HOST resources, risking node instability.")
        ephemeral = container.get('ephemeral-storage')
        if not ephemeral:
            findings.append("RESOURCE RISK: No ephemeral-storage limit defined.")
        affinity = spec.get('scheduling', {}).get('affinity', {})
        if "podAntiAffinity" not in str(affinity):
            findings.append("HA RISK: No podAntiAffinity detected. Pods may colocate.")
        if "livenessProbe" not in str(container) or "readinessProbe" not in str(container):
            findings.append("STABILITY: Custom probes missing.")
        if "DEBUG" in str(spec.get('logging', {})):
            findings.append("PERFORMANCE: Debug logging detected.")
        if svc_type == 'DataGrid' and "storage" not in str(spec.get('service', {})):
            findings.append("DATA RISK: Persistence missing for DataGrid.")
        if svc_type == 'Cache': findings.append(self.kcs_map.get("cache_type", "Ref missing"))
        if spec.get('autoscale'): findings.append("CRITICAL: Autoscale enabled.")
        if heap_gb > 3.0 and "+UseG1GC" not in jvm_opts: findings.append(self.kcs_map.get("g1gc_recommended", "Ref missing"))
        if "-Xmx" in jvm_opts: findings.append(self.kcs_map.get("xmx_detected", "Ref missing"))
        if upg_type != 'Shutdown': findings.append(f"NOTICE: Upgrade type '{upg_type}' risk.")
        if not spec.get('configListener'): findings.append(self.kcs_map.get("bidirectional_disabled", "Ref missing"))
        return findings
    def _analyze_cache(self, spec):
        findings = []
        template = spec.get('template', '')
        if 'memory' not in template.lower() and 'size' not in template.lower():
            findings.append(self.kcs_map.get("eviction_missing", "Ref missing"))
        return findings
    def analyze(self):
        items = [self.data] if isinstance(self.data, dict) and self.data.get('kind') in ['Infinispan', 'Cache'] else self.data.get('items', [])
        for item in items:
            kind = item.get('kind')
            meta = item.get('metadata', {})
            spec = item.get('spec', {})
            container = spec.get('container', {})
            mem_raw = container.get('memory')
            mem_gb = self.to_gb(mem_raw)
            qos = self._get_qos(container)
            findings = []
            if kind == 'Infinispan':
                findings = self._analyze_infinispan(spec, meta, meta.get('labels', {}), mem_gb * 0.5)
                if qos.startswith("BestEffort"):
                    findings.append(f"WARNING: {self.kcs_map.get('qos_kcs', 'QoS Risk')} (BestEffort)")
            elif kind == 'Cache':
                findings = self._analyze_cache(spec)
            self.reports.append({
                "name": meta.get('name', 'Unknown'),
                "kind": kind,
                "status": {
                    "operator": meta.get('labels', {}).get('operator.infinispan.org/version', 'N/A'),
                    "operand": spec.get('version', 'N/A'),
                    "replicas": spec.get('replicas', 'N/A'),
                    "exposed": "Yes" if spec.get('expose') else "No",
                    "encryption": "Enabled" if spec.get('security', {}).get('endpointEncryption') else "Disabled",
                    "qos": qos,
                    "heap": f"{mem_gb * 0.5:.2f}Gi" if mem_raw else "HOST RAM",
                    "off_heap": f"{mem_gb * 0.5:.2f}Gi" if mem_raw else "HOST RAM"
                },
                "findings": findings
            })
    def print_report(self, out_file=None):
        res = ["="*65, "INFINISPAN DRC RELIABILITY REPORT", "="*65]
        for r in self.reports:
            res.append(f"RESOURCE: {r['name']} ({r['kind']})")
            res.append(f"  Versions:")
            res.append(f"    Operator:   {r['status']['operator']}")
            res.append(f"    Operand:    {r['status']['operand']}")
            res.append(f"  Replicas:     {r['status']['replicas']}")
            res.append(f"  Exposed:      {r['status']['exposed']}")
            res.append(f"  Encryption:   {r['status']['encryption']} (KCS 7017543)")
            res.append(f"  QoS Class:    {r['status']['qos']} (KCS 6972165)")
            res.append(f"  Target Heap:      {r['status']['heap']}")
            res.append(f"  Target Off-Heap:  {r['status']['off_heap']}")
            if not r['findings']: res.append("  [+] Optimal Configuration")
            for f in r['findings']: res.append(f"  [!] {f}")
            res.append("-"*65)
        txt = "\n".join(res)
        print(txt)
        if out_file:
            with open(out_file, "w") as f: f.write(txt)
def print_help():
    print("\n" + "#" * 60)
    print("INFINISPAN DRC ADVISOR - USAGE GUIDE")
    print("#" * 60)
    print("Usage: python advisor.py <input.yaml> [-o report.txt]")
    print("#" * 60 + "\n")
    
if __name__ == "__main__":
    parser = argparse.ArgumentParser(add_help=False)
    parser.add_argument('file', nargs='?')
    parser.add_argument('-o', '--output')
    args = parser.parse_args()
    if not args.file:
        print_help()
        sys.exit(0)
    try:
        with open(args.file, 'r') as f:
            adv = InfinispanDRCAdvisor()
            adv.setup(f.read())
            adv.analyze()
            adv.print_report(args.output)
    except FileNotFoundError:
        print(f"\nError: File '{args.file}' not found.")
        print_help()
        sys.exit(1)