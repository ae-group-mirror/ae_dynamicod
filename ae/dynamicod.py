"""
dynamic execution of code blocks and expressions
================================================

this ae namespace portion provides useful helper functions to evaluate Python expressions and execute
Python code dynamically at application run-time.

dynamically executed code block or expression string offers convenience for powerful system and application
configuration and for data-driven architectures.

for the dynamic execution of functions and code blocks the helper functions :func:`try_call`, :func:`try_exec`
and :func:`exec_with_return` are provided. the helper function :func:`try_eval` evaluates dynamic expressions.

.. note::
    **security considerations**

    make sure that any dynamically executed code is from a secure source to prevent code injections of malware.
    treat configuration files from untrusted sources with extreme caution and
    only execute them after a complete check and/or within a sandbox.

.. hint::
    these functions are e.g. used by the :class:`~.literal.Literal` class to dynamically determine literal values.
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
from typing import Any, Callable, Dict, List, Optional, Tuple, Type
from _ast import stmt

from ae.base import (                                                               # type: ignore
    DATE_ISO, DATE_TIME_ISO, UNSET,
    full_stack_trace,
    module_attr, module_file_path, module_name,
    norm_name, norm_path,
    stack_frames, stack_var, stack_vars)


__version__ = '0.3.14'


# suppress unused import err (needed e.g. for unpickling of dates via try_eval() and for include them into base_globals)
_d = (os, DATE_ISO, DATE_TIME_ISO,
      ascii_letters, digits, datetime, full_stack_trace, logging, logging_config,
      module_attr, module_file_path, module_name,
      norm_name, norm_path,
      stack_frames, stack_var, stack_vars,
      threading, unicodedata, weakref)


def exec_with_return(code_block: str, ignored_exceptions: Tuple[Type[Exception], ...] = (),
                     glo_vars: Optional[Dict[str, Any]] = None, loc_vars: Optional[Dict[str, Any]] = None
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
        glo_vars.update(base_globals)

    try:
        code_ast = ast.parse(code_block)    # raises SyntaxError if code block is invalid
        nodes: List[stmt] = code_ast.body
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

    return UNSET                        # mypy needs explicit return statement and value


def try_call(callee: Callable, *args, ignored_exceptions: Tuple[Type[Exception], ...] = (), **kwargs) -> Optional[Any]:
    """ execute callable while ignoring specified exceptions and return callable return value.

    :param callee:              pointer to callable (either function pointer, lambda expression, a class, ...).
    :param args:                function arguments tuple.
    :param ignored_exceptions:  tuple of ignored exceptions.
    :param kwargs:              function keyword arguments dict.
    :return:                    function return value or UNSET if an ignored exception got thrown.
    """
    ret = UNSET
    try:  # catch type conversion errors, e.g. for datetime.date(None) while bool(None) works (->False)
        ret = callee(*args, **kwargs)
    except ignored_exceptions:
        pass
    return ret


def try_eval(expr: str, ignored_exceptions: Tuple[Type[Exception], ...] = (),
             glo_vars: Optional[Dict[str, Any]] = None, loc_vars: Optional[Dict[str, Any]] = None) -> Optional[Any]:
    """ evaluate expression string ignoring specified exceptions and return evaluated value.

    :param expr:                expression to evaluate.
    :param ignored_exceptions:  tuple of ignored exceptions.
    :param glo_vars:            optional globals() available in the expression evaluation.
    :param loc_vars:            optional locals() available in the expression evaluation.
    :return:                    function return value or UNSET if an ignored exception got thrown.
    """
    ret = UNSET

    if glo_vars is None:
        glo_vars = base_globals
    elif '_add_base_globals' in glo_vars:
        glo_vars.update(base_globals)

    try:  # catch type conversion errors, e.g. for datetime.date(None) while bool(None) works (->False)
        ret = eval(expr, glo_vars, loc_vars)
    except ignored_exceptions:
        pass
    return ret


def try_exec(code_block: str, ignored_exceptions: Tuple[Type[Exception], ...] = (),
             glo_vars: Optional[Dict[str, Any]] = None, loc_vars: Optional[Dict[str, Any]] = None) -> Optional[Any]:
    """ execute python code block string ignoring specified exceptions and return value of last code line in block.

    :param code_block:          python code block to be executed.
    :param ignored_exceptions:  tuple of ignored exceptions.
    :param glo_vars:            optional globals() available in the code execution.
    :param loc_vars:            optional locals() available in the code execution.
    :return:                    function return value or UNSET if an ignored exception got thrown.
    """
    ret = UNSET
    try:
        ret = exec_with_return(code_block, glo_vars=glo_vars, loc_vars=loc_vars)
    except ignored_exceptions:
        pass
    return ret


base_globals = globals()        #: default if no global variables get passed in dynamic code/expression evaluations
