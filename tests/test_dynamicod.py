""" ae.dynamicod unit tests """
import ast
import textwrap

import pytest

import ae.base as tst_ae_base
import datetime as tst_dt
# import os as tst_os - removed in 0.3.17 (replaced with os_path_*() functions explicitly imported from ae.base)
import string as tst_str
from ae.base import DATE_ISO, UNSET

# noinspection PyProtectedMember
from ae.dynamicod import _base_globals_names, _import_names, exec_with_return, try_call, try_eval, try_exec


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

    def test_exec_with_return_with_base_globals(self):
        for name in _base_globals_names:
            obj_name = (' as ' + name).rsplit(' as ')[-1]
            assert exec_with_return(obj_name) is not None

    def test_import_names_exception(self):
        with pytest.raises(AttributeError):
            _import_names(["ae.base.not_existing_module_attr"])

        with pytest.raises(AttributeError):
            _import_names(["os.not_existing_module_attr"])

        with pytest.raises(ImportError):
            _import_names(["invalid or not existing import name"])

    def test_try_call(self):
        assert try_call(str, 123) == "123"
        assert try_call(bytes, '123', encoding='ascii') == b"123"
        assert try_call(int, '123') == 123

        call_arg = "no-number"
        with pytest.raises(ValueError):
            assert try_call(int, call_arg)
        assert try_call(int, call_arg, ignored_exceptions=(ValueError, )) is UNSET

    def test_try_eval_ae_base(self):
        assert try_eval("DATE_ISO") is DATE_ISO
        assert try_eval("UNSET") is UNSET
        assert try_eval("os_path_join") is tst_ae_base.os_path_join

    def test_try_eval_builtins(self):
        assert try_eval("abs") is abs
        assert try_eval("all") is all
        assert try_eval("any") is any
        assert try_eval("ascii") is ascii
        assert try_eval("bool") is bool
        assert try_eval("bytes") is bytes
        assert try_eval("dict") is dict
        assert try_eval("False") is False
        assert try_eval("int") is int
        assert try_eval("int('123')") == 123
        assert try_eval("list") is list
        assert try_eval("map") is map
        assert try_eval("print") is print
        assert try_eval("set") is set
        assert try_eval("sorted") is sorted
        assert try_eval("str") is str
        assert try_eval("str(123)") == "123"
        assert try_eval("str(bytes(b'123'), encoding='ascii')") == "123"
        assert try_eval("zip") is zip

    def test_try_eval_datetime(self):
        assert try_eval("datetime") is tst_dt
        assert try_eval("datetime.datetime(2100, 12, 21)") == tst_dt.datetime(2100, 12, 21)
        assert try_eval("datetime.date.today()") == tst_dt.date.today()

    def test_try_eval_multiline_expressions(self):
        expr = ''''tst_sep'.join(os_path_relpath(_d, 'ae')\nfor _d in path_files(os_path_join('ae', "**", "*.py")))\n'''
        assert 'tst_sep' not in try_eval(expr)
        assert try_eval(expr) == 'dynamicod.py'

        expr = textwrap.dedent('''
            'tst_sep'.join(os_path_relpath(_d, 'tests')
            for _d in sorted(path_files(os_path_join('tests', "**", "*.py"))))
        ''')
        assert 'tst_sep' in try_eval(expr)
        assert try_eval(expr) == 'conftest.py' + 'tst_sep' + 'test_dynamicod.py'

        expr = textwrap.dedent('''
            {
                'tst_key': [
                    'tst_val', 
                 ],
             }
        ''')

        val = try_eval(expr)
        assert val == ast.literal_eval(expr)
        assert isinstance(val, dict)
        assert val['tst_key'] == ['tst_val']

    # def test_try_eval_os(self):
    #     assert try_eval("os.path.join") is tst_os.path.join
    #     assert try_eval("""os.path.join("a", "b")""") == tst_os.path.join("a", "b")
    #     assert try_eval("os.path.sep") is tst_os.path.sep

    def test_try_eval_string(self):
        assert try_eval("digits") is tst_str.digits
        assert try_eval("ascii_letters") is tst_str.ascii_letters

    def test_try_eval_syntax_err(self):
        eval_str = "int('no-number')"
        with pytest.raises(ValueError):
            assert try_eval(eval_str)
        assert try_eval(eval_str, ignored_exceptions=(ValueError, )) is UNSET
        with pytest.raises(TypeError):      # list with ignored exceptions is not accepted
            # noinspection PyTypeChecker
            assert try_eval(eval_str, ignored_exceptions=[ValueError, ]) is UNSET

    def test_try_eval_vars(self):
        assert try_eval('b + 6', glo_vars=dict(b=3)) == 9
        assert try_eval('b + 6', loc_vars=dict(b=3)) == 9
        assert try_eval('b + 6', glo_vars=dict(b=33), loc_vars=dict(b=3)) == 9

    def test_try_eval_vars_add_base_globals(self):
        assert try_eval('datetime.date(2100, 12, 21).year') == 2100

        glo_vars = dict(_add_base_globals="")
        assert try_eval('datetime.date(2100, 12, 21).year', glo_vars=glo_vars) == 2100

        with pytest.raises(NameError):
            assert try_eval('datetime.date(2100, 12, 21).year', glo_vars={}) == 2100

    def test_try_eval_with_base_globals(self):
        for name in _base_globals_names:
            obj_name = (' as ' + name).rsplit(' as ')[-1]
            assert try_eval(obj_name) is not None

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
        dt_val = tst_dt.datetime.now()
        dt_str = tst_dt.datetime.strftime(dt_val, DATE_ISO)
        assert try_exec("dt = _; datetime.datetime.strftime(dt, DATE_ISO)", loc_vars={'_': dt_val}) == dt_str
