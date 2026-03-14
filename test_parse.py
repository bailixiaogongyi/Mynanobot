import re

content = """---
name: pdf-operations
description: >-
  当用户需要处理PDF文档时使用此技能。
always: false
metadata:
  nanobot:
    emoji: "📄"
    requires:
      bins: ["python"]
---

# PDF文档操作技能
"""

match = re.match(r'^---\n(.*?)\n---', content, re.DOTALL)
if match:
    metadata = {}
    for line in match.group(1).split('\n'):
        if ':' in line:
            key, value = line.split(':', 1)
            metadata[key.strip()] = value.strip().strip('"').strip("'")

    print('解析结果:')
    for k, v in metadata.items():
        print(f'  {k}: {repr(v)}')
