# vendored-litmus

Un chart Helm autonome qui embarque **Litmus core 3.30.0**, ses CRD et le
catalogue complet de faults de cette version. Une application peut découvrir le
catalogue, construire des `ChaosEngine` et suivre leurs `ChaosResult` via l’API
Kubernetes, sans ChaosCenter et sans télécharger des manifests au démarrage.

**Installer le chart ne lance aucune campagne de chaos.**

| Contenu installé par défaut | Quantité / comportement |
| --- | --- |
| `litmus-core` vendorisé | Opérateur, RBAC et 3 CRD |
| Faults `ChaosExperiment` | 53, dans le namespace de la release |
| Modèles `ChaosEngine` | 53 ConfigMaps, état initial `stop` |
| Scénarios amont | 10 Workflow + 10 CronWorkflow, stockés dans 20 ConfigMaps comme références |
| Index du catalogue | 1 ConfigMap JSON, version de contrat 1 |
| Identités | Un ServiceAccount consommateur, un exécuteur, RBAC distincts |

Les scénarios Argo sont des **références à adapter**, pas des campagnes activées :
ils gardent leurs paramètres et conventions amont. Argo Workflows n’est pas
installé. Les campagnes directes `ChaosEngine` n’en ont pas besoin.

## Installation

Depuis le dépôt Helm HTTP, hébergé par les fichiers versionnés de ce repository :

```sh
helm repo add vendored-litmus \
  https://raw.githubusercontent.com/sebastien-ribiere/vendored-litmus/main/helm-repository
helm repo update
helm upgrade --install chaos vendored-litmus/vendored-litmus \
  --version 0.1.0 --namespace chaos --create-namespace --wait --timeout 3m
```

Ou depuis les sources, **sans `helm dependency update` et sans téléchargement de
chart supplémentaire** :

```sh
git clone https://github.com/sebastien-ribiere/vendored-litmus.git
cd vendored-litmus
helm upgrade --install chaos ./charts/vendored-litmus \
  --namespace chaos --create-namespace --wait --timeout 3m
```

Le sous-chart amont est commité décompressé sous `charts/`. Les images restent à
récupérer depuis un registre. Les références Litmus utilisent `docker.io`, sans
le proxy `litmuschaos.docker.scarf.sh`.

## Utilisation par une application

```sh
# Découvrir les faults, les ConfigMaps de modèles et le ServiceAccount d’exécution.
kubectl -n chaos get cm chaos-vendored-litmus-index \
  -o jsonpath='{.data.catalogue\.json}' | jq .

# Lire un modèle en utilisant le nom présent dans l’index.
engine_cm=$(kubectl -n chaos get cm chaos-vendored-litmus-index \
  -o jsonpath='{.data.catalogue\.json}' | \
  jq -r '.faults[] | select(.name == "pod-delete") | .engineConfigMap')
kubectl -n chaos get cm "$engine_cm" -o jsonpath='{.data.engine\.yaml}'
```

L’application utilise `chaos-vendored-litmus-consumer` comme ServiceAccount,
remplit la cible et les paramètres du modèle, lui donne un nom unique, puis crée
un `ChaosEngine` avec `engineState: active`. L’exécution utilise
`chaos-vendored-litmus-executor`. Voir le [contrat d’intégration](docs/application-contract.md)
pour les endpoints, le suivi du verdict et les limites de permissions.

### Démonstration explicite sur une application jetable

Ces commandes **déclenchent un pod-delete** uniquement sur le Deployment
`chaos-demo` de l’exemple, dans le namespace `chaos` :

```sh
kubectl apply -n chaos -f examples/demo-app.yaml
kubectl rollout status deployment/chaos-demo -n chaos
kubectl apply -f examples/pod-delete-engine.yaml
kubectl -n chaos get chaosengines,chaosresults -w
```

Le résultat attendu est `demo-pod-delete-pod-delete`, phase `Completed`, verdict
`Pass`. L’exemple suppose le nom de release et le namespace `chaos` utilisés plus
haut. Une fois la campagne terminée :

```sh
kubectl delete -f examples/pod-delete-engine.yaml
kubectl delete -n chaos -f examples/demo-app.yaml
```

## Sélection et réutilisation

```sh
# Uniquement les 31 faults Kubernetes, sans les références Argo.
helm upgrade --install chaos ./charts/vendored-litmus -n chaos \
  --create-namespace -f examples/kubernetes-only.yaml

# Catalogue dans un namespace applicatif, CRD et opérateur global déjà présents.
helm upgrade --install app-catalogue ./charts/vendored-litmus \
  -n mon-application --create-namespace -f examples/catalogue-only.yaml
```

| Valeur | Défaut | Effet |
| --- | --- | --- |
| `litmus-core.enabled` | `true` | Installer core ; `false` pour réutiliser un opérateur existant |
| `litmus-core.operatorMode` | `standard` | Opérateur observant tous les namespaces |
| `catalogue.categories` | `[]` | Toutes les catégories ; sinon filtre par catégorie |
| `catalogue.include` | `[]` | Toutes les faults des catégories retenues ; sinon noms explicites |
| `catalogue.exclude` | `[]` | Exclut ces noms après les autres filtres |
| `catalogue.engineTemplates` | `true` | Publier les modèles d’engine |
| `catalogue.workflowTemplates` | `true` | Publier les 20 scénarios amont indépendamment du filtre de faults |
| `execution.rbac.scope` | `Namespace` | `Cluster` pour les faults nœuds / cibles hors namespace |
| `execution.serviceAccount.name` | dérivé de la release | Identité d’exécution référencée dans les modèles |
| `consumer.serviceAccount.name` | dérivé de la release | Identité de l’application orchestratrice |
| `images.litmusRegistry` | `docker.io` | Préfixe remplaçant Scarf dans le catalogue et ses helpers |
| `images.overrides` | `{}` | Remplacements exacts d’images, y compris par digest |

Les listes de catégories ou de noms inconnus, et une sélection vide, échouent au
rendu. Les droits d’exécution sont l’union dédupliquée des permissions déclarées
par les faults sélectionnées. Par défaut ils sont liés **au namespace de la
release** : installer le catalogue complet ne donne pas les droits cluster
nécessaires aux faults sur les nœuds. `execution.rbac.scope: Cluster` est une
extension explicite et large des permissions. Les credentials cloud, permissions
IAM, agents Spring Boot et privilèges des helpers restent à fournir selon la fault.

Déployer **un seul opérateur global par cluster**, et **un seul catalogue par
namespace** : les noms `ChaosExperiment` sont ceux de Litmus, sans préfixe Helm.
Ne pas faire adopter une installation existante par Helm sans migration de sa
propriété. Un opérateur `namespaced` ne dessert pas les catalogues des autres
namespaces.

## Registre privé / Harbor

```sh
helm template chaos ./charts/vendored-litmus -f examples/harbor.yaml
make images
```

Adapter `examples/harbor.yaml` et les trois dépôts d’images `litmus-core`.
`images.litmusRegistry` agit sur le catalogue, pas sur le sous-chart inchangé.
Les helpers tiers et les scénarios Argo contiennent aussi des images `latest` ou
sans tag héritées de l’amont : la version du catalogue est figée, **pas toutes les
images tierces**. Les miroiter et utiliser `images.overrides` avec leurs digests
pour une campagne reproductible. `make images` liste les références explicites,
y compris celles des scénarios stockés ; les images implicites choisies par des
binaires nécessitent une vérification propre à la fault.

`execution.serviceAccount.imagePullSecrets` permet d’associer des secrets
existants à l’exécuteur. Le chart core amont n’expose pas `imagePullSecrets` pour
l’opérateur : utiliser un registre accessible par les nœuds ou un mécanisme
externe d’injection. Aucun secret ni credential cloud n’est embarqué.

## CRD, mises à jour et désinstallation

Helm installe les CRD, mais ne les met pas à jour et ne les supprime pas. Les
revoir/appliquer séparément lors d’une montée de version, avant le chart. Avec
Argo CD, prévoir l’ordre CRD → opérateur/catalogue → campagnes. Éviter de laisser
Helm et une campagne Argo amont gérer le même `ChaosExperiment` : certains exemples
amont réappliquent leurs propres définitions.

Arrêter et supprimer les engines, attendre leur nettoyage, puis désinstaller les
releases catalogue et enfin core. Les CRD et les éventuels résultats conservés
restent dans le cluster. Ne pas supprimer les CRD pour « nettoyer » si d’autres
applications les utilisent.

## Développement et publication

```sh
python3 -m pip install -r requirements-dev.txt
make test                     # intégrité des sources + Helm lint + 11 tests
make package                  # archive autonome dans dist/
HELM=helm scripts/package-repository.sh  # archive et index HTTP committables
```

Le workflow CI teste aussi l’installation, l’upgrade, la réutilisation du catalogue
et une campagne `pod-delete` sur une application jetable dans un cluster Kind.
Le script refuse tout contexte autre que `kind-vendored-litmus-ci`.

Le dépôt HTTP fonctionne sans activer GitHub Pages. Lors d’une release, augmenter
la version du chart, régénérer le paquet/index, les committer ensemble et conserver
les anciennes archives. Un tag `chart-vX.Y.Z` déclenche en plus la publication OCI
sur `ghcr.io/sebastien-ribiere/charts/vendored-litmus` ; cet emplacement n’existe
qu’après une publication réussie. La visibilité du package GHCR se règle ensuite
sur GitHub si nécessaire.

Voir [la procédure de vendoring](docs/vendoring.md), [l’inventaire](docs/catalogue.md)
et [les licences amont](NOTICE.md).
