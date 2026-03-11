import yaml, re, csv, os
import advisor_rules as rules

class InfinispanDRCAdvisor:
    def __init__(self): # <--- Standardized double underscores
        self.data = None
        self.kcs_db = {}
        self._load_kcs()

    def _load_kcs(self):
        """Loads the KCS database into a lookup dictionary."""
        csv_path = os.path.join("kcs", "kcs_database.csv")
        if os.path.exists(csv_path):
            with open(csv_path, mode='r', encoding='utf-8-sig') as f:
                reader = csv.DictReader(f)
                reader.fieldnames = [n.strip() for n in reader.fieldnames]
                for row in reader:
                    self.kcs_db[row['id'].strip()] = {
                        'crit': row['criticality'].strip(),
                        'ref': row['reference'].strip()
                    }

    def load_content(self, yaml_content):
        """Safely parses the input YAML."""
        self.data = yaml.safe_load(yaml_content)

    def to_gb(self, size_str):
        """Converts K8s units (Mi, Gi) to float GB. Returns None if empty."""
        if not size_str: return None
        match = re.match(r"(\d+)([a-zA-Z]+)", str(size_str))
        if not match: return None
        v, u = float(match.group(1)), match.group(2).lower()
        return v if u == "gi" else v / 1024

    def analyze(self):
        """Processes all resources with full metadata extraction and strict QoS logic."""
        results = []
        items = self.data.get('items', [self.data]) if self.data else []


        for item in items:
            if not isinstance(item, dict) or 'spec' not in item: continue


            spec = item.get('spec', {})
            meta = item.get('metadata', {})
            cont = spec.get('container', {})
            res = cont.get('resources', {})
            limits = res.get('limits', {})
            reqs = res.get('requests', {})

            # 1. Strict Resource Extraction for QoS
            # Checks both top-level (operator style) and nested (k8s style)
            cpu_lim = cont.get('cpu') or limits.get('cpu')
            mem_lim = cont.get('memory') or limits.get('memory')


            # K8s defaults requests to limits if limits are set but requests are not
            cpu_req = reqs.get('cpu') or cont.get('cpu_request') or (cpu_lim if cpu_lim else None)
            mem_req = reqs.get('memory') or cont.get('memory_request') or (mem_lim if mem_lim else None)

            # 2. QoS and Heap Logic
            # Guaranteed: Everything defined and Req == Lim
            # BestEffort: Limits are missing
            # Burstable: Everything else

            qos_id = None
            if not cpu_lim or not mem_lim:
                qos_display = "BestEffort (Host Bound)"
                heap_display = "50% of Host RAM"
                off_heap_display = "50% of Host RAM"
                qos_id = "qos_kcs"
            elif cpu_lim == cpu_req and mem_lim == mem_req:
                qos_display = "Guaranteed"
                mem_gb = self.to_gb(mem_lim)
                heap_display = f"{mem_gb * 0.5:.2f}Gi"
                off_heap_display = f"{mem_gb * 0.5:.2f}Gi"
            else:
                qos_display = "Burstable"
                mem_gb = self.to_gb(mem_lim)
                heap_display = f"{mem_gb * 0.5:.2f}Gi"
                off_heap_display = f"{mem_gb * 0.5:.2f}Gi"
                qos_id = "qos_risk"

            # 3. Rule Execution
            raw_ids = []
            # Check for unknown fields in the spec
            unk = rules.check_unknown_fields(spec)
            if unk: raw_ids.append(unk)


            # Run the rule suite (Monitoring, Ephemeral, HA, etc.)
            raw_ids.extend(rules.check_full_logic(spec, meta, cont, self.to_gb))


            # Ensure the specific QoS risk is in findings
            if qos_id and qos_id not in raw_ids:
                raw_ids.append(qos_id)

            # 4. Metadata and Dependencies
            service_block = spec.get('service', {})
            sites_block = service_block.get('sites', {})
            locations = sites_block.get('locations', [])
            xsite_names = [loc.get('name') for loc in locations if loc.get('name')]

            # 5. Build Result Dictionary
            findings_objects = [self.kcs_db.get(fid, {'crit': 'INFO', 'ref': fid}) for fid in raw_ids]

            results.append({
                "name": meta.get('name', 'Unknown'),
                "operator": meta.get('labels', {}).get('operator.infinispan.org/version', 'N/A'),
                "operand": spec.get('version', 'N/A'),
                "replicas": spec.get('replicas', 0),
                "exposed": "Yes" if spec.get('expose') else "No",
                "encryption": spec.get('security', {}).get('endpointEncryption', {}).get('type', 'Disabled'),
                "qos": qos_display,
                "heap": heap_display,
                "off_heap": off_heap_display,
                "xsite": ", ".join(xsite_names) if xsite_names else "Disabled",
                "dependencies": spec.get('dependencies', []),
                "findings": findings_objects
            })


        return results