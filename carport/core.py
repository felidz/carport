# AUTOGENERATED! DO NOT EDIT! File to edit: ../nbs/api/01-core.ipynb.

# %% auto 0
__all__ = ['module2path', 'path2module', 'imps_from_file', 'get_imps', 'ImportGraph']

# %% ../nbs/api/01-core.ipynb 5
import ast 
from pathlib import Path 


def module2path(mod_name: str, root: str='.') -> Path: 
    return root/Path(*mod_name.split('.')).with_suffix('.py')

def path2module(path: str, root: str='.') -> str: 
    def str2abs(p): return Path(p).absolute()
    rel_path = str2abs(path).relative_to(str2abs(root))
    return '.'.join(rel_path.with_suffix("").parts)


# %% ../nbs/api/01-core.ipynb 6
def psplit(path: str, sep: str='.') -> list: 
    p = path.split(sep)
    return [sep.join(p[: i+1]) for i, _ in enumerate(p)]

# TODO: imports in __inin__.py
def del_init(mod_name: str) -> str: 
    if mod_name.endswith(".__init__") : 
        return mod_name.replace('.__init__', '') 
    return mod_name 
    
def add_init(mod_name: str) -> str: 
    if mod_name.endswith(".__init__"): 
        return mod_name 
    return f"{mod_name}.__init__"


# %% ../nbs/api/01-core.ipynb 7
def imps_from_file(path: Path, root: str='.') -> set: 
    code = path.read_text(encoding="utf8")
    mod_ast = ast.parse(source=code, filename=path)
    imps = set()
    for node in ast.walk(mod_ast): 
        # parse imports
        if isinstance(node, ast.Import): 
            for n_ast in node.names: 
                imported = (None, n_ast.name, n_ast.asname, None)
        elif isinstance(node, ast.ImportFrom): 
            # display(ast.dump(node))
            for n_ast in node.names: 
                imported = (node.module, n_ast.name, n_ast.asname, node.level)
        else: 
            continue   
        # translate (where, imported_name, as_name, level)
        where, imported_name, _, level = imported
        if level is None: 
            imp = imported_name
        elif level == 0: 
            imp = f"{where}.{imported_name}"
        else: 
            pa_mod = path2module(Path(*path.parts[: -level]), root)
            imp = f"{pa_mod}.{where}.{imported_name}"
        imps.add(imp)
    return imps


# %% ../nbs/api/01-core.ipynb 8
def get_imps(
    root: str='.', # directory where to look for import structure
    project: str='', # name of concerned project module 
    agg_external: bool = True, # whether to aggregate external imports by subsuming descendant modules
    agg_internal: bool = True  # whether to aggregate internal imports by subsuming non-modular leaves
    ): 
    mod2path = {}
    mod2imp_in, mod2imp_ex = {}, {}
    mod2imppath_in = {}  # todo: mod2imppath_ex 
    root = Path(root).absolute()
    for path in (root/project).rglob("*.py"): 
        mod = path2module(path, root)
        imps = imps_from_file(path, root) 
        mod2path[mod] = path
        for imp in imps: 
            imp_root = imp.split('.')[0]  # snake root 
            if imp_root == project: # i.e., imported module is an internal module
                if agg_internal: 
                    imp_path = module2path(imp, root)
                    imp = imp if imp_path.exists() else imp.rsplit('.', 1)[0] 
                mod2imp_in.setdefault(mod, set()).add(imp)
                mod2imppath_in.setdefault(mod, set()).add(imp_path)
            else: 
                imp = imp_root if agg_external else imp
                mod2imp_ex.setdefault(mod, set()).add(imp) 
    return dict(
        mod2path=mod2path,
        mod2imp_in=mod2imp_in, 
        mod2imp_ex=mod2imp_ex, 
        mod2imppath_in=mod2imppath_in,
    )


# %% ../nbs/api/01-core.ipynb 9
class ImportGraph: 
    def __init__(self, root: str='.', project: str='', **kwargs): 
        for k, v in get_imps(root, project, **kwargs).items(): 
            setattr(self, k, v)
        self._edges = [
            *[(fr, to, {'type': 'internal'}) for to, frs in self.mod2imp_in.items() for fr in frs],
            *[(fr, to, {'type': 'external'}) for to, frs in self.mod2imp_ex.items() for fr in frs],
            ]
        self.edges = [(fr, to) for fr, to, data in self._edges]
        self.nodes = sorted(set().union(*self.edges))
    
    def to_nx(self, ignore_nodes=[], **kw): 
        import networkx as nx
        
        g = nx.MultiDiGraph(self.edges)
        g.remove_nodes_from(ignore_nodes)
        return g
    
    def to_dot(self, path=None, **kw): 
        """ See networkx [drawing module](https://networkx.org/documentation/stable/reference/drawing.html).
        """
        import networkx as nx
        from io import StringIO
        
        string_io = StringIO() 
        g = self.to_nx(**kw)
        nx.nx_pydot.write_dot(g, path or string_io) 
        return string_io.getvalue()
    
    def to_d2(self, ignore_nodes=[], **kw): 
        """ Alternatives: [`py_d2`](https://github.com/MrBlenny/py-d2) may be a better way to do this.
        """
        # 
        e_string = '\n'.join({f"{fr} -> {to}" for fr, to in self.edges})
        
        deletes_hooks = '\n'.join(f"{i}: null" for i in ignore_nodes) if ignore_nodes else ""
        options = '''
        vars: { 
            d2-config: { 
                layout-engine: elk 
                } 
            }
        direction: right
        **.style.border-radius: 99
        *.style.font: mono
        '''
        # theme-id: 200
        d2_string = f"{options}\n{e_string}\n{deletes_hooks}"
        return  d2_string

    def draw_dot(self, **kw): 
        from carport.vis import dot2graph
        dot = self.to_dot(**kw)
        return dot2graph(dot)
    
    def draw_d2(self, app='kroki', **kw): 
        from carport.vis import d22graph
        d2 = self.to_d2(**kw) 
        return d22graph(d2, app=app)
