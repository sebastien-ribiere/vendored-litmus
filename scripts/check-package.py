#!/usr/bin/env python3
"""Check published index digest and chart payload against the source tree."""
import hashlib
from pathlib import Path
import tarfile
import yaml

root = Path(__file__).resolve().parents[1]
chart = root / 'charts/vendored-litmus'
metadata = yaml.safe_load((chart / 'Chart.yaml').read_text())
version = metadata['version']
archive = root / f'helm-repository/vendored-litmus-{version}.tgz'
index = yaml.safe_load((root / 'helm-repository/index.yaml').read_text())
entry = next(e for e in index['entries']['vendored-litmus'] if e['version'] == version)
assert entry['digest'] == hashlib.sha256(archive.read_bytes()).hexdigest()
with tarfile.open(archive) as tar:
    files = {m.name.removeprefix('vendored-litmus/'): tar.extractfile(m).read() for m in tar.getmembers() if m.isfile()}
expected = {str(p.relative_to(chart)) for p in chart.rglob('*') if p.is_file()}
assert set(files) == expected, (set(files) - expected, expected - set(files))
for relative, data in files.items():
    path = chart / relative
    # Helm normalizes Chart.yaml metadata during packaging.
    if path.name == 'Chart.yaml':
        source, packed = yaml.safe_load(path.read_bytes()), yaml.safe_load(data)
        # Empty repository fields may be inserted for local dependencies.
        for value in [source, packed]:
            for dep in value.get('dependencies', []):
                if dep.get('repository') == '':
                    dep.pop('repository')
        assert source == packed, relative
    else:
        assert data == path.read_bytes(), relative
print(f'Published chart {version}: digest and {len(files)} source files verified')
