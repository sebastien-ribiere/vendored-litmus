#!/usr/bin/env bash
# Run ONLY against the disposable kind cluster created by the CI workflow.
set -euo pipefail
[[ "$(kubectl config current-context)" == "kind-vendored-litmus-ci" ]] || {
  echo 'Refusing to run outside kind-vendored-litmus-ci' >&2; exit 1;
}
chart=charts/vendored-litmus
helm install chaos "$chart" --namespace chaos --create-namespace --wait --timeout 180s
[[ "$(kubectl -n chaos get chaosexperiments -o json | jq '.items | length')" == 53 ]]
[[ "$(kubectl -n chaos get chaosengines -o json | jq '.items | length')" == 0 ]]
# Real API validation and idempotent upgrade.
helm upgrade chaos "$chart" -n chaos --wait --timeout 180s
helm template chaos "$chart" -n chaos | kubectl apply --dry-run=server -f - >/dev/null
# Reuse the global operator and CRDs from another application namespace.
helm install app-catalogue "$chart" -n application --create-namespace -f examples/catalogue-only.yaml --wait --timeout 180s
[[ "$(kubectl -n application get chaosexperiments -o json | jq '.items | length')" == 53 ]]
consumer=system:serviceaccount:chaos:chaos-vendored-litmus-consumer
executor=system:serviceaccount:chaos:chaos-vendored-litmus-executor
[[ "$(kubectl auth can-i create chaosengines.litmuschaos.io -n chaos --as="$consumer")" == yes ]]
[[ "$(kubectl auth can-i delete pods -n chaos --as="$executor")" == yes ]]
[[ "$(kubectl auth can-i patch nodes --as="$executor" 2>/dev/null || true)" == no ]]
# Explicitly exercise one fault only on the disposable demo workload.
kubectl apply -n chaos -f examples/demo-app.yaml
kubectl rollout status deployment/chaos-demo -n chaos --timeout=180s
kubectl apply -f examples/pod-delete-engine.yaml
for ((attempt=0; attempt<90; attempt++)); do
  verdict=$(kubectl get chaosresult demo-pod-delete-pod-delete -n chaos -o jsonpath='{.status.experimentStatus.verdict}' 2>/dev/null || true)
  phase=$(kubectl get chaosresult demo-pod-delete-pod-delete -n chaos -o jsonpath='{.status.experimentStatus.phase}' 2>/dev/null || true)
  if [[ "$phase" == Completed ]]; then
    [[ "$verdict" == Pass ]] || { echo "Fault verdict: $verdict" >&2; exit 1; }
    break
  fi
  sleep 5
done
[[ "$phase" == Completed && "$verdict" == Pass ]]
kubectl rollout status deployment/chaos-demo -n chaos --timeout=120s
# Engines must be removed before removing catalogue resources/operator.
kubectl delete chaosengine demo-pod-delete -n chaos --wait=true --timeout=120s
helm uninstall app-catalogue -n application
helm uninstall chaos -n chaos
kubectl get crd chaosengines.litmuschaos.io >/dev/null
echo 'Install, upgrade, catalogue reuse, pod-delete and uninstall passed.'
