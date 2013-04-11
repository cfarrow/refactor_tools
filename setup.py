from setuptools import setup, find_packages

setup(
    name='refactor_tools',
    version='0.0.1',
    description='tools for refactoring python code',
    packages=find_packages(),
    entry_points=dict(
        console_scripts=[
            'rename-imports = refactor_tools.import_refactor_helper:rename_imports_main',
            'find-imports = refactor_tools.import_refactor_helper:find_imports_main',
            ],
    ),
)
