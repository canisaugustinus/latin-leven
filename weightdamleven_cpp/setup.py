from setuptools import setup, Extension
import pybind11

cpp_args = []

sfc_module = Extension(
    'weightdamleven',
    sources=['module.cpp'],
    include_dirs=[pybind11.get_include()],
    language='c++',
    extra_compile_args=cpp_args,
)

setup(
    name='weightdamleven',
    version='1.1',
    description='Keyboard-Weighted Damerau-Levenshtein Calculations. Implemented as a C++ extension (PyBind11).',
    ext_modules=[sfc_module],
)