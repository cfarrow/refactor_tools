import ast
import glob
import os.path
import re

IMPORT_FROM_PATTERN_TEMPLATE = "from {}(.* import .+)"
IMPORT_PATTERN_TEMPLATE = "import {}(.*)"

# IDEA full pep8 checking
# FIXME Rename relative imports
# FIXME use logging, not __str__


def make_import_regexes(module_name):
    import_from_pattern = IMPORT_FROM_PATTERN_TEMPLATE.format(module_name)
    import_from_regex = re.compile(import_from_pattern)
    import_pattern = IMPORT_PATTERN_TEMPLATE.format(module_name)
    import_regex = re.compile(import_pattern)
    return import_regex, import_from_regex


class ImportCheckerVisitor(ast.NodeVisitor):

    def __init__(self, module_name):
        self.module_name = module_name
        self.import_found = False

    def visit_ImportFrom(self, node):
        # Relative imports have None as the module attribute
        if node.module is None:
            return
        if node.module.startswith(self.module_name):
            self.import_found = True

    def visit_Import(self, node):
        module_names = set(name.name for name in node.names)
        if any(module_name.startswith(self.module_name) for module_name in
                module_names):
            self.import_found = True


def imports_module(path, module_name):
    """
    Determine one module, specified by path, imports another.

    """
    with open(path, 'r') as infile:
        source = infile.read()

    root = ast.parse(source)
    visitor = ImportCheckerVisitor(module_name)
    visitor.visit(root)
    return visitor.import_found


class BaseImportWalker(object):

    def __init__(self, module_name):
        self.module_name = module_name
        self.path = None
        self.globs = ['*.py', '*.enaml', '*.rst']

    def walk(self, path):
        """
        Walk a directory searching for a specific module import.

        """
        self.path = path
        os.path.walk(path, self._visit_path, None)

    def _visit_path(self, modules, dirname, _):
        glob_patterns = (os.path.join(dirname, glob_suffix)
                         for glob_suffix in self.globs)
        for glob_pattern in glob_patterns:
            module_paths = glob.glob(glob_pattern)
            for module_path in module_paths:
                self._visit_module(module_path)

    def _visit_module(self, module_path):
        """
        Visit a module. This must be overloaded.

        """
        raise NotImplementedError


class CollectingImportWalker(BaseImportWalker):

    def __init__(self, module_name):
        super(CollectingImportWalker, self).__init__(module_name)
        self.found_modules = set()

    def __str__(self):
        paths = sorted(self.found_modules)
        paths = (os.path.relpath(module_path, self.path) for module_path in
                    self.found_modules)
        output = "\n".join(sorted(paths))
        return output


class ImportFinderAST(CollectingImportWalker):

    def _visit_module(self, module_path):
        if imports_module(module_path, self.module_name):
            self.found_modules.add(module_path)


class ImportFinderRE(CollectingImportWalker):

    def __init__(self, module_name):
        super(ImportFinderRE, self).__init__(module_name)
        self.import_regex, self.import_from_regex = \
                make_import_regexes(module_name)

    def _visit_module(self, module_path):

        with open(module_path, 'r') as infile:
            source = infile.read()

        if self.import_regex.search(source):
            self.found_modules.add(module_path)
        elif self.import_from_regex.search(source):
            self.found_modules.add(module_path)


class ImportRenamer(BaseImportWalker):
    """Rename imports from a move.

    This does not handle relative imports.

    """

    def __init__(self, module_name, new_module_name):
        super(ImportRenamer, self).__init__(module_name)
        self.new_module_name = new_module_name
        self.import_regex, self.import_from_regex = \
                make_import_regexes(module_name)
        self.import_from_repl = r"from {}\1".format(new_module_name)
        self.import_repl = r"import {}\1".format(new_module_name)
        self.output = []

    def _visit_module(self, module_path):

        with open(module_path, 'r') as infile:
            source = infile.read()

        new_source = self._check_import(module_path, source)
        if new_source is None:
            new_source = self._check_import_from(module_path, source)

        if new_source is not None:
            with open(module_path, 'w') as outfile:
                outfile.write(new_source)

    def _check_import(self, module_path, source):
        """
        Check for import statement in source

        """
        return self._check(module_path, source,
                self.import_regex, self.import_repl)

    def _check_import_from(self, module_path, source):
        """
        Check for import-from statement in source

        """
        return self._check(module_path, source,
                self.import_from_regex, self.import_from_repl)

    def _check(self, module_path, source, regex, repl):
        output = module_path

        if not regex.search(source):
            return

        # Check for pep8
        if self._meets_pep8(source, regex, repl):
            output = module_path
        else:
            output = "pep8: {}".format(module_path)

        self.output.append(output)

        return regex.sub(repl, source)

    def _meets_pep8(self, source, regex, repl):
        """
        Checks whether modified imports will meet pep8.

        This assumes matches have been found.

        Returns True, False or None if there are no matches.

        """
        retval = None
        for match in regex.finditer(source):
            retval = True
            new_line = match.expand(repl)
            if len(new_line) > 79:
                retval = False
                break

        return retval

    def __str__(self):
        return "\n".join(self.output)


def find_imports(path, module_name):
    """
    Find imports in python modules under path that import the named module.

    """
    finder = ImportFinderRE(module_name)
    finder.walk(path)
    print finder


def rename_imports(path, module_name, new_module_name):
    """
    Rename imports in python modules under path that import the named module.

    """
    renamer = ImportRenamer(module_name, new_module_name)
    renamer.walk(path)
    print renamer


def find_imports_main():
    import sys
    find_imports(*sys.argv[1:3])


def rename_imports_main():
    import sys
    rename_imports(*sys.argv[1:4])


if __name__ == "__main__":

    find_imports_main()
