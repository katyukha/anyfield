import anyfield

import pytest

import logging
_logger = logging.getLogger(__name__)
_logger.setLevel(logging.INFO)



def test_apply_fn_simple_function_one_arg():
    """ Test if it is posible to add to stack simple function of one argument
    """
    sf = anyfield.SField()  # create new instance of SField

    fn = lambda x: x + 5  # Simple functions for tests

    # Add one single call to fn
    sf.__apply_fn__(fn)

    assert (fn, [anyfield.PlaceHolder], {}) in sf.__sf_stack__
    assert len(sf.__sf_stack__) == 1

    sf.__calculate__(1) == 6
    sf.__calculate__(7) == 12

    with pytest.raises(TypeError):
        sf.__calculate__(None)


def test_apply_fn_simple_function_two_arg():
    """ Test if function call with more than one arg is added to stack safely
    """
    sf = anyfield.SField()  # create new instance of SField

    fn = lambda x, z: x + z  # Simple functions for tests

    # Add one single call to fn
    sf.__apply_fn__(fn, 25)

    assert (fn, [anyfield.PlaceHolder, 25], {}) in sf.__sf_stack__
    assert len(sf.__sf_stack__) == 1

    assert sf.__calculate__(1) == 26
    assert sf.__calculate__(20) == 45

    with pytest.raises(TypeError):
        sf.__calculate__(None)


def test_apply_fn_simple_function_kwargs():
    """ Test apply function with keyword arguments
    """
    sf = anyfield.SField()  # create new instance of SField

    def fn(record, arg1=25, arg2=None):
        res = record * arg1
        if arg2 is not None:
            res = res + arg2
        return res

    # Add one single call to fn
    sf.__apply_fn__(fn, arg2=100)

    assert len(sf.__sf_stack__) == 1
    sfn, sargs, skwargs = sf.__sf_stack__[0]
    assert sfn is fn
    assert sargs == [anyfield.PlaceHolder]
    assert skwargs == {'arg2': 100}

    assert sf.__calculate__(1) == 125
    assert sf.__calculate__(2) == 150

    with pytest.raises(TypeError):
        sf.__calculate__(None)


def test_sfield_dummy():
    sf = anyfield.SField(dummy=True)

    x1 = sf.__apply_fn__(lambda x: 5)
    x2 = sf.__apply_fn__(lambda x: 9)

    assert not x1.__sf_dummy__
    assert not x2.__sf_dummy__
    assert x1 is not sf
    assert x2 is not sf
    assert x1.__class__ is sf.__class__
    assert x2.__class__ is sf.__class__
    assert x1.__class__ is x2.__class__


def test_sfield_expression():
    F = anyfield.F

    assert ((F + 5 - 25) / 3.0).__calculate__(5) == (5 + 5 -25) / 3.0
    assert (((F + 5) - 25) / 3.0).__calculate__(5) == ((5 + 5) -25) / 3.0
    assert ((F + 5 - 25) / F).__calculate__(5) == (5 + 5 -25) / 5
