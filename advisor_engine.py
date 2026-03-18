import yaml, re, csv, os, json
import advisor_rules as rules

class DRCAdvisor:
    def __init__(self):
        self.data = None
        self.eval_undefined = True
        self.kcs_db = {}
        self._load_kcs()
        self.type = "Unknown"  # v2.3: Identity attribute

    def _load_kcs(self, legacy=False):
        if not legacy:
            """v2.2: Streamlined loader. Merges legacy JSON and Modular YAML into kcs_db."""
            self.kcs_db = {}

            # 1. Load Legacy JSON
            legacy_path = 'kcs/kcs_db.json'
            if os.path.exists(legacy_path):
                with open(legacy_path, 'r') as f:
                    self.kcs_db = json.load(f)

            # 2. Append Modular YAML
            # We load both to ensure the DB is ready for any kind
            for rule_file in ['rules/infinispan-spec-rules.yaml', 'rules/cache-spec-rules.yaml']:
                if os.path.exists(rule_file):
                    with open(rule_file, 'r') as f:
                        registry = yaml.safe_load(f)
                        if registry:
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
                rule_id = path_str.strip('.')
                self.kcs_db[rule_id] = {
                    "criticality": node.get('criticality', 'NOTICE'),
                    "reference": node.get('reference', ''),
                    "fix": node.get('fix', 'N/A'),
                    "kcs": node.get('kcs', 'N/A')
                }
            else:
                for k, v in node.items():
                    self._flatten_to_db(v, f"{path_str}{k}.")

    def load_content(self, yaml_content, eval_header=True):
        self.data = yaml.safe_load(yaml_content)
        self.eval_undefined = (str(eval_header).lower() == 'true')

        # Detect Kind for Class Identity
        if isinstance(self.data, dict):
            if 'items' in self.data and len(self.data['items']) > 0:
                self.type = self.data['items'][0].get('kind', 'Infinispan')
            else:
                self.type = self.data.get('kind', 'Infinispan')

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
        """v2.3 Agnostic Router"""
        if isinstance(self.data, dict) and 'items' in self.data:
            items = self.data['items']
        else:
            items = [self.data] if self.data else []

        all_results = []
        for item in items:
            kind = item.get('kind', 'Unknown')
            if kind == 'Infinispan':
                all_results.extend(self.analyze_infinispan(debug))
            elif kind == 'Cache':
                all_results.extend(self.analyze_cache(item, debug))
            else:
                print(f"Skipping unknown kind: {kind}")
        return all_results

    def analyze_infinispan(self, debug=True):
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

            mem_map = rules.split_res(container.get('memory'))
            raw_findings, metadata = rules.check_full_logic_caller(
                spec, meta, status, container, self.to_gb, False, debug, self.eval_undefined)

            ver = str(spec.get('version', '0'))
            is_old_ver = ver < "8.4.5"
            heap_ratio = 0.25 if is_old_ver else 0.50

            limit_mem = mem_map.get('limits', 0)
            if limit_mem != "undefined" and limit_mem != 0:
                heap_val = self.to_gb(limit_mem) * heap_ratio
                heap_display = f"{heap_val:.2f}Gi"
            else:
                heap_display = f"{int(heap_ratio*100)}% of Host RAM"

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
                "eval_header": self.eval_undefined,
                "findings": [
                    f if isinstance(f, dict) else self.kcs_db.get(f, {'crit': 'NOTICE', 'ref': f}) 
                    for f in raw_findings
                ],
            })
        return results

    def analyze_cache(self, item, debug=True):
        results = []
        spec = item.get('spec', {})
        meta = item.get('metadata', {})
        status = item.get('status', {})

        raw_findings, metadata = rules.check_full_logic_caller(
            item, "cache", self.to_gb, False, debug, self.eval_undefined)

        conditions = status.get('conditions', [])
        ready_status = next((c.get('status') for c in conditions if c.get('type') == 'Ready'), "Unknown")

        results.append({
            "resource_type": "Cache",
            "name": meta.get('name', 'Unknown'),
            "namespace": meta.get('namespace', 'default'),
            "cluster": spec.get('clusterName', 'N/A'),
            "template_name": spec.get('templateName', 'Inline/Custom'),
            "strategy": spec.get('updates', {}).get('strategy', 'retain'),
            "ready": ready_status,
            "findings": [
                f if isinstance(f, dict) else self.kcs_db.get(f, {'crit': 'NOTICE', 'ref': f}) 
                for f in raw_findings
            ]
        })
        return results