"""
**Note**, this module is in **experimental** stage

This module provides *SField* class which is ised to avaoid lambdas
there where function of one argument is required to be applied to multiple items
Examples of such cases could be functions like:
- sorted
- filter
- map
- etc

Also this module provides shortcuts (already built SField instances),
that could be starting point of SField expressions. They are: SF, F
Both are same.

For example::

    import requests
    from anyfield import F, SView
    data = requests.get('https://api.github.com/repos/vmg/redcarpet/issues?state=closed')
    data = data.json()
    view = SView(F['id'],
                 F['state'],
                 F['user']['login'],
                 F['title'][:40],
    )
    for row in view(data):
        print(row)

Will result in::

    [121393880, u'closed', u'fusion809', u'Rendering of markdown in HTML tags']
    [120824892, u'closed', u'nitoyon', u'Fix bufprintf for Windows MinGW-w64']
    [118147051, u'closed', u'clemensg', u'Fix header anchor normalization']
    [115033701, u'closed', u'mitchelltd', u'Unicode headers produce invalid anchors']
    [113887752, u'closed', u'Stemby', u'Definition lists']
    [113740700, u'closed', u'Stemby', u'Multiline tables']
    [112952970, u'closed', u'im-kulikov', u"recipe for target 'redcarpet.so' failed"]
    [112494169, u'closed', u'mstahl', u'Unable to compile native extensions in O']
    [111961692, u'closed', u'reiz', u'Adding dependency badge to README']
    [111582314, u'closed', u'jamesaduke', u'Pre tags on code are not added when you ']
    [108204636, u'closed', u'shaneog', u'Push 3.3.3 to Rubygems']


"""

import six
import operator
import logging

_logger = logging.getLogger(__name__)

__all__ = (
    'SField',
    'SView',
    'SF',
    'F',
    'toFn',
    'toSField',
)


# List of operators, could be applied to SField instances
SUPPORTED_OPERATIONS = [
    '__abs__',
    '__add__',
    '__concat__',
    '__contains__',
    '__delitem__',
    '__div__',
    '__eq__',
    '__floordiv__',
    '__ge__',
    '__getitem__',
    '__gt__',
    '__iadd__',
    '__iconcat__',
    '__idiv__',
    '__ifloordiv__',
    '__ilshift__',
    '__imod__',
    '__imul__',
    '__index__',
    '__ipow__',
    '__irshift__',
    '__isub__',
    '__itruediv__',
    '__le__',
    '__lshift__',
    '__lt__',
    '__mod__',
    '__mul__',
    '__ne__',
    '__neg__',
    '__pos__',
    '__pow__',
    '__rshift__',
    '__setitem__',
    '__sub__',
    '__truediv__',
]


# Filter only operations that are supported by current python version
# For example '__div__' operation is not supported by python 3
SUPPORTED_OPERATIONS = [op for op in SUPPORTED_OPERATIONS if getattr(operator, op, False)]


@six.python_2_unicode_compatible
class PlaceHolderClass(object):
    """ Simple class to represent current calculated value (at start it is record itself), in operation list
    """
    inst = None

    def __new__(cls):
        if cls.inst is None:
            cls.inst = super(PlaceHolderClass, cls).__new__(cls)
        return cls.inst

    def __str__(self):
        return "PlaceHolder"

    def __repr__(self):
        return "<PlaceHolder>"


PlaceHolder = PlaceHolderClass()


class Operator(object):
    """ Simple operator implementation for SField

        This class is used internaly to bound operations to SField class

        By default on init operation name is used to get
        corresponding implementation function from ``operator`` module

        :param str operation: name of operation, if no 'operation_fn' passed, then
                              operation function will be taken from `operator` module.
        :param callable operation_fn: function that implements operation
    """
    def __init__(self, operation, operation_fn=None):
        self.operation = operation

        # Get operation implementation
        if operation_fn is None:
            self.operation_fn = getattr(operator, self.operation)
        else:
            self.operation_fn = operation_fn

        self.__doc__ = self.operation_fn.__doc__
        self.__name__ = self.operation_fn.__name__

    def __call__(self, obj, *args, **kwargs):
        # on operator call, just add operator's function to field's stack
        return obj.__apply_fn__(self.operation_fn, *args, **kwargs)

    def __get__(self, instance, cls):
        if instance is None:
            return six.create_unbound_method(self, cls)
        else:
            return six.create_bound_method(self, instance)

    def __repr__(self):
        return "<Operator for %s>" % self.operation


class SFieldMeta(type):
    """ SField's metaclass. At this time, just generates operator-related methods of SFields
    """

    def __new__(mcs, name, bases, attrs):
        cls = super(SFieldMeta, mcs).__new__(mcs, name, bases, attrs)

        for operation in SUPPORTED_OPERATIONS:
            mcs.add_operation(cls, operation)

        # Extra operator definition
        # mcs.add_operation(cls, '__getattr__', _getattr_)
        mcs.add_operation(cls, '__call__', lambda x, *args, **kwargs: x(*args, **kwargs))

        # Logical operations. Use bitwise operators for logical cases
        mcs.add_operation(cls, '__and__', lambda x, y: x and y)
        mcs.add_operation(cls, '__or__', lambda x, y: x or y)
        mcs.add_operation(cls, '__invert__', operator.not_)

        # Extra methods
        mcs.add_operation(cls, 'q_contains', lambda x, y: y in x)
        mcs.add_operation(cls, 'q_in', lambda x, y: x in y)

        return cls

    @classmethod
    def add_operation(mcs, cls, name, fn=None):
        if fn and fn.__name__ == '<lambda>':
            fn.__name__ = '<lambda for %s>' % name
        setattr(cls, name, Operator(name, fn))


@six.python_2_unicode_compatible
class SField(six.with_metaclass(SFieldMeta, object)):
    """ Class that allows to build simple expressions.
        For example, instead of writing something like::

            l = [{'a': 1, 'b': {'c': 5}, 'd': 4},
                 {'a': 2, 'b': {'c': 15}, 'd': 3}]
            l.sort(key=lambda x: x['a'] + x['b']['c'] - x['d'])

        With this class it is possible to write folowing::

            l = [{'a': 1, 'b': {'c': 5}, 'd': 4},
                 {'a': 2, 'b': {'c': 15}, 'd': 3}]
            SF = SField(dummy=True)
            l.sort(key=(SF['a'] + SF['b']['c'] - SF['d'])._F)

        Or using SF shortcut and F wrapper defined in this module::

            from anyfield import SField, F
            l = [{'a': 1, 'b': {'c': 5}, 'd': 4},
                 {'a': 2, 'b': {'c': 15}, 'd': 3}]
            l.sort(key=(F['a'] + F['b']['c'] - F['d'])._F)

        :param bool dummy: if set to True, on next operation new SField instance will be created

    """

    def __init__(self, dummy=False):
        self._stack = []  # operation stack
        self._dummy = dummy

    def __add_op__(self, op, args, kwargs):
        """ Add operation to operation stack of this SField instance

            :param callable op: callable that implements operation
            :param tuple args: arguments template for operation.
            :return: self
            :rtype: SField
        """
        _logger.debug("__add_op__ called with args (op: %s, args: %s, kwargs: %s)", op, args, kwargs)
        obj = self if self._dummy is False else self.__class__(dummy=False)
        obj._stack.append((op, args, kwargs))
        return obj

    def __apply_fn__(self, fn, *args, **kwargs):
        """ Adds ability to apply specified function to record in expression

            :param callable fn: function to apply to expression result
            :return: SField instance

            For example::

                data = ['10', '23', '1', '21', '53', '3', '4', '16']
                expr = SField().__apply_fn__(int)
                data.sort(key=expr._F)
                print data  # will print ['1', '3', '4', '10', '16', '21', '23', '53']
        """
        _logger.debug("__apply_fn__ called with args (fn: %s, args: %s, kwargs: %s)", fn, args, kwargs)
        return self.__add_op__(fn, [PlaceHolder] + list(args), kwargs)

    def __calculate__(self, record):
        """ Do final calculation of this SField instances for specified record
        """
        res = record

        def process_arg(arg):
            """ Simple function to process arguments
            """
            if arg is PlaceHolder:
                return res
            elif isinstance(arg, SField):
                return arg.__calculate__(record)
            else:
                return arg

        for op, args, kwargs in self._stack:
            # process arguments
            args = tuple((process_arg(arg) for arg in args))
            kwargs = {key: process_arg(kwargs[key]) for key in kwargs}

            _logger.debug("calc %s iter (op: %s, args: %s, kwargs: %s)", self, op, args, kwargs)

            # do operation
            res = op(*args, **kwargs)
        return res

    # Shortcut methods
    def _F(self, record):
        """ Shortcut for __calculate__ method

            If you need callable of one arg ot be passed for example to `filter` function
            Just finishe your expression with `._F` and You will get it
        """
        return self.__calculate__(record)

    def _A(self, fn, *args, **kwargs):
        """ Shortcut for '__apply_fn__' method.
        """
        return self.__apply_fn__(fn, *args, **kwargs)

    # ---

    def __repr__(self):
        if self._dummy:
            return u"<SField (dummy)>"
        return u"<SField (%s)>" % len(self._stack)

    def __str__(self):
        return repr(self)

    def __getattr__(self, name):
        # this is required to avoid adding to stack repeating call to tese
        # methods
        if name in ('_ipython_canary_method_should_not_exist_', '_ipython_display_'):
            raise AttributeError("Do not add ipython check methods to field stack")
        return self.__apply_fn__(getattr, name)


def toFn(fn):
    """ Simple wrapper to adapt SField instances to callables,
        that usualy used in .filter(), .sort() and other methods.

        If some part of Your code may accept SField instances or
        callable of one arg as parametrs, use this function to adapt argument
        for example::

            def my_super_filter_func(my_sequence, filter_fn):
                filter_fn = toFn(filter_fn)
                # Do your code

        This little line of code makes your function be able
        to use SField instances as filter_fn filter functions.

        :param fn: callable or SField instance
        :rtype: callable
        :return: if fn is instance of SField, then it's method .__claculate__ will be returned,
                 otherwise 'fn' will be returned unchanged
    """
    if isinstance(fn, SField):
        return fn.__calculate__
    return fn


def toSField(field):
    """ Reverse of `toFn`. if field is not SField instance, attempts to convert it to SField

        :return: field converted to SField instance
    """
    if callable(field) and not isinstance(field, SField):
        return SField().__apply_fn__(field)
    elif isinstance(field, SField):
        return field
    else:
        raise ValueError("Cannot parse field: %r" % field)


class SView(object):
    """ Just a simple view to work with SField.

        This class allows to build table-like representation
        of data.

        For example::

            view = SView(F.name, F.user.name, F.user.name.startswith('~'))
            data = requests.get('<data url>').json()
            for name, username, umark in view(data):
                print name, username, umark

    """

    def __init__(self, *fields):
        self.fields = []
        for f in fields:
            assert isinstance(f, SField) or callable(f), "Each field must be callable or instance of SField"
            self.fields.append(toSField(f))

    def __call__(self, data):
        for record in data:
            yield [f.__calculate__(record) for f in self.fields]


# Shortcuts
# =========

#: Shortcut for SField(dummy=True).
#: Can be used as starting point of SField expression.
SF = SField(dummy=True)

#: Shortcut for SField(dummy=True).
#: Can be used as starting point of SField expression.
F = SField(dummy=True)

