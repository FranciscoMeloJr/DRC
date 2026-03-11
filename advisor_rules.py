# Comprehensive Logic Registry
def check_unknown_fields(spec):
    known = {
        'replicas', 'version', 'service', 'security', 'expose',
        'configListener', 'container', 'affinity', 'logging',
        'upgrades', 'jmx', 'autoscale', 'scheduling', 'dependencies',
        'configMapName', 'cloudEvents', 'extraJvmOpts', 'sites'
    }
    unknowns = set(spec.keys()) - known
    return f"SPEC UNKNOWN: Fields not recognized: {', '.join(unknowns)}" if unknowns else None

def check_full_logic(spec, meta, container, to_gb):
    findings = []
    service_spec = spec.get('service', {})
    jvm_opts = spec.get('extraJvmOpts', "")

    # Rule 20 & 21: QoS & Resource Validation
    cpu_limit = container.get('cpu')
    mem_limit = container.get('memory')
    requests = container.get('requests', {})

    if not cpu_limit or not mem_limit:
        # If either is missing, it uses host resources (BestEffort)
        findings.append("qos_kcs")
    else:
        # If they exist, check if Requests == Limits for Guaranteed QoS
        req_cpu = requests.get('cpu', cpu_limit)
        req_mem = requests.get('memory', mem_limit)
        if req_cpu != cpu_limit or req_mem != mem_limit:
            findings.append("qos_risk")

    # Rule 22: Operand Version & cgroups v2 (8.4.x)
    operand_v = str(spec.get('version', '0'))
    if not operand_v.startswith('8.4'):
        findings.append("version_old")
    findings = []
    service_spec = spec.get('service', {})
    jvm_opts = spec.get('extraJvmOpts', "")

    # Rule 20: Host Resource Usage Check
    cpu_limit = container.get('cpu')
    mem_limit = container.get('memory')
    if not cpu_limit or not mem_limit:
        findings.append("qos_kcs")

    # Rule 21: Burstable/Guaranteed QoS Check (KCS 6972165)
    # We detect if the user has inconsistent requests vs limits
    if cpu_limit and mem_limit:
        # If a nested 'requests' block exists, check if it matches limits
        # Note: Often in CRs, limits are top-level and requests are nested
        reqs = container.get('requests', {})
        if reqs:
            if reqs.get('cpu') != cpu_limit or reqs.get('memory') != mem_limit:
                findings.append("qos_risk")
    findings = []
    service_spec = spec.get('service', {})
    jvm_opts = spec.get('extraJvmOpts', "")

    # 1. Replicas & Quorum
    try:
        reps = int(spec.get('replicas', 0))
    except (ValueError, TypeError):
        reps = 0

    if reps == 1:
        findings.append("single_node_risk")
    elif reps > 1 and reps % 2 == 0:
        findings.append("quorum_risk")

    # 2. HA / Affinity
    if not spec.get('affinity', {}).get('podAntiAffinity'):
        findings.append("ha_risk")

    # 3. ConfigListener
    cl = spec.get('configListener', {})
    if not cl or not cl.get('enabled'):
        findings.append("bidirectional_disabled")
    elif cl.get('logging', {}).get('level') == 'DEBUG':
        findings.append("cl_debug")

    # 4. Service & Misc
    if service_spec.get('type') == 'Cache': findings.append("cache_type")
    if spec.get('jmx', {}).get('enabled'): findings.append("jmx_enabled")
    if spec.get('cloudEvents'): findings.append("cloudevents_deprecated")
    if spec.get('autoscale') and service_spec.get('type') == 'DataGrid':
        findings.append("autoscale_invalid")

    # 5. JVM & Resources
    if jvm_opts:
        findings.append("jvm_opts")
        if "-Xmx" in jvm_opts or "-Xms" in jvm_opts: findings.append("xmx_detected")
        if to_gb(container.get('memory', '0Gi')) >= 6.0 and "-XX:+UseG1GC" not in jvm_opts:
            findings.append("g1gc_recommended")

    if not container.get('ephemeral-storage'): findings.append("ephemeral_missing")
    if not container.get('livenessProbe') or not container.get('readinessProbe'):
        findings.append("probes_missing")
    if spec.get('upgrades', {}).get('type') == 'RollingUpdate':
        findings.append("rolling_upgrade_pressure")

    # Rule 33: Prometheus Monitoring Labels
    # Checks for 'prometheus.io/scrape' in the metadata annotations
    annotations = meta.get('annotations', {})
    if annotations.get('prometheus.io/scrape') != 'true':
        findings.append("monitoring_missing")

    return findings
