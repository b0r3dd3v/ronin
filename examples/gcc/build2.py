#!/usr/bin/env python

#
# gcc GTK+ Hello World
#
# build2.py
#
# Source: https://developer.gnome.org/gtk3/stable/gtk-getting-started.html
#
# Requirements:
#
#   Ubuntu: sudo apt install gcc ccache libgtk-3-dev
#
# This adds on build1.py by separating the compile and link phases, which is the recommended setup
# for larger projects.
#

from ronin.cli import cli
from ronin.contexts import new_build_context
from ronin.gcc import GccCompile, GccLink
from ronin.phases import Phase
from ronin.pkg_config import Package
from ronin.projects import Project
from ronin.utils.paths import glob

with new_build_context(output_path_relative='build2') as ctx:

    project = Project('gcc GTK+ Hello World')
    extensions = [Package('gtk+-3.0')]
    
    # Compile
    compile = Phase(GccCompile(),
                    inputs=glob('src/**/*.c'),
                    extensions=extensions)

    # Link
    link = Phase(GccLink(),
                 inputs_from=[compile],
                 extensions=extensions,
                 output='example_1')

    project.phases['compile'] = compile
    project.phases['link'] = link
    
    cli(project)