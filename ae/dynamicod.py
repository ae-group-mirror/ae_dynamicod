"""
dynamic execution of code blocks and expressions
================================================

this ae namespace portion provides useful helper functions to evaluate Python expressions and execute
Python code dynamically at application run-time. these functions are e.g. used by the :class:`~ae.literal.Literal`
class to dynamically determine literal values.

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
import datetime
import logging
import logging.config as logging_config
import os
import threading
import unicodedata
import weakref

from string import ascii_letters, digits
from typing import Any, Callable, Optional, Type
from _ast import stmt

# import all non-private base symbols which can be made accessible in dynamic code execution and expression evaluations
from ae.base import *                                                                       # type: ignore # noqa: F403


__version__ = '0.3.15'


# suppress unused import err (needed e.g. for unpickling of dates via try_eval() and for include them into base_globals)
_dc = (ascii_letters, digits, datetime, logging, logging_config, os, threading, unicodedata, weakref)


VariableMap = dict[str, Any]


def _merge_vars(add: VariableMap) -> VariableMap:
    merged = base_globals.copy()
    merged.update(add)
    return merged


def exec_with_return(code_block: str, ignored_exceptions: tuple[Type[Exception], ...] = (),
                     glo_vars: Optional[VariableMap] = None, loc_vars: Optional[VariableMap] = None
                     ) -> Optional[Any]:
    """ execute python code block and return the resulting value of its last code line.

    :param code_block:          python code block to execute.
    :param ignored_exceptions:  tuple of ignored exceptions.
    :param glo_vars:            optional globals() available in the code execution.
    :param loc_vars:            optional locals() available in the code execution.
    :return:                    value of the expression at the last code line
                                or UNSET if either code block is empty, only contains comment lines, or one of
                                the ignorable exceptions raised or if last code line is no expression.

    inspired by this SO answer
    https://stackoverflow.com/questions/33409207/how-to-return-value-from-exec-in-function/52361938#52361938.
    """
    if glo_vars is None:
        glo_vars = base_globals
    elif '_add_base_globals' in glo_vars:
        glo_vars = _merge_vars(glo_vars)    # use base_globals updated/extended by the vars specified in glo_vars

    try:
        code_ast = ast.parse(code_block)    # raises SyntaxError if code block is invalid
        nodes: list[stmt] = code_ast.body
        if nodes:
            if isinstance(nodes[-1], ast.Expr):
                last_node = nodes.pop()
                if len(nodes) > 0:
                    # noinspection BuiltinExec
                    exec(compile(code_ast, "<ast>", 'exec'), glo_vars, loc_vars)
                # noinspection PyTypeChecker
                # .. and mypy needs getattr() instead of last_node.value
                return eval(compile(ast.Expression(getattr(last_node, 'value')), "<ast>", 'eval'), glo_vars, loc_vars)
            # noinspection BuiltinExec
            exec(compile(code_ast, "<ast>", 'exec'), glo_vars, loc_vars)
    except ignored_exceptions:
        pass                            # return UNSET if one of the ignorable exceptions raised in compiling

    return UNSET                        # type: ignore # noqa: F405 # mypy needs explicit return statement and value


def try_call(callee: Callable, *args, ignored_exceptions: tuple[Type[Exception], ...] = (), **kwargs) -> Optional[Any]:
    """ execute callable while ignoring specified exceptions and return callable return value.

    :param callee:              pointer to callable (either function pointer, lambda expression, a class, ...).
    :param args:                function arguments tuple.
    :param ignored_exceptions:  tuple of ignored exceptions.
    :param kwargs:              function keyword arguments dict.
    :return:                    function return value or UNSET if an ignored exception got thrown.
    """
    ret = UNSET                                                                             # type: ignore # noqa: F405
    try:  # catch type conversion errors, e.g. for datetime.date(None) while bool(None) works (->False)
        ret = callee(*args, **kwargs)
    except ignored_exceptions:
        pass
    return ret


def try_eval(expr: str, ignored_exceptions: tuple[Type[Exception], ...] = (),
             glo_vars: Optional[VariableMap] = None, loc_vars: Optional[VariableMap] = None) -> Optional[Any]:
    """ evaluate expression string ignoring specified exceptions and return evaluated value.

    :param expr:                expression to evaluate.
    :param ignored_exceptions:  tuple of ignored exceptions.
    :param glo_vars:            optional globals() available in the expression evaluation.
    :param loc_vars:            optional locals() available in the expression evaluation.
    :return:                    function return value or UNSET if an ignored exception got thrown.
    """
    ret = UNSET                                                                             # type: ignore # noqa: F405

    if glo_vars is None:
        glo_vars = base_globals
    elif '_add_base_globals' in glo_vars:
        glo_vars = _merge_vars(glo_vars)    # use base_globals updated/extended by the vars specified in glo_vars

    try:  # catch type conversion errors, e.g. for datetime.date(None) while bool(None) works (->False)
        ret = eval(expr, glo_vars, loc_vars)
    except ignored_exceptions:
        pass
    return ret


def try_exec(code_block: str, ignored_exceptions: tuple[Type[Exception], ...] = (),
             glo_vars: Optional[VariableMap] = None, loc_vars: Optional[VariableMap] = None) -> Optional[Any]:
    """ execute python code block string ignoring specified exceptions and return value of last code line in block.

    :param code_block:          python code block to be executed.
    :param ignored_exceptions:  tuple of ignored exceptions.
    :param glo_vars:            optional globals() available in the code execution.
    :param loc_vars:            optional locals() available in the code execution.
    :return:                    function return value or UNSET if an ignored exception got thrown.
    """
    ret = UNSET                                                                             # type: ignore # noqa: F405
    try:
        ret = exec_with_return(code_block, glo_vars=glo_vars, loc_vars=loc_vars)
    except ignored_exceptions:
        pass
    return ret


base_globals = globals()        #: default if no global variables get passed in dynamic code/expression evaluations
