# Vendoring et maintenance

Les sources amont sont conservées sans modification, licences incluses.
`vendor.lock.json` contient les URLs, tags, commits et SHA-256 des 230 fichiers
importés : le chart core complet, tous les YAML de `faults/` et `experiments/`,
et les deux licences. Les icônes binaires de ChaosHub ne sont pas nécessaires au
catalogue Kubernetes et ne sont pas importées.

```sh
git clone --depth 1 --branch litmus-core-3.30.0 \
  https://github.com/litmuschaos/litmus-helm.git /tmp/litmus-helm
git clone --depth 1 --branch 3.30.0 \
  https://github.com/litmuschaos/chaos-charts.git /tmp/chaos-charts
python3 scripts/vendor.py --helm-source /tmp/litmus-helm --chaos-source /tmp/chaos-charts
python3 scripts/vendor.py --check
```

L’import refuse un checkout sale ou un commit différent de celui attendu. La
vérification compare aussi l’ensemble des fichiers : ajout/suppression détectés.
Les bundles `faults/<category>/experiments.yaml` sont conservés pour traçabilité,
mais seuls les `fault.yaml` individuels sont rendus, pour éviter les doublons.

Le wrapper adapte au rendu les namespaces, labels, images et comptes, et neutralise
les modèles d’engine. Il n’applique jamais le contenu d’une ConfigMap. Le core
amont reste inchangé ; ses images sont remplacées par les valeurs du parent.

Pour une montée de version :

1. Examiner les changements amont (CRD, images, permissions et scénarios).
2. Modifier les deux pins de `scripts/vendor.py`, les métadonnées/versions du
   chart et ses images. Importer depuis les commits exacts.
3. Examiner le diff complet de `vendor.lock.json`, des CRD et des permissions.
4. Mettre à jour l’inventaire et les attentes de couverture des tests si nécessaire.
5. Exécuter `make test` et la CI Kind. Vérifier les manifests des images et les
   architectures de vos nœuds ; un tag existant n’implique pas une image multiarch.
6. Gérer séparément l’upgrade des CRD existantes, puis incrémenter la version du
   wrapper et régénérer `helm-repository/` sans supprimer les anciennes archives.

Le SHA-256 du paquet est dans `helm-repository/index.yaml`. Le script
`check-package.py` compare aussi le contenu de l’archive distribuée aux sources.
L’installation depuis le `.tgz` ne contacte pas les dépôts Helm amont.
