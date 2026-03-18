## Comprehensive Logic Registry
import yaml
import os
import json 

# V2.2 / V2.3 Agnostic Implementation

# --- 1. THE NEW CALLER (dispatcher) ---
def split_res(val):
    """Standardizes Infinispan resource strings (limit:request)."""
    if val == "undefined" or val is None:
        return {"limits": "undefined", "requests": "undefined"}
    val_str = str(val).strip()
    if ':' in val_str:
        parts = val_str.split(':')
        return {
            "limits": parts[0] if parts[0] else "undefined",
            "requests": parts[1] if parts[1] else "undefined"
        }
    return {"limits": val_str, "requests": val_str}

def _expand(obj, keys):
    """Safe dictionary expansion for the synthetic tree."""
    if not isinstance(obj, dict): return "undefined"
    return {k: obj.get(k, "undefined") for k in keys}

def _eval_rule(obj, rule, findings, full_context, eval_undefined=True):
    """v2.2: Evaluates a leaf rule with a noise-filter toggle."""
    
    # --- THE GATEKEEPER ---
    if not eval_undefined and obj == 'undefined':
        return
    # ----------------------

    cond = rule.get('condition')
    # Detection of spec root based on context type (Agnostic Support)
    if 'infinispan' in full_context:
        spec_data = full_context.get('infinispan', {}).get('spec', {})
    else:
        spec_data = full_context.get('cache', {}).get('spec', {})
    
    # Clean up the condition string
    cond = str(cond).strip()
    
    # Prepare the evaluation string
    eval_str = cond if "obj" in cond else f"obj {cond}"
    
    try:
        eval_locals = {
            "obj": obj,
            "spec": spec_data,
            "str": str, "float": float, "int": int, "any": any, "len": len
        }
        
        # Evaluate logic safely
        if eval(eval_str, {"__builtins__": None}, eval_locals):
            findings.append({
                "crit": rule.get('criticality', 'NOTICE'),
                "ref": rule.get('reference', ''),
                "fix": rule.get('fix', ''),
                "kcs": rule.get('kcs', '')
            })
    except Exception:
        pass

def _walk_tree(data_node, rule_node, findings, full_context, eval_undefined=True):
    """v2.2: Recursively crawls the tree, carrying the toggle baton."""
    if isinstance(rule_node, dict):
        if 'condition' in rule_node:
            # 1. Forward to the Evaluator
            _eval_rule(data_node, rule_node, findings, full_context, eval_undefined=eval_undefined)
        else:
            for key, next_rule in rule_node.items():
                # Get next data piece
                next_data = data_node.get(key, 'undefined') if isinstance(data_node, dict) else 'undefined'
                
                # 2. CRITICAL: Pass the baton into the NEXT level of recursion
                _walk_tree(next_data, next_rule, findings, full_context, eval_undefined=eval_undefined)

def check_full_logic_tree(context, kind, eval_undefined=True):
    """v2.3: Agnostic tree loader. kind='infinispan' or 'cache'."""
    findings = []
    rules_path = f'rules/{kind}-spec-rules.yaml'
    if not os.path.exists(rules_path): return []
    with open(rules_path, 'r') as f:
        registry = yaml.safe_load(f)
    _walk_tree(context, registry, findings, context, eval_undefined)
    return findings

def check_full_logic_caller(item_or_spec, meta, status, container, to_gb, legacy=False, debug=True, eval_undefined=True):
    # --- 1. Agnostic Kind Detection ---
    is_cache = (item_or_spec.get('kind') == 'Cache') if isinstance(item_or_spec, dict) else False

    # --- BRANCH A: CACHE IMPLEMENTATION (v2.3) ---
    if is_cache:
        spec = item_or_spec.get('spec', {})
        full_context = {
            "cache": {
                "metadata": _expand(meta, ["name", "namespace"]),
                "spec": {
                    "clusterName": spec.get("clusterName", "undefined"),
                    "template": spec.get("template", "undefined"),
                    "templateName": spec.get("templateName", "undefined"),
                    "updates": _expand(spec.get("updates", {}), ["strategy"])
                },
                "status": {
                    "conditions": item_or_spec.get("status", {}).get("conditions", "undefined")
                }
            }
        }
        if debug:
            print("\n--- [DEBUG] CACHE CONTEXT ---\n", json.dumps(full_context, indent=2))
        return check_full_logic_tree(full_context, "cache", eval_undefined), {"qos_class": "N/A"}

    # --- BRANCH B: INFINISPAN IMPLEMENTATION (v2.2 Original) ---
    spec = item_or_spec # In Infinispan mode, first arg is the spec
    cpu_map = split_res(container.get("cpu"))
    mem_map = split_res(container.get("memory"))

    # Extract service container data safely
    svc = spec.get("service", {})
    svc_cont = svc.get("container", {}) if isinstance(svc.get("container"), dict) else {}

    full_context = {
        "infinispan": {
            "metadata": _expand(meta, ["name", "namespace", "labels", "annotations"]),
            "spec": {
                "replicas": spec.get("replicas", "undefined"),
                "version": spec.get("version", "undefined"),
                "container": {
                    "cpu": cpu_map,
                    "memory": mem_map,
                    "extraJvmOpts": container.get("extraJvmOpts", "undefined"),
                    "storage": {
                        "ephemeral": container.get("storage", {}).get("ephemeral", "undefined") 
                        if isinstance(container.get("storage"), dict) else "undefined"
                    },
                },
                "service": {
                    "type": svc.get("type", "undefined"),
                    "container": {
                        "storage": svc_cont.get("storage", "undefined"),
                        "ephemeralStorage": svc_cont.get("ephemeralStorage", "undefined"),
                        "livenessProbe": container.get("livenessProbe", "undefined"),
                        "readinessProbe": svc_cont.get("readinessProbe", "undefined")
                    }
                },
                "configListener": _expand(spec.get("configListener", {}), ["enabled"]),
                "scheduling": _expand(spec.get("scheduling", {}), ["affinity"])
            },
            "status": _expand(status, ["qosClass", "operand", "conditions", "phase"])
        }
    }

    if debug:
        print("\n--- [DEBUG] MODE: %s ---" % ("LEGACY HARDCODED" if legacy else "MODULAR TREE WALKER"))
        if not legacy:
            print("Synthetic Context:")
            print(json.dumps(full_context, indent=2, default=str))
        print("------------------------------------------\n")

    # QoS Priority: Status > Spec
    live_qos = status.get("qosClass")
    if not live_qos or live_qos == "undefined":
        is_guaranteed = (cpu_map['limits'] == cpu_map['requests'] and cpu_map['limits'] != "undefined")
        live_qos = "Guaranteed" if is_guaranteed else "Burstable"

    if not legacy:
        return check_full_logic_tree(full_context, "infinispan", eval_undefined), {"qos_class": live_qos}
    else:
        return [], {"qos_class": live_qos}

# --- 2. LEGACY V2.1 HARDCODED LOGIC (Keep exactly as original) ---
def check_full_logic(spec, meta, container, to_gb, debug=False):
    findings = []
    service_spec = spec.get('service', {})
    jvm_opts = spec.get('extraJvmOpts', "")
    res = container.get('resources', {})
    limits = res.get('limits', {})

    # 1. Replicas & Quorum
    replicas_count = spec.get('replicas', 0)
    if replicas_count > 0 and replicas_count % 2 == 0:
        findings.append("quorum_risk")
    if not spec.get('affinity', {}).get('podAntiAffinity'):
        findings.append("ha_risk")

    # 2. Prometheus Labels
    if meta.get('labels', {}).get('prometheus.io/scrape') != 'true':
        findings.append("monitoring_missing")

    # 3. ConfigListener
    cl = spec.get('configListener', {})
    if not cl or not cl.get('enabled'):
        findings.append("bidirectional_disabled")
    if cl.get('logging', {}).get('level') == 'DEBUG':
        findings.append("cl_debug")

    # 4. JMX
    if spec.get('jmx', {}).get('enabled'):
        findings.append("jmx_enabled")

    # 5. Encryption
    sec = spec.get('security', {}).get('endpointEncryption', {})
    if not sec or sec.get('type') in ['None', 'Disabled']:
        findings.append("encryption_info")

    # 6. Service Type
    if service_spec.get('type') == 'Cache':
        findings.append("cache_type")

    # 7. ConfigMap
    if spec.get('configMapName'):
        findings.append(f"ADVANCED: Custom ConfigMap '{spec.get('configMapName')}' used.")

    # 8. CloudEvents
    if spec.get('cloudEvents'):
        findings.append("cloudevents_deprecated")

    # 9. Scheduling
    if spec.get('scheduling'):
        findings.append("SCHEDULING: Custom scheduling/tolerations detected.")

    # 10. Upgrades
    if spec.get('upgrades', {}).get('type') == 'RollingUpdate':
        findings.append("rolling_upgrade_pressure")

    # 11. Autoscale
    if spec.get('autoscale') and service_spec.get('type') == 'DataGrid':
        findings.append("autoscale_invalid")

    # 12. JVM Opts & G1GC
    if jvm_opts:
        findings.append("jvm_opts")
        if "-Xmx" in jvm_opts or "-Xms" in jvm_opts:
            findings.append("xmx_detected")
        mem_limit = container.get('memory', '0Gi')
        if to_gb(mem_limit) >= 6.0 and "-XX:+UseG1GC" not in jvm_opts:
            findings.append("g1gc_recommended")

    # 13. Production Resource Boundaries
    if not limits.get('cpu') or not limits.get('memory'):
        findings.append("prod_resources_missing")
    cpu_val = limits.get('cpu', '0')
    cores = int(cpu_val[:-1])/1000 if isinstance(cpu_val, str) and cpu_val.endswith('m') else float(cpu_val)
    mem_gb = to_gb(limits.get('memory', '0Gi'))
    if (0 < cores <= 1.0) or (0 < mem_gb < 2.0):
        findings.append("low_resources")

    # 14. Ephemeral Storage & Probes
    if not container.get('ephemeral-storage'):
        findings.append("ephemeral_missing")
    if not container.get('livenessProbe') or not container.get('readinessProbe'):
        findings.append("probes_missing")

    # 15. X-Site & Cgroups v2
    if spec.get('sites'):
        findings.append("xsite_info")
    if str(spec.get('version', '0')) < "8.4.5":
        findings.append("cgv2_risk")

    # 16. FIPS Environment Check & Workaround
    fips_host = meta.get('labels', {}).get('fips-enabled') == 'true'
    fips_spec = spec.get('security', {}).get('fips') == 'true'

    if fips_host or fips_spec:
        if "-Dcom.redhat.fips=false" not in jvm_opts:
            findings.append("fips_requirement")

    # 17. Detecting logging
    logging_conf = spec.get('logging', {})
    log_level = logging_conf.get('level', '').upper()
    if log_level not in ['DEBUG', 'TRACE']:
        findings.append("drc_log")

    # 18. Affinity
    if "affinity" not in spec.get('scheduling', {}):
        findings.append("affinity_weak")
    else:
        affinity_str = str(spec.get('scheduling', {}).get('affinity', ''))
        if "preferredDuringSchedulingIgnoredDuringExecution" in affinity_str:
            findings.append("affinity_soft")
        if "requiredDuringSchedulingIgnoredDuringExecution" in affinity_str:
            findings.append("affinity_hard")

    # 19. QoS mismatch
    resources = spec.get('container', {}).get('resources', {})
    limits_q = resources.get('limits', {})
    requests_q = resources.get('requests', {})
    if limits_q != requests_q or not limits_q:
        findings.append("qos_mismatch")

    if debug:
        print(findings)
    return findings