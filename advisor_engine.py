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

    def analyze(self):
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
            cpu_l = cont.get('cpu') or lim.get('cpu')
            mem_l = cont.get('memory') or lim.get('memory')
            cpu_r = req.get('cpu') or cpu_l
            mem_r = req.get('memory') or mem_l

            # Cgroups v2 / Version Logic
            ver = str(spec.get('version', '0'))
            is_old_ver = ver < "8.4.5"
            heap_ratio = 0.25 if is_old_ver else 0.50

            # QoS Determination (Validated Logic)
            qos_id = None
            if not cpu_l or not mem_l:
                qos, qos_id = "BestEffort (Host Bound)", "qos_kcs"
                heap_display = f"{int(heap_ratio*100)}% of Host RAM"
            elif cpu_l == cpu_r and mem_l == mem_r:
                qos = "Guaranteed"
                heap_display = f"{self.to_gb(mem_l) * heap_ratio:.2f}Gi"
            else:
                qos, qos_id = "Burstable", "qos_risk"
                heap_display = f"{self.to_gb(mem_l) * heap_ratio:.2f}Gi"

            # Run the Logical Registry
            raw_ids = rules.check_full_logic(spec, meta, cont, self.to_gb)


            if qos_id and qos_id not in raw_ids:
                raw_ids.append(qos_id)

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