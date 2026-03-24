import os
import yaml
import requests
import datetime

# 🧠 Live Cache & Audit Metadata
_rule_cache = {}
_audit_log = {
    "last_sync": "Never",
    "source": "Disk (Initialization)",
    "status": "Ready",
    "online_enabled": os.getenv("DRC_ONLINE_ENABLED", "false").lower() == "true"
}

GITHUB_RAW_BASE = "https://raw.githubusercontent.com/FranciscoMeloJr/DRC/drc-advisor-v2.6/rules/"
ONLINE_ENABLED = _audit_log["online_enabled"]

def get_audit_data():
    """Returns the current registry status for the UI."""
    return _audit_log

def get_rules(filename, force_refresh=False):
    global _rule_cache, _audit_log
    
    # 1. Memory Cache check
    if filename in _rule_cache and not force_refresh:
        return _rule_cache[filename]

    # 2. Try Online ONLY if explicitly enabled
    if ONLINE_ENABLED:
        github_url = f"{GITHUB_RAW_BASE}{filename}"
        try:
            print(f"🌐 [OPT-IN] Attempting GitHub Sync for {filename}...")
            res = requests.get(github_url, timeout=2)
            if res.status_code == 200:
                rules = yaml.safe_load(res.text)
                if rules:
                    _rule_cache[filename] = rules
                    _save_locally(filename, res.text)
                    
                    # 📝 Update Audit Log
                    _audit_log["last_sync"] = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    _audit_log["source"] = "GitHub (v2.6 Ninetails)"
                    _audit_log["status"] = "Success"
                    return rules
        except Exception as e:
            _audit_log["status"] = f"Sync Failed: {str(e)}"
            print(f"⚠️ [ONLINE] Sync failed: {e}")

    # 3. Default / Fallback: Load from local
    print(f"🏠 [LOCAL] Loading {filename} from disk.")
    rules = _load_from_disk(filename)
    _rule_cache[filename] = rules
    
    if not ONLINE_ENABLED:
        _audit_log["last_sync"] = "N/A (Offline Mode)"
        _audit_log["source"] = "Local Disk"
        _audit_log["status"] = "Active"
        
    return rules

def _load_from_disk(filename):
    current_dir = os.path.dirname(os.path.abspath(__file__))
    local_path = os.path.join(current_dir, filename)
    try:
        if os.path.exists(local_path):
            with open(local_path, 'r') as f:
                return yaml.safe_load(f) or {}
    except Exception:
        pass
    return {}

def _save_locally(filename, content):
    """Saves remote updates to local disk for persistence."""
    try:
        current_dir = os.path.dirname(os.path.abspath(__file__))
        local_path = os.path.join(current_dir, filename)
        with open(local_path, 'w') as f:
            f.write(content)
    except Exception:
        pass # Handle read-only filesystems