# Contrat du catalogue pour une application

## Découverte et identités

Le catalogue vit dans le namespace de la release, comme ses `ChaosExperiment`,
`ChaosEngine` et `ChaosResult`. Les cibles peuvent être dans d’autres namespaces
uniquement si l’opérateur et l’exécuteur disposent des droits adaptés.

L’application peut découvrir l’index par labels :

```text
GET /api/v1/namespaces/{namespace}/configmaps?labelSelector=vendored-litmus.io%2Fcatalogue%3Dindex
```

Utiliser aussi `app.kubernetes.io/instance=<release>` si plusieurs types de
catalogues sont présents. Le champ `data["catalogue.json"]` contient :

```json
{
  "schemaVersion": 1,
  "litmusVersion": "3.30.0",
  "namespace": "chaos",
  "executionServiceAccount": "chaos-vendored-litmus-executor",
  "faults": [{
    "name": "pod-delete",
    "category": "kubernetes",
    "engineConfigMap": "<nom à lire dans l’index>"
  }],
  "workflowReferences": [{
    "name": "pod-delete",
    "variant": "workflow",
    "configMap": "<nom à lire dans l’index>",
    "key": "manifest.yaml",
    "requires": "Argo Workflows; application-specific adaptation"
  }]
}
```

Ne pas reconstruire les noms des ConfigMaps : ils sont normalisés et tronqués.
`engineConfigMap` est absent si `catalogue.engineTemplates=false`.
`workflowReferences` est vide si `catalogue.workflowTemplates=false`.

Le consommateur peut lire les ConfigMaps, définitions et résultats du namespace,
et créer/modifier/supprimer des engines. Il ne modifie pas le catalogue. Le droit
de créer un engine permet de déléguer des perturbations à l’exécuteur ; réserver
cette identité à une application de confiance. RBAC seul ne filtre ni les cibles
ni les noms de faults dans le contenu d’un engine. Une politique d’admission peut
compléter cette frontière selon l’environnement.

## Déclencher et suivre une campagne

1. Lire l’index et vérifier `schemaVersion` et `litmusVersion`.
2. Lire le `ChaosExperiment` pour découvrir `spec.definition.env`, `permissions`,
   volumes, secrets et détails de la fault. Les métadonnées amont complètes sont
   aussi incluses dans les fichiers du chart.
3. Lire `data["engine.yaml"]` dans la ConfigMap référencée. C’est un blueprint,
   pas un objet déjà installé. Son état est `stop`.
4. Copier le blueprint : renseigner un nom DNS unique, le namespace de catalogue,
   le ServiceAccount d’exécution de l’index, `appinfo` (si applicable), les variables
   obligatoires et les probes métier. Pour les applications non annotées, mettre
   `annotationCheck: 'false'` explicitement, comme dans l’exemple du repository.
5. Vérifier les prérequis propres à la fault (credentials, IAM, Spring Boot,
   accès nœuds, politiques de sécurité, images). Les champs vides amont ne sont
   pas automatiquement remplis par le chart.
6. Passer `spec.engineState` à `active`, puis créer l’objet :

   ```text
   POST /apis/litmuschaos.io/v1alpha1/namespaces/{namespace}/chaosengines
   ```

7. Suivre l’engine et le résultat `{engine-name}-{fault-name}` via les endpoints
   `chaosengines` et `chaosresults` de la même API. Attendre une phase terminale ;
   un POST réussi ou un pod terminé ne constitue pas un verdict de résilience.
   Dans l’exemple, le succès est `status.experimentStatus.phase=Completed` et
   `status.experimentStatus.verdict=Pass`. Gérer aussi échec, arrêt, timeout et
   absence de résultat. Le nom généré de l’engine doit rester assez court pour
   les noms de ressources dérivés.
8. Archiver paramètres, identifiants, version du catalogue, verdict et résultats
   de probes avant nettoyage. L’application pilote l’ordre des faults, délais,
   concurrence et critères d’arrêt de sa campagne.

Pour demander l’arrêt : patcher `spec.engineState: stop`, puis attendre la fin du
nettoyage de la fault. Un arrêt demandé n’est pas une garantie instantanée de
restauration de l’infrastructure. Supprimer l’engine après collecte des preuves.

L’exemple [pod-delete-engine.yaml](../examples/pod-delete-engine.yaml) est
exécutable après installation avec release/namespace `chaos` et déploiement de
l’application de démonstration. Il cible seulement `app=chaos-demo`.

## Scénarios amont et Argo

Les 20 YAML Workflow/CronWorkflow sont inclus comme données de référence pour
préserver les scénarios amont sans lancer de jobs ni de planification à
l’installation. Les expressions `{{workflow.parameters.*}}` restent littérales.
Le préfixe Scarf et les remplacements explicites d’images sont appliqués au rendu.

Ils ne sont pas directement exécutables sans adaptation : namespaces, comptes
`argo-chaos`/`litmus-admin`, applications de démonstration, paramètres et certains
tags `latest` viennent de l’amont. Certains installent des faults ou applications.
Avant utilisation avec Argo, supprimer l’étape d’installation des faults déjà
gérées par Helm, adapter les identités et vérifier les dépendances. Le parcours
recommandé pour une application orchestratrice est l’API `ChaosEngine` ci-dessus.
