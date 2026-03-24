import re
import yaml
import os
# We use 'rules.registry' because 'drc' is the root in sys.path
from rules import registry

class JVMAdvisor:
    def __init__(self, raw_text):
        self.raw_text = raw_text
        # Line 12 Logic: Use the Registry to get live rules
        self.rules = registry.get_rules("jvm-rules.yaml")

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
        # Template
        template_match = re.search(r"^(\d+):.*?# JRE version:.*?\n# Java VM:.*?\n", self.raw_text, re.DOTALL | re.MULTILINE)
        template_full = template_match.group(0) if template_match else ""

        # 1. Fact Extraction
        limit_raw = self._find(r"memory_limit_in_bytes:\s*(\d+\s*k?)")
        limit_mb = self._parse_to_mb(limit_raw)
        
        # Format for display: 3145728 k -> 3072 MB -> 3.0 GB
        limit_display = f"{round(limit_mb / 1024, 1)} GB" if limit_mb > 0 else "N/A"

        heap_max_raw = self._find(r"Heap Max Capacity:\s*(\d+\w*)")
        quota_raw = self._find(r"cpu_quota:\s*(\d+)")
        period_raw = self._find(r"cpu_period:\s*(\d+)")
        metaspace_used_raw = self._find(r"Metaspace\s+used\s+(\d+K)")
        code_cache_used_raw = self._find(r"CodeHeap.*used=(\d+K)")

        # 2. Context Calculation
        limit_mb = self._parse_to_mb(limit_raw)
        heap_mb = self._parse_to_mb(heap_max_raw)
        pcnt = round((heap_mb / limit_mb) * 100) if limit_mb > 0 else 0
        
        cpuset_raw = self._find(r"cpu_cpuset_cpus:\s*([\d-]+)") # "0-11"
        active_raw = self._find(r"active_processor_count:\s*(\d+)") # "1"
        
        total_cores = self._parse_cpu_range(cpuset_raw)
        active_cores = int(active_raw) if active_raw.isdigit() else 0

        pid_val = 1
        if template_full != "N/A":
            pid_match = re.search(r"^(\d+):", template_full)
            pid_val = int(pid_match.group(1)) if pid_match else 1

        cores = 1
        if quota_raw != "N/A":
            period = int(period_raw) if period_raw != "N/A" else 100000
            cores = int(quota_raw) // period

        # 1. Targeted Extractions for the new branches
        # ---------------------------------------------------------
        # Metaspace & Code Cache
        meta_used = self._find(r"Metaspace\s+used\s+(\d+\w*)")
        cc_used = self._find(r"Code_Cache\s+used\s+(\d+\w*)")
        max_meta = self._find(r"MaxMetaspaceSize:\s*(.*)")

        # Summary & Process (Memory tracking)
        rss_raw = self._find(r"Resident Set Size:\s*([\d_]+[kKmMgG]?)")
        peak_raw = self._find(r"Resident Set Size:.*?peak:\s*([\d_]+[kKmMgG]?)")
        heap_raw = self._find(r"Heap Max Capacity:\s*(\d+\s*\w*)")
        elapsed = self._find(r"Elapsed Time:\s*(.*)")

        # --- 2. System (THP / Page Size) ---
        # Matches "/sys/.../enabled: [always] madvise never"
        thp_raw = self._find(r"transparent_hugepage/enabled:\s*(.*)")
        # Extracts the value inside brackets, e.g., "always"
        thp_active = self._find(r"\[(\w+)\]", thp_raw) if thp_raw != "N/A" else "N/A"
        
        # Matches "/sys/.../hpage_pmd_size: 2097152"
        hpage_size = self._find(r"hpage_pmd_size:\s*(\d+)")

        # System
        os_info = self._find(r"OS:\s*(.*)")
        os_uptime = self._find(r"OS uptime:\s*(.*)")
        thp_info = self._find(r"Transparent Huge Pages:\s*(.*)")
        page_size = self._find(r"Page Size:\s*(\d+\w*)")

        context = {
            "template": template_full,
            "pid": pid_val,
            "is_g1": "g1 gc" in template_full.lower(),
            "is_redhat": "Red_Hat" in template_full,
            "version": self._find(r"(\d+\.\d+\.\d+)", template_full),
            "arch": "linux-amd64" if "linux-amd64" in template_full.lower() else "other",
            "pcnt": pcnt,
            "cg_type": self._find(r"container_type:\s*(\w+)"),
            "jre": self._find(r"JRE version:\s*(.*?)\s"),
            "cores": cores,
            "limit_mb": limit_mb,
            "limit_gb": round(limit_mb / 1024, 1),
            "workers": int(self._find(r"Parallel Workers:\s*(\d+)").replace("N/A", "0")),
            "metaspace_used": self._parse_to_mb(metaspace_used_raw),
            "rss": rss_raw.replace("_", ""), 
            "rss_peak": peak_raw.replace("_", ""),
            "thp": thp_active, 
            "hpage": hpage_size,
            "page": "4096"
        }

        cg_val = context.get("cg_type", "").lower()
        if "cgroupv1" in cg_val:
            cg_advice = "cgroups v1"
        elif "cgroupv2" in cg_val:
            cg_advice = "cgroups v2"
        else:
            cg_advice = "not detected"

        # 3. Build the Tree
        tree = {
            "Summary": {
                "JRE_version": context["jre"],
                "Java_VM": self._find(r"Java VM:\s*(.*?)\n"),
            },
            "Template": {
                "Full_Header": context["template"],
                "PID": context["pid"],
                "JRE_Build": context["version"],
                "GC_Collector": "G1GC" if context["is_g1"] else "Other",
                "Architecture": context["arch"],
                "Note": "",
                "Crit": "NOTICE"
            },
            "container_cgroup_information": {
                "container_type": context["cg_type"],
                "cpu_cores": cores,
                "memory_limit": f"{context['limit_gb']} GB",
                "Note": "",
                "cpu_cores": f"{active_cores} / {total_cores}",
                "Crit": "NOTICE"
            },
            "Metaspace_and_Code_Cache": {
                "Metaspace_Used": meta_used,
                "Code_Cache_Used": cc_used,
                "MaxMetaspace": max_meta, # e.g. "unlimited"
                "Crit": "NOTICE"
            },
            "GC_Precious_Log": {
                "Heap_Max_Capacity": heap_raw,
                "Parallel_Workers": self._find(r"Parallel Workers:\s*(\d+)")
            },
            "Summary": {
                "RSS": context["rss"],
                "Peak": context["rss_peak"],
                "Elapsed_time": self._find(r"Elapsed Time:\s*(.*)")
            },
            "Process_details": {
                "RSS": context["rss"],
                "Peak": context["rss_peak"],
                "Heap": self._find(r"Heap Max Capacity:\s*(\d+\w*)")
            },
            "System": {
                "OS": self._find(r"OS:\s*(.*)"),
                "Total_time_OS_running": self._find(r"OS uptime:\s*(.*)"),
                "THP": f"{context['thp']} (PMD: {context['hpage']})",
                "Page_size": context["page"]
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
        if not val_str or "N/A" in val_str.upper(): return 0
        try:
            # Clean string: "3145728 k" -> 3145728
            clean_val = re.sub(r"[^0-9.]", "", val_str)
            num = float(clean_val)
            
            # If it's from 'memory_limit_in_bytes' with a 'k', it's KB.
            if "k" in val_str.lower():
                return num / 1024
            # If it's already in bytes (no 'k'), it's bytes.
            if num > 100000000: # Heuristic: if it's a massive number, it's bytes
                return num / 1024 / 1024
            return num
        except:
            return 0

    def _parse_cpu_range(self, cpu_range_str):
        if not cpu_range_str or "N/A" in cpu_range_str: return 0
        try:
            # Handles "0-11" -> [0, 11]
            parts = cpu_range_str.split('-')
            if len(parts) == 2:
                return (int(parts[1]) - int(parts[0])) + 1
            return int(parts[0]) + 1 if parts[0].isdigit() else 0
        except:
            return 0