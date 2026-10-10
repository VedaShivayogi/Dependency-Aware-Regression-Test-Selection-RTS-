import ast
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Set, Optional, Any, Tuple


@dataclass
class FunctionSymbol:
    """Represents a parsed function or method symbol."""
    name: str
    qualified_name: str
    file_path: Path
    start_line: int
    end_line: int
    is_method: bool = False
    class_name: Optional[str] = None
    is_test: bool = False
    calls: List[str] = field(default_factory=list)
    docstring: Optional[str] = None


@dataclass
class ClassSymbol:
    """Represents a parsed class symbol."""
    name: str
    qualified_name: str
    file_path: Path
    start_line: int
    end_line: int
    methods: List[FunctionSymbol] = field(default_factory=list)
    base_classes: List[str] = field(default_factory=list)


@dataclass
class ImportSymbol:
    """Represents an imported module or symbol."""
    module: str
    imported_name: Optional[str] = None
    alias: Optional[str] = None
    is_relative: bool = False
    level: int = 0
    line_number: int = 1


@dataclass
class SyntaxErrorInfo:
    """Stores information on files that failed AST parsing."""
    file_path: Path
    line: int
    offset: int
    message: str


@dataclass
class FileASTInfo:
    """Extracted AST details for a single Python source file."""
    file_path: Path
    module_name: str
    imports: List[ImportSymbol] = field(default_factory=list)
    functions: List[FunctionSymbol] = field(default_factory=list)
    classes: List[ClassSymbol] = field(default_factory=list)
    has_dynamic_imports: bool = False
    has_reflection: bool = False
    wildcard_imports: List[str] = field(default_factory=list)
    syntax_error: Optional[SyntaxErrorInfo] = None


class ASTAnalyzerVisitor(ast.NodeVisitor):
    """AST visitor to extract imports, classes, functions, and call graphs."""

    def __init__(self, file_path: Path, module_name: str):
        self.file_path = file_path
        self.module_name = module_name
        self.imports: List[ImportSymbol] = []
        self.functions: List[FunctionSymbol] = []
        self.classes: List[ClassSymbol] = []
        self.has_dynamic_imports = False
        self.has_reflection = False
        self.wildcard_imports: List[str] = []

        self._current_class: Optional[str] = None
        self._current_function: Optional[FunctionSymbol] = None

    def visit_Import(self, node: ast.Import):
        for alias in node.names:
            self.imports.append(ImportSymbol(
                module=alias.name,
                alias=alias.asname,
                line_number=node.lineno
            ))
        self.generic_visit(node)

    def visit_ImportFrom(self, node: ast.ImportFrom):
        module = node.module or ""
        level = node.level or 0
        is_relative = level > 0

        for alias in node.names:
            if alias.name == "*":
                self.wildcard_imports.append(module)
            self.imports.append(ImportSymbol(
                module=module,
                imported_name=alias.name if alias.name != "*" else None,
                alias=alias.asname,
                is_relative=is_relative,
                level=level,
                line_number=node.lineno
            ))
        self.generic_visit(node)

    def visit_ClassDef(self, node: ast.ClassDef):
        prev_class = self._current_class
        self._current_class = node.name

        base_classes = []
        for base in node.bases:
            if isinstance(base, ast.Name):
                base_classes.append(base.id)
            elif isinstance(base, ast.Attribute):
                base_classes.append(f"{base.value.id if isinstance(base.value, ast.Name) else 'Expr'}.{base.attr}")

        class_symbol = ClassSymbol(
            name=node.name,
            qualified_name=f"{self.module_name}.{node.name}",
            file_path=self.file_path,
            start_line=node.lineno,
            end_line=getattr(node, 'end_lineno', node.lineno),
            base_classes=base_classes
        )

        self.classes.append(class_symbol)
        self.generic_visit(node)
        self._current_class = prev_class

    def visit_FunctionDef(self, node: ast.FunctionDef):
        self._visit_func_node(node)

    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef):
        self._visit_func_node(node)

    def _visit_func_node(self, node):
        is_method = self._current_class is not None
        is_test = node.name.startswith("test_") or "test" in self.file_path.name.lower()
        
        qual_name = (f"{self.module_name}.{self._current_class}.{node.name}" 
                     if is_method else f"{self.module_name}.{node.name}")

        func_symbol = FunctionSymbol(
            name=node.name,
            qualified_name=qual_name,
            file_path=self.file_path,
            start_line=node.lineno,
            end_line=getattr(node, 'end_lineno', node.lineno),
            is_method=is_method,
            class_name=self._current_class,
            is_test=is_test,
            docstring=ast.get_docstring(node)
        )

        prev_func = self._current_function
        self._current_function = func_symbol

        # Parse calls inside function
        self.generic_visit(node)

        if is_method and self.classes:
            # Add to current class methods
            for c in self.classes:
                if c.name == self._current_class:
                    c.methods.append(func_symbol)
                    break
        else:
            self.functions.append(func_symbol)

        self._current_function = prev_func

    def visit_Call(self, node: ast.Call):
        # Extract call identifier
        call_name = None
        if isinstance(node.func, ast.Name):
            call_name = node.func.id
            if call_name in {"getattr", "setattr", "__import__", "eval", "exec"}:
                self.has_reflection = True
        elif isinstance(node.func, ast.Attribute):
            val_id = node.func.value.id if isinstance(node.func.value, ast.Name) else ""
            call_name = f"{val_id}.{node.func.attr}" if val_id else node.func.attr

        if call_name and self._current_function:
            self._current_function.calls.append(call_name)

        if isinstance(node.func, ast.Name) and node.func.id in {"__import__", "importlib.import_module"}:
            self.has_dynamic_imports = True

        self.generic_visit(node)


def analyze_python_file(file_path: Path, root_path: Path) -> FileASTInfo:
    """Parses a single Python file into FileASTInfo."""
    file_path = file_path.resolve()
    root_path = root_path.resolve()

    try:
        rel_path = file_path.relative_to(root_path)
        module_name = ".".join(rel_path.with_suffix("").parts)
    except ValueError:
        module_name = file_path.stem

    try:
        content = file_path.read_text(encoding="utf-8", errors="replace")
        parsed_ast = ast.parse(content, filename=str(file_path))
    except SyntaxError as se:
        return FileASTInfo(
            file_path=file_path,
            module_name=module_name,
            syntax_error=SyntaxErrorInfo(
                file_path=file_path,
                line=se.lineno or 1,
                offset=se.offset or 1,
                message=se.msg or "Syntax error during AST parsing"
            )
        )
    except Exception as e:
        return FileASTInfo(
            file_path=file_path,
            module_name=module_name,
            syntax_error=SyntaxErrorInfo(
                file_path=file_path,
                line=1,
                offset=1,
                message=f"Failed to read/parse file: {str(e)}"
            )
        )

    visitor = ASTAnalyzerVisitor(file_path, module_name)
    visitor.visit(parsed_ast)

    return FileASTInfo(
        file_path=file_path,
        module_name=module_name,
        imports=visitor.imports,
        functions=visitor.functions,
        classes=visitor.classes,
        has_dynamic_imports=visitor.has_dynamic_imports,
        has_reflection=visitor.has_reflection,
        wildcard_imports=visitor.wildcard_imports
    )


def analyze_repository_ast(python_files: List[Path], root_path: Path) -> Dict[str, FileASTInfo]:
    """Analyzes all Python files in a repository and returns module mapping."""
    ast_map: Dict[str, FileASTInfo] = {}
    for path in python_files:
        info = analyze_python_file(path, root_path)
        ast_map[info.module_name] = info
    return ast_map
