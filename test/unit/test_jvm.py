import sys
import os

# Add the project root (DRC) to the Python path
# This assumes test_jvm.py is in DRC/test/unit/
root_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '../../'))
if root_path not in sys.path:
    sys.path.append(root_path)

# Now it will find the jvm module
from jvm.advisor_jvm import JVMAdvisor

sample_log = """
# JRE version: OpenJDK Runtime Environment (Red_Hat-21.0.7.0.6-2) (21.0.7+6) (build 21.0.7+6-LTS)
# Java VM: OpenJDK 64-Bit Server VM (Red_Hat-21.0.7.0.6-2) (21.0.7+6-LTS, mixed mode, sharing, tiered, compressed oops, compressed class ptrs, g1 gc, linux-s390x)

container (cgroup) information:
container_type: cgroupv2
cpu_quota: 2000
memory_limit: 1800M
memory_usage: 450M

GC Precious Log:
 CardTable entry size: 512
 Card Set container configuration: InlinePtr #cards 5 size 8 Array Of Cards #cards 12 size 40 Howl #buckets 4 coarsen threshold 1843 Howl Bitmap #cards 512 size 80 coarsen threshold 460 Card regions per heap region 1 cards per card region 2048
 CPUs: 51 total, 1 available
 Memory: 1800M
 Large Page Support: Disabled
 NUMA Support: Disabled
 Compressed Oops: Enabled (32-bit)
 Heap Region Size: 1M
 Heap Min Capacity: 8M
 Heap Initial Capacity: 30M
 Heap Max Capacity: 450M
 Pre-touch: Disabled
 Parallel Workers: 1
 Concurrent Workers: 1
 Concurrent Refinement Workers: 1
 Periodic GC: Disabled
"""

advisor = JVMAdvisor(sample_log)
result = advisor.analyze()

import json
print(json.dumps(result, indent=2))