"""Contract checks against real Helm renders and vendored CRD schemas."""
import collections
import json
import os
from pathlib import Path
import subprocess
import tempfile
import unittest

import jsonschema
import yaml

ROOT = Path(__file__).resolve().parents[1]
CHART = ROOT / 'charts/vendored-litmus'
HELM = os.environ.get('HELM', 'helm')

def render(values=None, chart=CHART, expect_success=True):
    with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml') as f:
        yaml.safe_dump(values or {}, f)
        f.flush()
        result = subprocess.run([HELM, 'template', 'chaos', str(chart), '-n', 'chaos', '--include-crds', '-f', f.name], capture_output=True, text=True)
    if not expect_success:
        assert result.returncode != 0, 'invalid config was accepted'
        return result.stderr
    assert result.returncode == 0, result.stderr
    return [d for d in yaml.safe_load_all(result.stdout) if d], result.stdout

class ChartContract(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.docs, cls.text = render()
        cls.faults = [d for d in cls.docs if d['kind'] == 'ChaosExperiment']
        cls.cms = [d for d in cls.docs if d['kind'] == 'ConfigMap']

    def test_complete_unique_catalogue_and_no_execution(self):
        upstream = [yaml.safe_load(p.read_text()) for p in (CHART / 'files/upstream/faults').glob('*/*/fault.yaml')]
        self.assertEqual(len(upstream), 53)
        self.assertEqual({d['metadata']['name'] for d in upstream}, {d['metadata']['name'] for d in self.faults})
        counts = collections.Counter(d['kind'] for d in self.docs)
        self.assertEqual(counts['ConfigMap'], 74)
        self.assertEqual(counts['CustomResourceDefinition'], 3)
        self.assertFalse(set(counts) & {'ChaosEngine', 'Workflow', 'CronWorkflow', 'Job'})
        identities = [(d['kind'], d['metadata'].get('namespace'), d['metadata']['name']) for d in self.docs]
        self.assertEqual(len(identities), len(set(identities)))
        for cm in self.cms:
            self.assertLess(sum(len(v.encode()) for v in cm['data'].values()), 1_000_000)
            self.assertLessEqual(len(cm['metadata']['name']), 63)

    def test_crd_schemas_accept_faults_engine_blueprints_and_demo(self):
        schemas = {d['spec']['names']['kind']: d['spec']['versions'][0]['schema']['openAPIV3Schema'] for d in self.docs if d['kind'] == 'CustomResourceDefinition'}
        for fault in self.faults:
            jsonschema.validate(fault, schemas['ChaosExperiment'])
        engines = [yaml.safe_load(cm['data']['engine.yaml']) for cm in self.cms if 'engine.yaml' in cm['data']]
        self.assertEqual(len(engines), 53)
        for engine in engines:
            jsonschema.validate(engine, schemas['ChaosEngine'])
            self.assertEqual(engine['spec']['engineState'], 'stop')
            self.assertEqual(engine['metadata']['namespace'], 'chaos')
            self.assertEqual(engine['spec']['chaosServiceAccount'], 'chaos-vendored-litmus-executor')
        jsonschema.validate(yaml.safe_load((ROOT / 'examples/pod-delete-engine.yaml').read_text()), schemas['ChaosEngine'])

    def test_index_resolves_every_reference_and_preserves_argo(self):
        cms = {d['metadata']['name']: d for d in self.cms}
        index = json.loads(cms['chaos-vendored-litmus-index']['data']['catalogue.json'])
        self.assertEqual(len(index['faults']), 53)
        self.assertEqual(len(index['workflowReferences']), 20)
        for entry in index['faults']:
            engine = yaml.safe_load(cms[entry['engineConfigMap']]['data']['engine.yaml'])
            self.assertEqual(engine['spec']['experiments'][0]['name'], entry['name'])
        for entry in index['workflowReferences']:
            raw = cms[entry['configMap']]['data'][entry['key']]
            doc = yaml.safe_load(raw)
            self.assertIn(doc['kind'], ['Workflow', 'CronWorkflow'])
            self.assertIn('{{workflow.parameters.', raw)

    def test_no_scarf_and_all_core_images_pinned(self):
        self.assertNotIn('litmuschaos.docker.scarf.sh', self.text)
        deployment = next(d for d in self.docs if d['kind'] == 'Deployment')
        container = deployment['spec']['template']['spec']['containers'][0]
        self.assertEqual(container['image'], 'docker.io/litmuschaos/chaos-operator:3.30.0')
        self.assertIn({'name': 'CHAOS_RUNNER_IMAGE', 'value': 'docker.io/litmuschaos/chaos-runner:3.30.0'}, container['env'])
        for fault in self.faults:
            self.assertTrue(fault['spec']['definition']['image'].endswith(':3.30.0'))

    def test_mirror_override_including_helpers_and_workflow_data(self):
        vals = {'images': {'litmusRegistry': 'harbor.test/proxy', 'overrides': {'alexeiled/stress-ng:latest-ubuntu': 'harbor.test/stress@sha256:' + 'a'*64}}}
        docs, text = render(vals)
        self.assertNotIn('litmuschaos.docker.scarf.sh', text)
        self.assertNotIn('alexeiled/stress-ng:latest-ubuntu', text)
        fault = next(d for d in docs if d['kind'] == 'ChaosExperiment' and d['metadata']['name'] == 'pod-memory-hog')
        self.assertEqual(fault['spec']['definition']['image'], 'harbor.test/proxy/litmuschaos/go-runner:3.30.0')
        env = {e['name']: e.get('value') for e in fault['spec']['definition']['env']}
        self.assertEqual(env['LIB_IMAGE'], 'harbor.test/proxy/litmuschaos/go-runner:3.30.0')
        self.assertIn('@sha256:', env['STRESS_IMAGE'])

    def test_category_include_exclude_and_rbac_follow_selection(self):
        docs, _ = render({'catalogue': {'categories': ['kubernetes'], 'include': ['pod-delete', 'pod-cpu-hog'], 'exclude': ['pod-cpu-hog'], 'workflowTemplates': False}})
        faults = [d for d in docs if d['kind'] == 'ChaosExperiment']
        self.assertEqual([d['metadata']['name'] for d in faults], ['pod-delete'])
        role = next(d for d in docs if d['kind'] == 'Role' and d['metadata']['name'].endswith('-executor'))
        source = yaml.safe_load((CHART / 'files/upstream/faults/kubernetes/pod-delete/fault.yaml').read_text())
        self.assertEqual({json.dumps(r, sort_keys=True) for r in role['rules']}, {json.dumps(r, sort_keys=True) for r in source['spec']['definition']['permissions']})
        self.assertEqual(len([d for d in docs if d['kind'] == 'ConfigMap']), 2)

    def test_catalogue_only_and_core_only(self):
        docs, _ = render({'litmus-core': {'enabled': False}})
        self.assertFalse(any(d['kind'] in ['CustomResourceDefinition', 'Deployment', 'ClusterRole'] for d in docs))
        self.assertEqual(sum(d['kind'] == 'ChaosExperiment' for d in docs), 53)
        docs, _ = render({'catalogue': {'enabled': False}})
        self.assertFalse(any(d['kind'] in ['ConfigMap', 'ChaosExperiment', 'Role'] for d in docs))

    def test_explicit_cluster_scope_and_external_identities(self):
        docs, _ = render({'litmus-core': {'enabled': False}, 'execution': {'rbac': {'scope': 'Cluster'}, 'serviceAccount': {'create': False, 'name': 'external-executor'}}, 'consumer': {'serviceAccount': {'create': False, 'name': 'external-consumer'}}})
        self.assertFalse(any(d['kind'] == 'ServiceAccount' for d in docs))
        binding = next(d for d in docs if d['kind'] == 'ClusterRoleBinding')
        self.assertEqual(binding['subjects'][0]['name'], 'external-executor')
        self.assertEqual(binding['subjects'][0]['namespace'], 'chaos')
        self.assertNotIn('namespace', binding['metadata'])

    def test_invalid_selection_or_scope_fails(self):
        for values, message in [({'catalogue': {'categories': ['typo']}}, 'Unknown fault category'), ({'catalogue': {'include': ['typo']}}, 'Unknown fault name'), ({'catalogue': {'include': ['pod-delete'], 'exclude': ['pod-delete']}}, 'Fault selection is empty'), ({'execution': {'rbac': {'scope': 'typo'}}}, 'scope')]:
            with self.subTest(values=values):
                self.assertIn(message, render(values, expect_success=False))

    def test_package_is_self_contained(self):
        with tempfile.TemporaryDirectory() as tmp:
            subprocess.run([HELM, 'package', str(CHART), '--destination', tmp], check=True, capture_output=True)
            docs, _ = render(chart=Path(tmp) / 'vendored-litmus-0.1.0.tgz')
            self.assertEqual(docs, self.docs)

    def test_examples_render(self):
        for path in (ROOT / 'examples').glob('*.yaml'):
            if path.name not in ['demo-app.yaml', 'pod-delete-engine.yaml']:
                with self.subTest(path=path):
                    render(yaml.safe_load(path.read_text()))

if __name__ == '__main__':
    unittest.main()
