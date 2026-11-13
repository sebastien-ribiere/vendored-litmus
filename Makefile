HELM ?= helm
PYTHON ?= python3
CHART := charts/vendored-litmus
.PHONY: test lint package verify-vendor images dependencies
verify-vendor:
	$(PYTHON) scripts/vendor.py --check
dependencies:
	$(HELM) dependency build $(CHART)
lint: dependencies
	$(HELM) lint --strict $(CHART)
test: verify-vendor lint
	HELM=$(HELM) $(PYTHON) -m unittest discover -s tests -v
package: test
	mkdir -p dist
	$(HELM) package $(CHART) --destination dist
images: dependencies
	$(HELM) template litmus $(CHART) | $(PYTHON) scripts/list-images.py
