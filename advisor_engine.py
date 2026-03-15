import yaml, re, csv, os
import advisor_rules as rules

class InfinispanDRCAdvisor:
    def __init__(self):
        self.data = None
        self.kcs_db = {}
        self._load_kcs()

    def _load_kcs(self):
        csv_path = os.path.join("kcs", "kcs_database.csv")
        if os.path.exists(csv_path):
            with open(csv_path, mode='r', encoding='utf-8-sig') as f:
                reader = csv.DictReader(f)
                reader.fieldnames = [n.strip() for n in reader.fieldnames]
                for row in reader:
                    if row.get('id'):
                        self.kcs_db[row['id'].strip()] = {
                            'crit': row.get('criticality', 'NOTICE').strip(),
                            'ref': row.get('reference', '').strip()
                        }

    def load_content(self, yaml_content):
        self.data = yaml.safe_load(yaml_content)

    def to_gb(self, size_str):
        if not size_str: return 0.0
        match = re.match(r"(\d+)([a-zA-Z]+)", str(size_str))
        if not match: return 0.0
        v, u = float(match.group(1)), match.group(2).lower()
        if u == "gi": return v
        if u == "mi": return v / 1024
        if u == "ki": return v / (1024 * 1024)
        return v

    def analyze(self, debug=True):
        results = []
        if isinstance(self.data, dict) and 'items' in self.data:
            items = self.data['items']
        else:
            items = [self.data] if self.data else []

        for item in items:
            if not isinstance(item, dict) or 'spec' not in item: continue


            spec = item.get('spec', {})
            meta = item.get('metadata', {})
            cont = spec.get('container', {})
            res = cont.get('resources', {})
            lim = res.get('limits', {})
            req = res.get('requests', {})

            # Extract Resource Values
            # 1. Capture Limits (remains the same)
            cpu_l = cont.get('cpu') or lim.get('cpu')
            mem_l = cont.get('memory') or lim.get('memory')

            # 2. Capture Requests: Default to -1 if missing
            cpu_r = req.get('cpu') if req.get('cpu') is not None else -1
            mem_r = req.get('memory') if req.get('memory') is not None else -1

            # Cgroups v2 / Version Logic
            ver = str(spec.get('version', '0'))
            is_old_ver = ver < "8.4.5"
            heap_ratio = 0.25 if is_old_ver else 0.50

            # QoS Determination (Validated Logic)
            # Default to Best Effort (The "Important" Risk)
            qos, qos_id = "BestEffort", "qos_important"
            heap_display = f"{int(heap_ratio*100)}% of Host RAM"

            if cpu_r or mem_r:
                # It has requests, so it's at least Burstable
                qos, qos_id = "Burstable", "qos_warning"
                # Calculate heap based on the defined memory limit
                mem_val = mem_l if mem_l else 0
                heap_display = f"{self.to_gb(mem_val) * heap_ratio:.2f}Gi"
                
                # Check for promotion to Guaranteed
                if cpu_l and mem_l and cpu_l == cpu_r and mem_l == mem_r:
                    qos, qos_id = "Guaranteed", "qos_notice"

            # Run the Logical Registry
            raw_ids = rules.check_full_logic(spec, meta, cont, self.to_gb)

            if qos_id not in raw_ids:
                raw_ids.append(qos_id)

            if debug:
                print(raw_ids)

            results.append({
                "name": meta.get('name', 'Unknown'),
                "namespace": meta.get('namespace', 'default'),
                "operator": meta.get('labels', {}).get('operator.infinispan.org/version', 'N/A'),
                "operand": ver,
                "replicas": spec.get('replicas', 0),
                "exposed": "Yes" if spec.get('expose') else "No",
                "encryption": spec.get('security', {}).get('endpointEncryption', {}).get('type', 'Disabled'),
                "qos": qos,
                "heap": f"{heap_display} (cgv2 risk)" if is_old_ver else heap_display,
                "findings": [self.kcs_db.get(fid, {'crit': 'NOTICE', 'ref': fid}) for fid in raw_ids],
            })
        return results