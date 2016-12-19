# -*- coding: utf-8 -*-
from distutils.core import setup
from Cython.Build import cythonize
from distutils.extension import Extension
from Cython.Distutils import build_ext
import numpy

Ext_modules = [Extension('cy_calculation', ['cy_calculation.pyx'], include_dirs=[numpy.get_include()])]

setup(
    name        = 'cy_calculation app',
    cmdclass    = {'build_ext':build_ext},
    ext_modules = Ext_modules,
)

