# Copyright 2016-2018 Tal Liron
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from ..executors import ExecutorWithArguments
from ..contexts import current_context
from ..extensions import Extension
from ..projects import Project
from ..ninja import pathify
from ..utils.platform import which
from ..utils.types import verify_type
import os


DEFAULT_JAVAC_COMMAND = 'javac'
DEFAULT_JAR_COMMAND = 'jar'


def configure_java(javac_command=None, jar_command=None):
    """
    Configures the current context's `Java <https://www.oracle.com/java/>`__ support.
    
    :param javac_command: ``javac`` command; defaults to "javac"
    :type javac_command: basestring or ~types.FunctionType
    :param jar_command: ``jar`` command; defaults to "jar"
    :type jar_command: basestring or ~types.FunctionType
    """
    
    with current_context(False) as ctx:
        ctx.java.javac_command = javac_command or DEFAULT_JAVAC_COMMAND
        ctx.java.jar_command = jar_command or DEFAULT_JAR_COMMAND


class JavaCompile(ExecutorWithArguments):
    """
    `Java <https://www.oracle.com/java/>`__ compile executor.
    
    The phase inputs are ".java" source files. The phase outputs are ".class" files.
    """
    
    def __init__(self, command=None, classpath=[]):
        """
        :param command: ``javac`` command; defaults to the context's ``java.javac_command``
        :type command: basestring or ~types.FunctionType
        :param classpath: initial classpath
        :type classpath: [:obj:`basestring` or :obj:`~types.FunctionType`]
        """
        
        super(JavaCompile, self).__init__()
        self.command = lambda ctx: which(ctx.fallback(command, 'java.javac_command',
                                                      DEFAULT_JAVAC_COMMAND))
        self.classpath = classpath or []
        self.output_type = 'object'
        self.output_extension = 'class'
        self.add_argument_unfiltered('$in')
        self.hooks.append(_debug_hook)
        self.hooks.append(_compile_hook)
        self.hooks.append(_classpath_hook)

    def enable_debug(self):
        self.add_argument('-g')
    
    def add_classpath(self, value):
        self.classpath.append(value)


class Jar(ExecutorWithArguments):
    """
    `Java <https://www.oracle.com/java/>`__ Jar creation executor.

    The phase inputs are ".class" files. The phase output is a ".jar" file.
    """
    
    def __init__(self, command=None, manifest=None):
        """
        :param command: ``jar`` command; defaults to the context's ``java.jar_command``
        :type command: basestring or ~types.FunctionType
        :param manifest: absolute path to manifest file
        :type manifest: basestring or ~types.FunctionType
        """
        
        super(Jar, self).__init__()
        self.command = lambda ctx: which(ctx.fallback(command, 'java.jar_command',
                                                      DEFAULT_JAR_COMMAND))
        self.command_types = ['java_jar']
        self.output_type = 'binary'
        self.output_extension = 'jar'
        if manifest:
            self.add_argument_unfiltered('cfm')
            self.add_argument_unfiltered('$out')
            self.add_argument(manifest)
        else:
            self.add_argument_unfiltered('cf')
            self.add_argument_unfiltered('$out')
    
    def store_only(self):
        self.add_argument('-0')

    def preserve_paths(self):
        self.add_argument('-P')
    
    def disable_manifest(self):
        self.add_argument('-M')


class JavaClasses(Extension):
    """
    `Java <https://www.oracle.com/java/>`__ classes generated by another phase.
    
    Usable only with a :class:`Jar` executor.
    """
    
    def __init__(self, project, phase_name):
        """
        :param project: project
        :type project: ~ronin.projects.Project
        :param phase_name: phase name in project
        :type phase_name: basestring or ~types.FunctionType
        """
        
        super(JavaClasses, self).__init__()
        verify_type(project, Project)
        self._project = project
        self._phase_name = phase_name

    def apply_to_phase(self, phase):
        verify_type(phase.executor, Jar)
        phase.rebuild_on_from.append(self._phase_name)
        phase.vars['inputs'] = _java_jar_inputs_var
        if not hasattr(phase, '_classes_extensions'):
            phase._classes_extensions = []
        phase._classes_extensions.append(self)

    def apply_to_executor_java_jar(self, executor):
        executor.add_argument_unfiltered('$inputs')
    
    @property
    def _classes_outputs(self):
        with current_context() as ctx:
            project_outputs = ctx.get('current.project_outputs')
        if project_outputs is None:
            return []
        phase_outputs = project_outputs.get(self._project)
        if phase_outputs is None:
            return []
        return phase_outputs.get(self._phase_name) or []


def _debug_hook(executor):
    with current_context() as ctx:
        if ctx.get('build.debug', False):
            executor.enable_debug()


def _compile_hook(executor):
    with current_context() as ctx:
        phase = ctx.current.phase

    executor.add_argument_unfiltered('-d', '$output_path')
    executor.add_classpath(phase.input_path)
    phase.vars['output_path'] = _java_output_path_var


def _classpath_hook(executor):
    if executor.classpath:
        executor.add_argument('-classpath', u':'.join([pathify(v) for v in executor.classpath]))


def _java_output_path_var(output, inputs):
    with current_context() as ctx:
        return ctx.current.phase.output_path


def _java_jar_inputs_var(output, inputs):
    with current_context() as ctx:
        phase = ctx.current.phase

    outputs = []
    for classes_extension in phase._classes_extensions:
        outputs += classes_extension._classes_outputs
    
    def arg(output):
        path = output.path
        the_file = output.file
        
        if not path.endswith(os.sep):
            path += os.sep
        path_length = len(path)

        if the_file.startswith(path):
            the_file = the_file[path_length:]
            return u'-C {path} {file}'.format(path=pathify(path), file=pathify(the_file))
        else:
            return pathify(the_file)

    return u' '.join([arg(v) for v in outputs])
