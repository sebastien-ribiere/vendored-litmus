#!/usr/bin/env python3
"""List explicit image references in rendered YAML, including inert catalogue data.

Includes upstream reference-only workflows. Implicit images chosen inside binaries
and provider-specific tools must also be checked before an air-gapped campaign.
"""
import re
import sys
import yaml

found = set()
def walk(value):
    if isinstance(value, dict):
        for key, child in value.items():
            if key == 'image' and isinstance(child, str):
                found.add(child)
            if key == 'name' and isinstance(child, str) and child.endswith('IMAGE') and isinstance(value.get('value'), str) and value['value']:
                found.add(value['value'])
            walk(child)
    elif isinstance(value, list):
        for child in value:
            walk(child)
    elif isinstance(value, str) and '\n' in value:
        # Embedded Workflow artifacts can contain another YAML document.
        try:
            for doc in yaml.safe_load_all(value):
                if isinstance(doc, (dict, list)):
                    walk(doc)
        except yaml.YAMLError:
            pass
        # Operator runner image is in an env value, captured by *_IMAGE above.

for doc in yaml.safe_load_all(sys.stdin):
    walk(doc)
print('\n'.join(sorted(found)))
