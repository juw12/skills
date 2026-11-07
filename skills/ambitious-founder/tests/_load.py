"""Load a bundled tool (flat layout: tools/ and examples/ in this skill folder)."""

import importlib.util
import os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TOOLS_DIR = os.path.join(ROOT, "tools")
EXAMPLES_DIR = os.path.join(ROOT, "examples")

# Original repo kept examples next to each skill; map those names here.
EXAMPLE_NAMES = {
    "example.json": "numbers.example.json",
}


def load(folder, name):
    path = os.path.join(TOOLS_DIR, name + ".py")
    spec = importlib.util.spec_from_file_location("founder_" + name, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def example(folder, name):
    return os.path.join(EXAMPLES_DIR, EXAMPLE_NAMES.get(name, name))
