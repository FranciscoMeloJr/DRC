import yaml, re, csv, os
import advisor_rules as rules

class InfinispanDRCAdvisor:
    def __init__(self):
        self.data = None
        self.kcs_db = {}
        self._load_kcs()

    def _load_kcs(self, legacy=False):
        if not legacy:
            """v2.2: Streamlined loader. Merges legacy JSON and Modular YAML into kcs_db."""
            self.kcs_db = {}

            # 1. Load Legacy JSON (Keep it for backward compatibility)
            legacy_path = 'kcs/kcs_db.json'
            if os.path.exists(legacy_path):
                with open(legacy_path, 'r') as f:
                    self.kcs_db = json.load(f)

            # 2. Append Modular YAML
            modular_path = 'kcs/infinispan-spec-rules.yaml'
            if os.path.exists(modular_path):
                with open(modular_path, 'r') as f:
                    registry = yaml.safe_load(f)
                
                # Flatten the tree directly into kcs_db
                self._flatten_to_db(registry)
        else:
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

    def _flatten_to_db(self, node, path_str=""):
        """v2.2 Clean Logic: Flattens YAML into kcs_db using the natural path as the ID."""
        if isinstance(node, dict):
            if 'condition' in node:
                # The ID is now just the path (e.g., 'infinispan.spec.replicas.single_node_risk')
                rule_id = path_str.strip('.')
                self.kcs_db[rule_id] = {
                    "criticality": node.get('criticality', 'NOTICE'),
                    "reference": node.get('reference', ''),
                    "fix": node.get('fix', 'N/A'),
                    "kcs": node.get('kcs', 'N/A')
                }
            else:
                for k, v in node.items():
                    # Recursively build the path string
                    self._flatten_to_db(v, f"{path_str}{k}.")

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
                container = spec.get('container', {})
                status = item.get('status', {})

                # 1. Get standard resource maps
                mem_map = rules.split_res(container.get('memory'))

                # 2. Run Modular Rules & Get Metadata
                raw_findings, metadata = rules.check_full_logic_caller(
                    spec, meta, status, container, self.to_gb, False, debug=debug
                )

                # 3. Handle Version & Heap Ratio
                ver = str(spec.get('version', '0'))
                is_old_ver = ver < "8.4.5"
                heap_ratio = 0.25 if is_old_ver else 0.50

                # 4. Calculate Heap Display
                limit_mem = mem_map.get('limits', 0)
                if limit_mem != "undefined" and limit_mem != 0:
                    heap_val = self.to_gb(limit_mem) * heap_ratio
                    heap_display = f"{heap_val:.2f}Gi"
                else:
                    heap_display = f"{int(heap_ratio*100)}% of Host RAM"

                # 5. Build Final Report Entry
                results.append({
                    "name": meta.get('name', 'Unknown'),
                    "namespace": meta.get('namespace', 'default'),
                    "operator": meta.get('labels', {}).get('operator.infinispan.org/version', 'N/A'),
                    "operand": ver,
                    "replicas": spec.get('replicas', 0),
                    "exposed": "Yes" if spec.get('expose') else "No",
                    "encryption": spec.get('security', {}).get('endpointEncryption', {}).get('type', 'Disabled'),
                    "qos": metadata.get("qos_class", "Burstable"),
                    "heap": f"{heap_display} (cgv2 risk)" if is_old_ver else heap_display,
                    "findings": [
                        f if isinstance(f, dict) else self.kcs_db.get(f, {'crit': 'NOTICE', 'ref': f}) 
                        for f in raw_findings
                    ],
                })
            return results