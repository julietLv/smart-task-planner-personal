import ast
import sys
from pathlib import Path
from collections import defaultdict

class TupleReturnChecker(ast.NodeVisitor):
    def __init__(self, filename):
        self.filename = filename
        self.func_return_tuple = set()          # 返回元组的函数名
        self.calls_to_check = []                # (node, func_name) 调用节点
        self.current_function = None

    def visit_FunctionDef(self, node):
        old_func = self.current_function
        self.current_function = node.name
        self.generic_visit(node)
        self.current_function = old_func

    def visit_Return(self, node):
        # 如果返回的值是一个元组字面量 (a, b) 或 (a, b, c)
        if node.value and isinstance(node.value, ast.Tuple):
            self.func_return_tuple.add(self.current_function)
        # 注意：如果返回的是变量名（可能指向元组），静态分析无法确定，这里忽略
        self.generic_visit(node)

    def visit_Assign(self, node):
        # 赋值语句: target = call(...)
        if isinstance(node.value, ast.Call) and isinstance(node.value.func, ast.Name):
            func_name = node.value.func.id
            # 如果赋值目标是单个变量（不是元组解包），才可能有问题
            if len(node.targets) == 1 and isinstance(node.targets[0], ast.Name):
                self.calls_to_check.append((node.value, func_name))
        self.generic_visit(node)

    def visit_Expr(self, node):
        # 处理表达式语句中的调用，比如 f() + 1
        if isinstance(node.value, ast.Call) and isinstance(node.value.func, ast.Name):
            func_name = node.value.func.id
            # 检查父节点是否是二元运算（加法、除法等）
            parent = getattr(node, 'parent', None)
            if parent and isinstance(parent, ast.BinOp):
                if parent.left is node.value or parent.right is node.value:
                    self.calls_to_check.append((node.value, func_name))
        self.generic_visit(node)

    def report(self):
        issues = []
        for call_node, func_name in self.calls_to_check:
            if func_name in self.func_return_tuple:
                line_no = call_node.lineno
                col = call_node.col_offset
                code_line = self._get_line(line_no)
                issues.append((line_no, col, func_name, code_line.strip()))
        return issues

    def _get_line(self, lineno):
        try:
            with open(self.filename, 'r', encoding='utf-8') as f:
                lines = f.readlines()
                if lineno <= len(lines):
                    return lines[lineno-1]
        except:
            pass
        return ""

def set_parents(node, parent=None):
    """为每个节点设置 parent 属性，方便向上遍历"""
    node.parent = parent
    for child in ast.iter_child_nodes(node):
        set_parents(child, node)

def scan_file(filepath):
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            source = f.read()
        tree = ast.parse(source, filename=str(filepath))
        set_parents(tree)
        checker = TupleReturnChecker(str(filepath))
        checker.visit(tree)
        return checker.report()
    except SyntaxError as e:
        # 忽略语法错误文件（比如模板文件）
        print(f"跳过语法错误文件 {filepath}: {e}", file=sys.stderr)
        return []
    except Exception as e:
        print(f"处理文件 {filepath} 时出错: {e}", file=sys.stderr)
        return []

def main():
    if len(sys.argv) < 2:
        print("用法: python check_unpack.py <目录或文件>")
        sys.exit(1)
    target = sys.argv[1]
    path = Path(target)
    all_issues = []

    if path.is_file():
        py_files = [path]
    else:
        py_files = path.rglob('*.py')

    for py_file in py_files:
        # 跳过常见的非代码文件
        if py_file.name.startswith('test_') or 'venv' in str(py_file) or '__pycache__' in str(py_file):
            continue
        issues = scan_file(py_file)
        for line, col, func, code in issues:
            all_issues.append(f"{py_file}:{line}:{col}: 调用函数 '{func}' 返回元组，但未解包: {code}")

    if all_issues:
        print("发现以下可能的问题：")
        for issue in all_issues:
            print(issue)
    else:
        print("未检测到明显的未解包元组调用问题。")

if __name__ == '__main__':
    main()