# Catalogue Litmus 3.30.0

53 faults, toutes installées par défaut. Les permissions et paramètres restent propres à chaque fault.

| Catégorie | Nombre | Faults |
| --- | ---: | --- |
| aws | 8 | `aws-az-chaos`, `aws-ssm-chaos-by-id`, `aws-ssm-chaos-by-tag`, `ebs-loss-by-id`, `ebs-loss-by-tag`, `ec2-stop-by-id`, `ec2-stop-by-tag`, `rds-instance-stop` |
| azure | 2 | `azure-disk-loss`, `azure-instance-stop` |
| gcp | 4 | `gcp-vm-disk-loss`, `gcp-vm-disk-loss-by-label`, `gcp-vm-instance-stop`, `gcp-vm-instance-stop-by-label` |
| kubernetes | 31 | `container-kill`, `disk-fill`, `docker-service-kill`, `kubelet-service-kill`, `node-cpu-hog`, `node-drain`, `node-io-stress`, `node-memory-hog`, `node-poweroff`, `node-restart`, `node-taint`, `pod-autoscaler`, `pod-cpu-hog`, `pod-cpu-hog-exec`, `pod-delete`, `pod-dns-error`, `pod-dns-spoof`, `pod-http-latency`, `pod-http-modify-body`, `pod-http-modify-header`, `pod-http-reset-peer`, `pod-http-status-code`, `pod-io-stress`, `pod-memory-hog`, `pod-memory-hog-exec`, `pod-network-corruption`, `pod-network-duplication`, `pod-network-latency`, `pod-network-loss`, `pod-network-partition`, `pod-network-rate-limit` |
| load | 1 | `k6-loadgen` |
| spring-boot | 6 | `spring-boot-app-kill`, `spring-boot-cpu-stress`, `spring-boot-exceptions`, `spring-boot-faults`, `spring-boot-latency`, `spring-boot-memory-stress` |
| vmware | 1 | `vmware-vm-poweroff` |

## Scénarios de référence

Chaque scénario existe en variantes Workflow et CronWorkflow (20 YAML au total).

- bank-of-anthos
- namespaced-scope-chaos
- node-cpu-hog
- node-memory-hog
- pod-cpu-hog
- pod-delete
- pod-memory-hog
- podtato-head
- sock-shop
- sock-shop-promProbe

Ces scénarios sont stockés en ConfigMaps et nécessitent une adaptation avant exécution. Voir [le contrat applicatif](application-contract.md).
