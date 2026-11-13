{{- define "vl.name" -}}
{{- default .Chart.Name .Values.nameOverride | trunc 63 | trimSuffix "-" -}}
{{- end -}}
{{- define "vl.fullname" -}}
{{- default (printf "%s-%s" .Release.Name (include "vl.name" .)) .Values.fullnameOverride | trunc 40 | trimSuffix "-" -}}
{{- end -}}
{{- define "vl.labels" -}}
app.kubernetes.io/name: {{ include "vl.name" . }}
app.kubernetes.io/instance: {{ .Release.Name }}
app.kubernetes.io/managed-by: {{ .Release.Service }}
app.kubernetes.io/version: {{ .Chart.AppVersion | quote }}
helm.sh/chart: {{ printf "%s-%s" .Chart.Name .Chart.Version | quote }}
{{- end -}}
{{- define "vl.executionSA" -}}
{{- default (printf "%s-executor" (include "vl.fullname" .)) .Values.execution.serviceAccount.name -}}
{{- end -}}
{{- define "vl.consumerSA" -}}
{{- default (printf "%s-consumer" (include "vl.fullname" .)) .Values.consumer.serviceAccount.name -}}
{{- end -}}
{{/* Transform data as text; never tpl upstream Argo expressions. */}}
{{- define "vl.rewriteImages" -}}
{{- $text := .text -}}
{{- range $original, $replacement := .root.Values.images.overrides -}}
{{- $text = replace $original $replacement $text -}}
{{- end -}}
{{- replace "litmuschaos.docker.scarf.sh/" (printf "%s/" (trimSuffix "/" .root.Values.images.litmusRegistry)) $text -}}
{{- end -}}
{{/* Build a deterministic, validated catalogue, shared by rendering and RBAC. */}}
{{- define "vl.faults" -}}
{{- $root := . -}}
{{- $all := dict -}}
{{- $categories := dict -}}
{{- range $path, $_ := .Files.Glob "files/upstream/faults/*/*/fault.yaml" -}}
{{- $doc := fromYaml ($root.Files.Get $path) -}}
{{- $name := $doc.metadata.name -}}
{{- $category := index (splitList "/" $path) 3 -}}
{{- if hasKey $all $name }}{{ fail (printf "Duplicate fault: %s" $name) }}{{ end -}}
{{- $_ := set $categories $category true -}}
{{- $_ := set $all $name (dict "name" $name "category" $category "path" $path) -}}
{{- end -}}
{{- range .Values.catalogue.categories -}}
{{- if not (hasKey $categories .) }}{{ fail (printf "Unknown fault category: %s" .) }}{{ end -}}
{{- end -}}
{{- range concat .Values.catalogue.include .Values.catalogue.exclude -}}
{{- if not (hasKey $all .) }}{{ fail (printf "Unknown fault name: %s" .) }}{{ end -}}
{{- end -}}
{{- $selected := list -}}
{{- range $name := keys $all | sortAlpha -}}
{{- $fault := get $all $name -}}
{{- if and (or (empty $root.Values.catalogue.categories) (has $fault.category $root.Values.catalogue.categories)) (or (empty $root.Values.catalogue.include) (has $name $root.Values.catalogue.include)) (not (has $name $root.Values.catalogue.exclude)) -}}
{{- $selected = append $selected $fault -}}
{{- end -}}
{{- end -}}
{{- if and .Values.catalogue.enabled (empty $selected) }}{{ fail "Fault selection is empty" }}{{ end -}}
{{- toJson $selected -}}
{{- end -}}
{{- define "vl.documentName" -}}
{{- printf "%s-%s-%s" (include "vl.fullname" .root | trunc 20 | trimSuffix "-") .kind (.id | lower | trunc 32 | trimSuffix "-") | trimSuffix "-" -}}
{{- end -}}
