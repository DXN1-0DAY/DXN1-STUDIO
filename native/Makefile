# dxn3 native — C++23 core. Two binaries, zero dependencies beyond libstdc++.
#   make              -> build/dxn3-native   (the studio: play + inspect)
#   make              -> build/dxn3-selftest (engine assertions)
#   make test         -> build + run selftest
#   make run SCENE=…  -> run a scene from the repo root
CXX ?= g++
CXXFLAGS ?= -std=c++23 -O2 -Wall -Wextra -Wpedantic
BUILD := build

.PHONY: all test run clean

all: $(BUILD)/dxn3-native $(BUILD)/dxn3-selftest

$(BUILD)/dxn3-native: src/main.cpp src/tui.cpp src/spark.cpp src/spark.hpp src/tui.hpp src/json.hpp
	@mkdir -p $(BUILD)
	$(CXX) $(CXXFLAGS) src/main.cpp src/tui.cpp src/spark.cpp -o $@

$(BUILD)/dxn3-selftest: src/selftest.cpp src/spark.cpp src/spark.hpp src/json.hpp
	@mkdir -p $(BUILD)
	$(CXX) $(CXXFLAGS) src/selftest.cpp src/spark.cpp -o $@

test: all
	$(BUILD)/dxn3-selftest

run: $(BUILD)/dxn3-native
	$(BUILD)/dxn3-native --scene $(SCENE)

clean:
	rm -rf $(BUILD)
