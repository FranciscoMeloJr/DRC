import re
import yaml
import os

class JVMAdvisor:
    def __init__(self, raw_text):
        self.raw_text = raw_text
        self.rules = self._load_rules()

    def _load_rules(self):
        base_path = os.path.dirname(os.path.abspath(__file__))
        rule_path = os.path.join(base_path, '..', 'rules', 'jvm-rules.yaml')
        try:
            if os.path.exists(rule_path):
                with open(rule_path, 'r') as f:
                    return yaml.safe_load(f)
        except Exception as e:
            print(f"⚠️ Error loading JVM rules: {e}")
        return {}

    def analyze(self):
        # 1. Fact Extraction
        limit_raw = self._find(r"memory_limit:\s*(\d+\w*)")
        heap_max_raw = self._find(r"Heap Max Capacity:\s*(\d+\w*)")
        quota_raw = self._find(r"cpu_quota:\s*(\d+)")
        period_raw = self._find(r"cpu_period:\s*(\d+)")
        metaspace_used_raw = self._find(r"Metaspace\s+used\s+(\d+K)")
        code_cache_used_raw = self._find(r"CodeHeap.*used=(\d+K)")

        # 2. Context Calculation
        limit_mb = self._parse_to_mb(limit_raw)
        heap_mb = self._parse_to_mb(heap_max_raw)
        pcnt = round((heap_mb / limit_mb) * 100) if limit_mb > 0 else 0
        
        cores = 0
        if quota_raw != "N/A":
            period = int(period_raw) if period_raw != "N/A" else 100000
            cores = int(quota_raw) // period

        context = {
            "pcnt": pcnt,
            "cg_type": self._find(r"container_type:\s*(\w+)"),
            "jre": self._find(r"JRE version:\s*(.*?)\s"),
            "cores": cores,
            "workers": int(self._find(r"Parallel Workers:\s*(\d+)").replace("N/A", "0")),
            "metaspace_used": self._parse_to_mb(metaspace_used_raw)
        }

        # 3. Build the Tree
        tree = {
            "Summary": {
                "JRE_version": context["jre"],
                "Java_VM": self._find(r"Java VM:\s*(.*?)\n"),
            },
            "container_cgroup_information": {
                "container_type": context["cg_type"],
                "cpu_cores": cores,
                "memory_limit": limit_raw,
                "Note": "",
                "Crit": "NOTICE"
            },
            "Metaspace_and_Code_Cache": {
                "Metaspace_Used": metaspace_used_raw,
                "Code_Cache_Used": code_cache_used_raw,
                "Note": "",
                "Crit": "NOTICE"
            },
            "GC_Precious_Log": {
                "Heap_Max_Capacity": heap_max_raw,
                "Parallel_Workers": context["workers"]
            }
        }

        # 4. Apply Rules
        for group_name, rules in self.rules.items():
            if not isinstance(rules, dict): continue
            for rule_id, body in rules.items():
                try:
                    if eval(body['condition'], {"__builtins__": None}, context):
                        crit = body.get('criticality', 'NOTICE').upper()
                        msg = body['message'].format(**context)
                        
                        if any(x in group_name for x in ["memory", "cpu", "cgroup"]):
                            branch = tree["container_cgroup_information"]
                            branch["Note"] = f"{branch['Note']} | {msg}".strip(" | ")
                            branch["Crit"] = crit
                        elif "metaspace" in group_name:
                            tree["Metaspace_and_Code_Cache"]["Note"] = msg
                            tree["Metaspace_and_Code_Cache"]["Crit"] = crit
                except:
                    continue

        return tree

    def _find(self, pattern, text=None):
        match = re.search(pattern, text or self.raw_text, re.MULTILINE | re.IGNORECASE)
        return match.group(1).strip() if match else "N/A"

    def _parse_to_mb(self, val_str):
        if not val_str or "N/A" in val_str: return 0
        try:
            num = float(re.findall(r"(\d+(?:\.\d+)?)", val_str)[0])
            if "G" in val_str.upper(): return num * 1024
            if "K" in val_str.upper(): return num / 1024
            return num
        except: return 0