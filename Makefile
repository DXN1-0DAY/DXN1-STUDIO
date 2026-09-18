# DXN1 STUDIO — DS3
# the studio is one command away

.PHONY: serve gates version help

help:        ## list targets
	@grep -E '^[a-z-]+:.*##' $(MAKEFILE_LIST) | awk -F':.*## ' '{printf "  %-10s %s\n", $$1, $$2}'

serve:       ## serve the editor at http://localhost:8080/ui/ — scenes ride ../scenes/
	python3 -m http.server 8080 --bind 127.0.0.1

gates:       ## the law — every gate plus the probe walkers, must end ALL GREEN
	bash scripts/gates.sh

version:     ## print the current version
	@cat VERSION
