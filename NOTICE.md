# Third-party notices

This repository vendors LitmusChaos components under Apache-2.0:

- `litmuschaos/litmus-helm`, tag `litmus-core-3.30.0`, commit
  `860331c22d5cd435b2b473ff3b79086e885f2a65`.
- `litmuschaos/chaos-charts`, tag `3.30.0`, commit
  `3d485c7854aeabcf136118ff54b78434a1a14099`.

The core chart and selected source YAML files are copied byte-for-byte; their
licenses are included in `charts/vendored-litmus/files/upstream/`.
`vendor.lock.json` records SHA-256 for every vendored file. Render-time namespace,
identity, label, engine state and image adaptations belong to this wrapper chart.
Container images are referenced, not redistributed in this repository. They and
third-party binaries retain their respective licenses.
