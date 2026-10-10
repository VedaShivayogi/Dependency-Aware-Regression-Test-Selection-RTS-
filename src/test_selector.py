from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Set, Optional, Tuple, Any

from src.change_detector import ChangeDetectionResult, ChangedSymbol
from src.dependency_graph import DependencyGraph
from src.test_discovery import TestItem


@dataclass
class SelectionRationale:
    """Detailed justification for test selection decision."""
    selection_mode: str
    selected_test_ids: List[str] = field(default_factory=list)
    explanations: Dict[str, str] = field(default_factory=dict)
    dependency_paths: Dict[str, List[str]] = field(default_factory=dict)
    changed_symbols: List[str] = field(default_factory=list)
    uncertainty_warnings: List[str] = field(default_factory=list)
    is_fallback_full_suite: bool = False


class TestSelector:
    """Engine for selecting tests using full suite, changed-file, or dependency-aware algorithms."""
    __test__ = False

    def __init__(self, dep_graph: DependencyGraph, all_tests: List[TestItem]):
        self.dep_graph = dep_graph
        self.all_tests = all_tests
        self.test_id_to_item: Dict[str, TestItem] = {t.test_id: t for t in all_tests}

    def select_tests(
        self,
        mode: str,
        changes: ChangeDetectionResult,
        conservative: bool = True
    ) -> SelectionRationale:
        """Selects tests based on specified mode ('full', 'changed_file', or 'dependency_aware')."""
        mode = mode.lower().strip()
        if mode == "full":
            return self.select_full_suite()
        elif mode == "changed_file":
            return self.select_changed_file_baseline(changes)
        elif mode == "dependency_aware":
            return self.select_dependency_aware(changes, conservative=conservative)
        else:
            raise ValueError(f"Unknown test selection mode: '{mode}'. Must be 'full', 'changed_file', or 'dependency_aware'.")

    def select_full_suite(self) -> SelectionRationale:
        """Mode 1: Full Suite baseline (selects all discovered tests)."""
        test_ids = [t.test_id for t in self.all_tests]
        explanations = {t_id: "Full Suite Mode: Executing all available repository tests." for t_id in test_ids}
        return SelectionRationale(
            selection_mode="full",
            selected_test_ids=test_ids,
            explanations=explanations,
            changed_symbols=[],
            uncertainty_warnings=[]
        )

    def select_changed_file_baseline(self, changes: ChangeDetectionResult) -> SelectionRationale:
        """Mode 2: Changed-File Baseline (heuristic file name matching and direct imports)."""
        changed_file_names = {f.name.lower() for f in changes.modified_files + changes.added_files}
        changed_stems = {f.stem.lower() for f in changes.modified_files + changes.added_files}

        selected_ids: Set[str] = set()
        explanations: Dict[str, str] = {}

        for test in self.all_tests:
            test_file_name = test.file_path.name.lower()
            test_file_stem = test.file_path.stem.lower()

            # Rule A: Changed file is the test file itself
            if test_file_name in changed_file_names:
                selected_ids.add(test.test_id)
                explanations[test.test_id] = f"Direct match: Changed file is the test file '{test.file_path.name}'."
                continue

            # Rule B: Name convention heuristic (e.g., cart.py changed -> test_cart.py)
            for stem in changed_stems:
                if f"test_{stem}" in test_file_stem or f"{stem}_test" in test_file_stem:
                    selected_ids.add(test.test_id)
                    explanations[test.test_id] = f"Name heuristic match: Changed file stem '{stem}' matches test file '{test.file_path.name}'."
                    break

        selected_list = sorted(list(selected_ids))
        uncertainty = []
        if not selected_list and (changes.modified_files or changes.added_files):
            uncertainty.append("Changed-File Baseline found no tests matching changed file names.")

        return SelectionRationale(
            selection_mode="changed_file",
            selected_test_ids=selected_list,
            explanations=explanations,
            changed_symbols=[f.name for f in changes.modified_files + changes.added_files],
            uncertainty_warnings=uncertainty
        )

    def select_dependency_aware(
        self,
        changes: ChangeDetectionResult,
        conservative: bool = True
    ) -> SelectionRationale:
        """Mode 3: Dependency-Aware Test Selection using graph traversal."""
        selected_ids: Set[str] = set()
        explanations: Dict[str, str] = {}
        dep_paths: Dict[str, List[str]] = {}
        uncertainty_warnings: List[str] = []

        changed_symbol_names = [s.symbol_name for s in changes.changed_symbols]

        if changes.is_uncertain and changes.warning_message:
            uncertainty_warnings.append(changes.warning_message)

        # Check for unresolved dependencies in graph
        if self.dep_graph.unresolved_dependencies:
            uncertainty_warnings.append(
                f"Graph contains {len(self.dep_graph.unresolved_dependencies)} unresolved external/dynamic imports."
            )

        # Identify graph nodes for changed symbols
        target_changed_nodes: Set[str] = set()
        for sym in changes.changed_symbols:
            if sym.symbol_type == "function":
                # Look for func: or test: nodes matching sym.symbol_name
                for node_id, data in self.dep_graph.graph.nodes(data=True):
                    if data.get("qualified_name") == sym.symbol_name:
                        target_changed_nodes.add(node_id)
            elif sym.symbol_type in ("module", "class"):
                mod_node = f"mod:{sym.symbol_name}"
                if mod_node in self.dep_graph.graph:
                    target_changed_nodes.add(mod_node)

        # Also map changed file paths directly to module nodes
        for changed_file in changes.modified_files + changes.added_files:
            mod_name = self.dep_graph.file_to_module.get(changed_file.resolve())
            if mod_name:
                mod_node = f"mod:{mod_name}"
                if mod_node in self.dep_graph.graph:
                    target_changed_nodes.add(mod_node)

        # Traversal: For each target changed node, find dependent callers & tests
        for chg_node in target_changed_nodes:
            # Get upstream dependent nodes
            dependents = self.dep_graph.get_dependent_nodes(chg_node)
            dependents.add(chg_node)

            for dep_node in dependents:
                node_data = self.dep_graph.graph.nodes.get(dep_node, {})
                # If dep_node is a test node or test function
                if node_data.get("type") == "test":
                    qual = node_data.get("qualified_name")
                    # Match qual to discovered test items
                    for test_item in self.all_tests:
                        if test_item.func_name in qual or (test_item.class_name and test_item.class_name in qual):
                            selected_ids.add(test_item.test_id)
                            path = self.dep_graph.get_dependency_path(dep_node, chg_node)
                            dep_paths[test_item.test_id] = path
                            explanations[test_item.test_id] = (
                                f"Dependency path traced: {dep_node} -> ... -> {chg_node} ({chg_node.split(':')[-1]} changed)."
                            )

        # Conservative mode expansion: If static resolution was uncertain or wildcard imports used, expand to file level tests
        if conservative and (uncertainty_warnings or not selected_ids) and (changes.modified_files or changes.added_files):
            uncertainty_warnings.append("Conservative Mode active: Expanding selection due to unresolved dependencies or empty selection.")
            for test_item in self.all_tests:
                if test_item.test_id not in selected_ids:
                    # Check if test module imports any changed module
                    for chg_file in changes.modified_files + changes.added_files:
                        chg_mod = self.dep_graph.file_to_module.get(chg_file.resolve())
                        if chg_mod:
                            test_mod_node = f"mod:{test_item.module_name}"
                            chg_mod_node = f"mod:{chg_mod}"
                            if self.dep_graph.graph.has_edge(test_mod_node, chg_mod_node):
                                selected_ids.add(test_item.test_id)
                                explanations[test_item.test_id] = f"Conservative Expansion: Test module '{test_item.module_name}' imports changed module '{chg_mod}'."

        selected_list = sorted(list(selected_ids))
        is_fallback = False

        # Fallback safeguard: If still zero tests selected when files changed, offer full suite fallback rationale
        if not selected_list and (changes.modified_files or changes.added_files):
            uncertainty_warnings.append("No tests were mapped by static analysis. Falling back to Full Suite execution to ensure zero missed regressions.")
            selected_list = [t.test_id for t in self.all_tests]
            is_fallback = True
            for t_id in selected_list:
                explanations[t_id] = "Fallback Selection: Executing full suite because static dependency mapping yielded no direct tests."

        return SelectionRationale(
            selection_mode="dependency_aware",
            selected_test_ids=selected_list,
            explanations=explanations,
            dependency_paths=dep_paths,
            changed_symbols=changed_symbol_names,
            uncertainty_warnings=uncertainty_warnings,
            is_fallback_full_suite=is_fallback
        )
