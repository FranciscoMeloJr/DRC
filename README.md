# DRC
DRC is the parser for DG 8/Infinispan yamls aka CR/CRD - the name comes from there.
Usage:::
$ python advisor_ui.py test/expose.yaml 
=================================================================
RESOURCE: example-infinispan (Infinispan)
  Versions:
    Operator:   N/A
    Operand:    N/A
  Replicas:     1
  Exposed:      Yes
  Encryption:   Disabled
  QoS Class:    BestEffort (Host Bound)
  Cross-Site:   Disabled
  Target Heap:  50% of Host RAM  Off-Heap: 50% of Host RAM

  [!] [CRITICAL] there is only one pod in this cluster.
  [!] [IMPORTANT] the pods could be deployed in the same hosts
  [!] [IMPORTANT] KCS 6973004: spec.configListener is missing. Bidirectional replication is disabled.
  [!] [WARNING] RESOURCE RISK: No ephemeral-storage limit. Logs or local stores could cause node pressure.
  [!] [CRITICAL] STABILITY: Custom probes missing. Default settings may cause pods to be killed during state transfer.
  [!] [IMPORTANT] Monitoring: Prometheus scrape labels or annotations are missing. Cluster metrics will not be collected.
  [!] [CRITICAL] KCS 6991230: Best-Effort QoS (Host Bound). Pod is prioritized for eviction during node pressure.
-----------------------------------------------------------------

FINAL SUMMARY - 2026-03-11 02:09:45
  Critical Risks:        3
  Important:             3
  Warnings:              1
  General Notes:         0
=================================================================
