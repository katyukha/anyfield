import six
import unittest
import doctest

import anyfield

import logging
_logger = logging.getLogger(__name__)
_logger.setLevel(logging.INFO)



class TestSField(unittest.TestCase):
    def setUp(self):
        pass

    def test_apply_fn_simple_function_one_arg(self):
        """ Test if it is posible to add to stack simple function of one argument
        """
        sf = anyfield.SField()  # create new instance of SField

        fn = lambda x: x + 5  # Simple functions for tests

        # Add one single call to fn
        sf.__apply_fn__(fn)

        self.assertIn((fn, [anyfield.PlaceHolder], {}), sf.__sf_stack__)
        self.assertEqual(len(sf.__sf_stack__), 1)

        self.assertEqual(sf.__calculate__(1), 6)
        self.assertEqual(sf.__calculate__(7), 12)

        with self.assertRaises(TypeError):
            sf.__calculate__(None)

    def test_apply_fn_simple_function_two_arg(self):
        """ Test if function call with more than one arg is added to stack safely
        """
        sf = anyfield.SField()  # create new instance of SField

        fn = lambda x, z: x + z  # Simple functions for tests

        # Add one single call to fn
        sf.__apply_fn__(fn, 25)

        self.assertIn((fn, [anyfield.PlaceHolder, 25], {}), sf.__sf_stack__)
        self.assertEqual(len(sf.__sf_stack__), 1)

        self.assertEqual(sf.__calculate__(1), 26)
        self.assertEqual(sf.__calculate__(20), 45)

        with self.assertRaises(TypeError):
            sf.__calculate__(None)

    def test_apply_fn_simple_function_kwargs(self):
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

        self.assertEqual(len(sf.__sf_stack__), 1)
        sfn, sargs, skwargs = sf.__sf_stack__[0]
        self.assertIs(sfn, fn)
        self.assertEqual(sargs, [anyfield.PlaceHolder])
        self.assertDictEqual(skwargs, {'arg2': 100})

        self.assertEqual(sf.__calculate__(1), 125)
        self.assertEqual(sf.__calculate__(2), 150)

        with self.assertRaises(TypeError):
            sf.__calculate__(None)

    def test_sfield_dummy(self):
        sf = anyfield.SField(dummy=True)

        x1 = sf.__apply_fn__(lambda x: 5)
        x2 = sf.__apply_fn__(lambda x: 9)

        self.assertFalse(x1.__sf_dummy__)
        self.assertFalse(x2.__sf_dummy__)
        self.assertIsNot(x1, sf)
        self.assertIsNot(x2, sf)
        self.assertIs(x1.__class__, sf.__class__)
        self.assertIs(x2.__class__, sf.__class__)
        self.assertIs(x1.__class__, x2.__class__)

    def test_sfield_expression(self):
        F = anyfield.F

        self.assertEqual( ((F + 5 - 25) / 3.0).__calculate__(5),
                          (5 + 5 -25) / 3.0)

        self.assertEqual( (((F + 5) - 25) / 3.0).__calculate__(5),
                          ((5 + 5) -25) / 3.0)

        self.assertEqual( ((F + 5 - 25) / F).__calculate__(5),
                          (5 + 5 -25) / 5)


def load_tests(loader, tests, ignore):
    tests.addTests(doctest.DocTestSuite(anyfield))
    return tests
