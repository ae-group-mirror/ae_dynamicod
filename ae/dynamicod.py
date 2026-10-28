"""
dynamic execution of code blocks and expressions
================================================

this ae namespace portion provides useful helper functions to evaluate Python expressions and execute
Python code dynamically at application run-time. these functions are e.g. used by the :class:`~ae.literal.Literal`
class to dynamically parse literals into their representing values.

dynamically executed code block or expression string offers convenience for powerful system and application
configuration and for data-driven architectures.

for the dynamic execution of functions and code blocks the helper functions :func:`try_call`, :func:`try_exec`
and :func:`exec_with_return` are provided. the helper function :func:`try_eval` evaluates dynamic expressions.

.. note::
    **security considerations**

    make sure that any dynamically executed code is from a secure source to prevent code injections of malware.
    treat configuration files from untrusted sources with extreme caution and
    only execute them after a complete check and/or within a sandbox/controlled-environment.

.. hint::
    most of the helper functions provided by this module have the two arguments `glo_vars` and `loc_vars` to
    pass the global and local variable names and values that are accessible from the dynamically evaluated/executed
    expression/code. therefore, code injections can be controlled by passing dictionaries to these arguments which are
    either empty or contain only secure symbols.
"""
import ast
import importlib

from collections.abc import Callable
from typing import Any, Iterable

from ae.base import UNSET                   # type: ignore


__version__ = '0.3.17'


ObjectsMap = dict[str, Any]


def exec_with_return(code_block: str, ignored_exceptions: tuple[type[Exception], ...] = (),
                     glo_vars: ObjectsMap | None = None, loc_vars: ObjectsMap | None = None
                     ) -> Any | None:
    """ execute Python code block and return the resulting value of its last code line.

    :param code_block:          Python code block to execute.
    :param ignored_exceptions:  tuple of ignored exceptions.
    :param glo_vars:            optional globals() available in the code execution.
    :param loc_vars:            optional locals() available in the code execution.
    :return:                    value of the expression at the last code line
                                or :data:`~ae.base.UNSET` if either code block is empty, only contains comment lines,
                                or one of the ignorable exceptions raised or if last code line is no expression.

    inspired by this SO answer
    https://stackoverflow.com/questions/33409207/how-to-return-value-from-exec-in-function/52361938#52361938.
    """
    if glo_vars is None:
        glo_vars = base_globals
    elif '_add_base_globals' in glo_vars:
        glo_vars = _merge_vars(glo_vars)    # use base_globals updated/extended by the vars specified in glo_vars

    try:
        code_ast = ast.parse(code_block)    # raises SyntaxError if code block is invalid
        nodes: list[ast.stmt] = code_ast.body
        if nodes:
            if isinstance(nodes[-1], ast.Expr):
                last_node = nodes.pop()
                if len(nodes) > 0:
                    exec(compile(code_ast, "<ast>", 'exec'), glo_vars, loc_vars)            # pylint: disable=exec-used

                # mypy needs getattr() instead of last_node.value                           # pylint: disable=eval-used
                return eval(compile(ast.Expression(getattr(last_node, 'value')), "<ast>", 'eval'), glo_vars, loc_vars)

            exec(compile(code_ast, "<ast>", 'exec'), glo_vars, loc_vars)                    # pylint: disable=exec-used
    except ignored_exceptions:
        pass                            # return UNSET if one of the ignorable exceptions raised in compiling

    return UNSET


def try_call(callee: Callable, *args, ignored_exceptions: tuple[type[Exception], ...] = (), **kwargs) -> Any | None:
    """ execute callable while ignoring specified exceptions and return callable return value.

    :param callee:              pointer to callable (either function pointer, lambda expression, a class).
    :param args:                function arguments tuple.
    :param ignored_exceptions:  tuple of ignored exceptions.
    :param kwargs:              function keyword arguments dict.
    :return:                    function return value or :data:`~ae.base.UNSET` if an ignored exception got thrown.
    """
    ret = UNSET
    try:  # catch type conversion errors, e.g. for datetime.date(None) while bool(None) works (->False)
        ret = callee(*args, **kwargs)
    except ignored_exceptions:
        pass
    return ret


def try_eval(expr: str, ignored_exceptions: tuple[type[Exception], ...] = (),
             glo_vars: ObjectsMap | None = None, loc_vars: ObjectsMap | None = None) -> Any | None:
    """ evaluate expression string ignoring specified exceptions and return evaluated value.

    :param expr:                expression to evaluate.
    :param ignored_exceptions:  tuple of ignored exceptions.
    :param glo_vars:            optional globals() available in the expression evaluation.
    :param loc_vars:            optional locals() available in the expression evaluation.
    :return:                    function return value or :data:`~ae.base.UNSET` if an ignored exception got thrown.
    """
    ret = UNSET

    if glo_vars is None:
        glo_vars = base_globals
    elif '_add_base_globals' in glo_vars:
        glo_vars = _merge_vars(glo_vars)    # use base_globals updated/extended by the vars specified in glo_vars

    try:  # catch type conversion errors, e.g. for datetime.date(None) while bool(None) works (->False)
        ret = eval(expr, glo_vars, loc_vars)                                                # pylint: disable=eval-used
    except ignored_exceptions:
        pass
    return ret


def try_exec(code_block: str, ignored_exceptions: tuple[type[Exception], ...] = (),
             glo_vars: ObjectsMap | None = None, loc_vars: ObjectsMap | None = None) -> Any | None:
    """ execute Python code block string ignoring specified exceptions and return value of last code line in block.

    :param code_block:          Python code block to be executed.
    :param ignored_exceptions:  tuple of ignored exceptions.
    :param glo_vars:            optional globals() available in the code execution.
    :param loc_vars:            optional locals() available in the code execution.
    :return:                    function return value or :data:`~ae.base.UNSET` if an ignored exception got thrown.
    """
    ret = UNSET
    try:
        ret = exec_with_return(code_block, glo_vars=glo_vars, loc_vars=loc_vars)
    except ignored_exceptions:
        pass
    return ret


def _import_names(names: Iterable[str]) -> ObjectsMap:
    """ resolve and map qualified Python names to their dynamically imported objects.

    :param names:               iterable of fully qualified Python import names, optionally with a `' as ' + alias_name`
                                suffix, like e.g.::

                                    ['datetime', 'datetime.date.strftime', 'os.path.join', 'string.digits as digits']

    :return:                    dictionary mapping fully qualified Python names to objects, like e.g.::

                                    {
                                        'datetime': <module datetime>,
                                        'datetime.date.strftime': <method datetime.date.strftime>,
                                        'os.path.join': <function os.path.join>,
                                        'digits': "0123456789"
                                    }

    :raises:                    ImportError if no importable module can be determined.
                                AttributeError if an attribute in a module does not exist.
    """
    objects: dict[str, object] = {}

    for name in names:
        import_name, *alias = name.split(' as ')

        parts = import_name.split(".")
        for module_parts_count in range(len(parts), 0, -1):
            module_name = ".".join(parts[:module_parts_count])
            try:
                module = importlib.import_module(module_name)
                break
            except ImportError:
                continue
        else:
            raise ImportError(f"module {import_name!r} cannot be imported")

        obj: object = module
        for attribute_name in parts[module_parts_count:]:
            obj = getattr(obj, attribute_name)

        objects[alias[0] if alias else import_name] = obj

    return objects


def _merge_vars(add: ObjectsMap) -> ObjectsMap:
    merged = base_globals.copy()
    merged.update(add)
    return merged


_base_globals_names = (
    'ae.base.DATE_ISO' + ' as ' + 'DATE_ISO',
    'ae.base.DATE_TIME_ISO' + ' as ' + 'DATE_TIME_ISO',
    'ae.base.dedefuse' + ' as ' + 'dedefuse',
    'ae.base.defuse' + ' as ' + 'defuse',
    'ae.base.format_given' + ' as ' + 'format_given',
    'ae.base.list_find' + ' as ' + 'list_find',
    'ae.base.mask_secrets' + ' as ' + 'mask_secrets',
    'ae.base.mask_url' + ' as ' + 'mask_url',
    'ae.base.norm_name' + ' as ' + 'norm_name',
    'ae.base.norm_path' + ' as ' + 'norm_path',
    'ae.base.now_str' + ' as ' + 'now_str',
    'ae.base.NOW_STR_FORMAT' + ' as ' + 'NOW_STR_FORMAT',
    'ae.base.os_path_abspath' + ' as ' + 'os_path_abspath',
    'ae.base.os_path_basename' + ' as ' + 'os_path_basename',
    'ae.base.os_path_dirname' + ' as ' + 'os_path_dirname',
    'ae.base.os_path_expanduser' + ' as ' + 'os_path_expanduser',
    'ae.base.os_path_isdir' + ' as ' + 'os_path_isdir',
    'ae.base.os_path_isfile' + ' as ' + 'os_path_isfile',
    'ae.base.os_path_join' + ' as ' + 'os_path_join',
    'ae.base.os_path_normpath' + ' as ' + 'os_path_normpath',
    'ae.base.os_path_realpath' + ' as ' + 'os_path_realpath',
    'ae.base.os_path_relpath' + ' as ' + 'os_path_relpath',
    'ae.base.os_path_splitext' + ' as ' + 'os_path_splitext',
    'ae.base.os_path_split' + ' as ' + 'os_path_split',
    'ae.base.parse_date' + ' as ' + 'parse_date',
    'ae.base.pep8_format' + ' as ' + 'pep8_format',
    'ae.base.read_bin_file' + ' as ' + 'read_bin_file',
    'ae.base.read_file' + ' as ' + 'read_file',
    'ae.base.round_traditional' + ' as ' + 'round_traditional',
    'ae.base.sign' + ' as ' + 'sign',
    'ae.base.url_failure' + ' as ' + 'url_failure',
    'ae.base.utc_datetime' + ' as ' + 'utc_datetime',
    'ae.base.UNSET' + ' as ' + 'UNSET',
    'ae.base.write_bin_file' + ' as ' + 'write_bin_file',
    'ae.base.write_file' + ' as ' + 'write_file',
    'ae.paths.path_files' + ' as ' + 'path_files',
    # 'ast',
    # 'ast.literal_eval' + ' as ' + 'literal_eval',
    'datetime',
    # 'logging',
    # 'logging.config' + ' as ' + 'logging_config',
    # 'os',
    'string.ascii_letters' + ' as ' + 'ascii_letters',
    'string.digits' + ' as ' + 'digits',
    # 'threading',
    'unicodedata',
    'weakref',
)
base_globals = _import_names(_base_globals_names)
