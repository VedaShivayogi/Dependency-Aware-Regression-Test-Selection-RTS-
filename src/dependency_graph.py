from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Set, Optional, Tuple, Any
import networkx as nx

from src.ast_analyzer import (
    FileASTInfo,
    FunctionSymbol,
    ClassSymbol,
    ImportSymbol,
    analyze_repository_ast,
)


@dataclass
class UnresolvedDependency:
    """Records an import or call target that could not be statically resolved."""
    source_module: str
    target_name: str
    source_line: int
    reason: str


class DependencyGraph:
    """Directed graph representing code modules, functions, classes, and test dependencies."""

    def __init__(self, root_path: Path):
        self.root_path = root_path.resolve()
        self.graph = nx.DiGraph()
        self.ast_map: Dict[str, FileASTInfo] = {}
        self.unresolved_dependencies: List[UnresolvedDependency] = []
        self.module_to_file: Dict[str, Path] = {}
        self.file_to_module: Dict[Path, str] = {}

    def build_graph(self, python_files: List[Path]) -> nx.DiGraph:
        """Constructs the dependency graph from parsed AST information."""
        self.graph.clear()
        self.unresolved_dependencies.clear()
        self.ast_map = analyze_repository_ast(python_files, self.root_path)

        # 1. Register module nodes and build mappings
        for mod_name, ast_info in self.ast_map.items():
            self.module_to_file[mod_name] = ast_info.file_path
            self.file_to_module[ast_info.file_path] = mod_name

            mod_node = f"mod:{mod_name}"
            self.graph.add_node(
                mod_node,
                type="module",
                name=mod_name,
                path=str(ast_info.file_path),
                has_syntax_error=ast_info.syntax_error is not None,
                has_reflection=ast_info.has_reflection,
                has_dynamic_imports=ast_info.has_dynamic_imports,
            )

        # 2. Add classes and functions
        for mod_name, ast_info in self.ast_map.items():
            mod_node = f"mod:{mod_name}"

            # Functions in module
            for func in ast_info.functions:
                node_prefix = "test" if func.is_test else "func"
                func_node = f"{node_prefix}:{func.qualified_name}"
                self.graph.add_node(
                    func_node,
                    type="test" if func.is_test else "function",
                    name=func.name,
                    qualified_name=func.qualified_name,
                    path=str(func.file_path),
                    start_line=func.start_line,
                    end_line=func.end_line,
                )
                # Module CONTAINS Function (Consumer: Module, Provider: Function)
                self.graph.add_edge(mod_node, func_node, relation="contains")

            # Classes in module
            for cls in ast_info.classes:
                cls_node = f"class:{cls.qualified_name}"
                self.graph.add_node(
                    cls_node,
                    type="class",
                    name=cls.name,
                    qualified_name=cls.qualified_name,
                    path=str(cls.file_path),
                    start_line=cls.start_line,
                    end_line=cls.end_line,
                )
                self.graph.add_edge(mod_node, cls_node, relation="contains")

                for method in cls.methods:
                    node_prefix = "test" if method.is_test else "func"
                    method_node = f"{node_prefix}:{method.qualified_name}"
                    self.graph.add_node(
                        method_node,
                        type="test" if method.is_test else "function",
                        name=method.name,
                        qualified_name=method.qualified_name,
                        path=str(method.file_path),
                        start_line=method.start_line,
                        end_line=method.end_line,
                    )
                    self.graph.add_edge(cls_node, method_node, relation="contains")

        # 3. Resolve imports (Module -> Target Module)
        for mod_name, ast_info in self.ast_map.items():
            mod_node = f"mod:{mod_name}"
            for imp in ast_info.imports:
                target_mod = self._resolve_import_module(mod_name, imp)
                if target_mod and target_mod in self.ast_map:
                    target_mod_node = f"mod:{target_mod}"
                    # mod_node IMPORTS target_mod_node (mod_node depends on target_mod_node)
                    self.graph.add_edge(mod_node, target_mod_node, relation="imports")
                else:
                    self.unresolved_dependencies.append(UnresolvedDependency(
                        source_module=mod_name,
                        target_name=imp.module or str(imp.imported_name),
                        source_line=imp.line_number,
                        reason="External library or unresolved relative module path"
                    ))

        # 4. Resolve function & test calls
        all_funcs_by_qualname = {}
        all_funcs_by_name = {}

        for n, d in self.graph.nodes(data=True):
            if d.get("type") in {"function", "test"}:
                qual = d.get("qualified_name", "")
                name = d.get("name", "")
                all_funcs_by_qualname[qual] = n
                if name not in all_funcs_by_name:
                    all_funcs_by_name[name] = []
                all_funcs_by_name[name].append(n)

        for mod_name, ast_info in self.ast_map.items():
            all_module_funcs = ast_info.functions + [m for c in ast_info.classes for m in c.methods]
            for func in all_module_funcs:
                node_prefix = "test" if func.is_test else "func"
                func_node = f"{node_prefix}:{func.qualified_name}"

                for call_str in func.calls:
                    target_node = self._resolve_call_target(
                        caller_mod=mod_name,
                        call_str=call_str,
                        ast_info=ast_info,
                        all_funcs_by_qualname=all_funcs_by_qualname,
                        all_funcs_by_name=all_funcs_by_name
                    )
                    if target_node and target_node in self.graph:
                        # func_node CALLS target_node (func_node depends on target_node)
                        self.graph.add_edge(func_node, target_node, relation="calls")

        return self.graph

    def _resolve_import_module(self, current_mod: str, imp: ImportSymbol) -> Optional[str]:
        """Resolves absolute and relative import statements into canonical module names."""
        if not imp.is_relative:
            return imp.module if imp.module in self.ast_map else None

        # Relative import
        parts = current_mod.split(".")
        level = imp.level
        if level > len(parts):
            return None

        base_parts = parts[:-level] if level > 0 else parts
        if imp.module:
            target_mod = ".".join(base_parts + imp.module.split("."))
        else:
            target_mod = ".".join(base_parts)

        if target_mod in self.ast_map:
            return target_mod

        # Check if imported_name is actually a submodule
        if imp.imported_name:
            submod = f"{target_mod}.{imp.imported_name}"
            if submod in self.ast_map:
                return submod

        return None

    def _resolve_call_target(
        self,
        caller_mod: str,
        call_str: str,
        ast_info: FileASTInfo,
        all_funcs_by_qualname: Dict[str, str],
        all_funcs_by_name: Dict[str, List[str]]
    ) -> Optional[str]:
        """Resolves function call target string to node ID."""
        # Check direct qualified match
        direct_qual = f"{caller_mod}.{call_str}"
        if direct_qual in all_funcs_by_qualname:
            return all_funcs_by_qualname[direct_qual]

        # Check imported alias or imported symbol
        for imp in ast_info.imports:
            imp_mod = self._resolve_import_module(caller_mod, imp)
            if imp_mod:
                # e.g., from calc import add -> call_str='add'
                if imp.imported_name and imp.imported_name == call_str:
                    target_qual = f"{imp_mod}.{call_str}"
                    if target_qual in all_funcs_by_qualname:
                        return all_funcs_by_qualname[target_qual]
                # e.g., import calc -> call_str='calc.add'
                alias_or_mod = imp.alias or imp.module
                if alias_or_mod and call_str.startswith(f"{alias_or_mod}."):
                    sub_call = call_str[len(alias_or_mod) + 1:]
                    target_qual = f"{imp_mod}.{sub_call}"
                    if target_qual in all_funcs_by_qualname:
                        return all_funcs_by_qualname[target_qual]

        # Fallback to unique name match if safe
        if call_str in all_funcs_by_name and len(all_funcs_by_name[call_str]) == 1:
            return all_funcs_by_name[call_str][0]

        return None

    def get_dependent_nodes(self, node_id: str) -> Set[str]:
        """
        Finds all nodes that depend on node_id (upstream dependent callers/importers).
        Since edges are directed Consumer -> Provider (e.g. Test -> Function),
        dependents of Provider are found by looking at incoming edges / predecessor reachability.
        """
        if node_id not in self.graph:
            return set()
        
        # Use reverse graph to traverse from Provider to Consumers
        rev_graph = self.graph.reverse(copy=False)
        return set(nx.descendants(rev_graph, node_id))

    def get_dependency_path(self, source_test_node: str, changed_node: str) -> List[str]:
        """Finds shortest path from test node to changed node in the dependency graph."""
        if source_test_node in self.graph and changed_node in self.graph:
            try:
                return nx.shortest_path(self.graph, source_test_node, changed_node)
            except (nx.NetworkXNoPath, nx.NodeNotFound):
                pass
        return []
