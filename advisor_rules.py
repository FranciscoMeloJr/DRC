# Comprehensive Logic Registry

def check_unknown_fields(spec):
    known = {
        'replicas', 'version', 'service', 'security', 'expose',
        'configListener', 'container', 'affinity', 'logging',
        'upgrades', 'jmx', 'autoscale', 'scheduling', 'dependencies',
        'configMapName', 'cloudEvents', 'extraJvmOpts', 'sites'
    }
    provided_keys = set(spec.keys())
    unknowns = provided_keys - known
    if unknowns:
        return f"SPEC UNKNOWN: Fields not recognized: {', '.join(unknowns)}"
    return None

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
    logging_conf =  spec.get('logging', {})
    log_level = logging_conf.get('level', '').upper()

    if log_level not in ['DEBUG', 'TRACE']:
        findings.append("drc_log")

    # 18. Affinity: hard, soft, weak
    if "affinity" not in spec.get('scheduling', {}):
        findings.append("affinity_weak")
    else:
        # Detect if it's Soft (preferred) vs Hard (required)
        affinity_str = str(spec.get('scheduling', {}).get('affinity', ''))
        if "preferredDuringSchedulingIgnoredDuringExecution" in affinity_str:
            findings.append("affinity_soft")
        if "requiredDuringSchedulingIgnoredDuringExecution" in affinity_str:
            findings.append("affinity_hard")

    # 19. QoS mismatch
    resources = spec.get('container', {}).get('resources', {})
    limits = resources.get('limits', {})
    requests = resources.get('requests', {})
    
    if limits != requests or not limits:
        findings.append("qos_mismatch")

    if debug:
        print(findings)

    return findings
    