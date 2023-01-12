""" ae.dynamicod unit tests """
import datetime as test_dt
import pytest
import textwrap

from typing import cast

from ae.base import DATE_ISO, UNSET

from ae.dynamicod import exec_with_return, try_call, try_eval, try_exec


module_var = 'module_var_val'   # used for try_exec() tests


class TestHelpers:
    def test_exec_with_return_basics(self):
        assert exec_with_return("") is UNSET
        assert exec_with_return('1 + 2') == 3
        assert exec_with_return('a = 1 + 2; a') == 3
        assert exec_with_return('a = 1 + 2; a + 3') == 6
        assert exec_with_return('\na = 1 + 2\na\n') == 3

    def test_exec_with_return_syntax_err(self):
        syn_err = 'if :'
        with pytest.raises(SyntaxError):
            exec_with_return(syn_err)
        assert exec_with_return(syn_err, ignored_exceptions=(SyntaxError, )) is UNSET

    def test_exec_with_return_code_block(self):
        if_stmt = """
                        if 1 + 2 == 3:
                            a = 6
                        else:
                            a = 9
                        a
        """
        with pytest.raises(IndentationError):
            exec_with_return(if_stmt)
        if_stmt = textwrap.dedent(if_stmt)
        assert exec_with_return(if_stmt) == 6

    def test_exec_with_return_vars(self):
        assert exec_with_return('a = b + 6; a', glo_vars=dict(b=3)) == 9
        assert exec_with_return('a = b + 6; a', loc_vars=dict(b=3)) == 9
        assert exec_with_return('a = b + 6; a', glo_vars=dict(b=69), loc_vars=dict(b=3)) == 9

        loc_vars = dict(b=3)
        assert exec_with_return('a = b + 6', glo_vars=dict(b=69), loc_vars=loc_vars) is UNSET
        assert loc_vars.get('a') == 9

    def test_exec_with_return_add_global_vars(self):
        assert exec_with_return('datetime.date(2100, 12, 21).year') == 2100

        glo_vars = dict(_add_base_globals="")
        assert exec_with_return('datetime.date(2100, 12, 21).year', glo_vars=glo_vars) == 2100

        with pytest.raises(NameError):
            assert exec_with_return('datetime.date(2100, 12, 21).year', glo_vars={}) == 2100

    def test_try_call(self):
        assert try_call(str, 123) == "123"
        assert try_call(bytes, '123', encoding='ascii') == b"123"
        assert try_call(int, '123') == 123

        call_arg = "no-number"
        with pytest.raises(ValueError):
            assert try_call(int, call_arg)
        assert try_call(int, call_arg, ignored_exceptions=(ValueError, )) is UNSET

    def test_try_eval_basics(self):
        assert try_eval("str(123)") == "123"
        assert try_eval("str(bytes(b'123'), encoding='ascii')") == "123"
        assert try_eval("int('123')") == 123

    def test_try_eval_syntax_err(self):
        eval_str = "int('no-number')"
        with pytest.raises(ValueError):
            assert try_eval(eval_str)
        assert try_eval(eval_str, ignored_exceptions=(ValueError, )) is UNSET
        with pytest.raises(TypeError):      # list with ignored exceptions is not accepted
            assert try_eval(eval_str, ignored_exceptions=cast(tuple, [ValueError, ])) is UNSET

    def test_try_eval_vars(self):
        assert try_eval('b + 6', glo_vars=dict(b=3)) == 9
        assert try_eval('b + 6', loc_vars=dict(b=3)) == 9
        assert try_eval('b + 6', glo_vars=dict(b=33), loc_vars=dict(b=3)) == 9

    def test_try_eval_add_global_vars(self):
        assert try_eval('datetime.date(2100, 12, 21).year') == 2100

        glo_vars = dict(_add_base_globals="")
        assert try_eval('datetime.date(2100, 12, 21).year', glo_vars=glo_vars) == 2100

        with pytest.raises(NameError):
            assert try_eval('datetime.date(2100, 12, 21).year', glo_vars={}) == 2100

    def test_try_exec(self):
        assert try_exec('a = 1 + 2; a') == 3
        assert try_exec('a = 1 + 2; a + 3') == 6
        assert try_exec('a = b + 6; a', glo_vars=dict(b=3)) == 9
        assert try_exec('a = b + 6; a', loc_vars=dict(b=3)) == 9
        assert try_exec('a = b + 6; a', glo_vars=dict(b=69), loc_vars=dict(b=3)) == 9

        code_block = "a=1+2; module_var"
        with pytest.raises(NameError):
            assert try_exec(code_block) == module_var
        assert try_exec(code_block, ignored_exceptions=(NameError, )) is UNSET
        assert try_exec(code_block, glo_vars=globals()) == module_var

        # check ae.core datetime/DATE_ISO context (globals)
        dt_val = test_dt.datetime.now()
        dt_str = test_dt.datetime.strftime(dt_val, DATE_ISO)
        assert try_exec("dt = _; datetime.datetime.strftime(dt, DATE_ISO)", loc_vars={'_': dt_val}) == dt_str
