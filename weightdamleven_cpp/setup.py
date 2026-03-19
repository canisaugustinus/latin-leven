from setuptools import setup, Extension
import sys
import pybind11

cpp_args = ['/O2', '/std:c++17'] if sys.platform == 'win32' \
           else ['-O3', '-march=native', '-std=c++17']

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