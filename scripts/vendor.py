#!/usr/bin/env python3
"""Import pinned upstream git checkouts, or verify the offline source inventory."""
import argparse
import hashlib
import json
from pathlib import Path
import shutil
import subprocess

ROOT = Path(__file__).resolve().parents[1]
CHART = ROOT / 'charts/vendored-litmus'
SOURCES = {
    'litmus-core': {'repository': 'https://github.com/litmuschaos/litmus-helm', 'ref': 'litmus-core-3.30.0', 'commit': '860331c22d5cd435b2b473ff3b79086e885f2a65'},
    'chaos-charts': {'repository': 'https://github.com/litmuschaos/chaos-charts', 'ref': '3.30.0', 'commit': '3d485c7854aeabcf136118ff54b78434a1a14099'},
}

def inventory():
    paths = list((CHART / 'charts/litmus-core').rglob('*')) + list((CHART / 'files/upstream').rglob('*'))
    return {str(p.relative_to(ROOT)): hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(paths) if p.is_file()}

def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--helm-source', type=Path)
    p.add_argument('--chaos-source', type=Path)
    p.add_argument('--check', action='store_true')
    args = p.parse_args()
    lockfile = ROOT / 'vendor.lock.json'
    if args.check:
        lock = json.loads(lockfile.read_text())
        assert lock['sources'] == SOURCES, 'Pinned source metadata changed'
        assert lock['files'] == inventory(), 'Vendored content differs from vendor.lock.json'
        print(f"Verified {len(lock['files'])} vendored files")
        return
    if not args.helm_source or not args.chaos_source:
        p.error('provide both source checkouts, or --check')
    for key, src in [('litmus-core', args.helm_source), ('chaos-charts', args.chaos_source)]:
        sha = subprocess.check_output(['git', '-C', str(src), 'rev-parse', 'HEAD'], text=True).strip()
        assert sha == SOURCES[key]['commit'], f'{key}: unexpected commit {sha}'
        assert not subprocess.check_output(['git', '-C', str(src), 'status', '--porcelain']), f'{key}: dirty checkout'
    core = CHART / 'charts/litmus-core'
    upstream = CHART / 'files/upstream'
    shutil.rmtree(core, ignore_errors=True)
    shutil.rmtree(upstream, ignore_errors=True)
    shutil.copytree(args.helm_source / 'charts/litmus-core', core)
    upstream.mkdir(parents=True)
    shutil.copyfile(args.helm_source / 'LICENSE', upstream / 'litmus-helm.LICENSE')
    shutil.copyfile(args.chaos_source / 'LICENSE', upstream / 'chaos-charts.LICENSE')
    for folder in ['faults', 'experiments']:
        for src in sorted((args.chaos_source / folder).rglob('*.yaml')):
            dst = upstream / src.relative_to(args.chaos_source)
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(src, dst)
    lockfile.write_text(json.dumps({'version': 1, 'sources': SOURCES, 'files': inventory()}, indent=2) + '\n')
    print(f'Imported {len(inventory())} files without modification')

if __name__ == '__main__':
    main()
