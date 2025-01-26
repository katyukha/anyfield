"""
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

import types
import operator
import logging

_logger = logging.getLogger(__name__)

__version__ = '0.3.1'
__all__ = (
    'SField',
    'CField',
    'SView',
    'SF',
    'CF',
    'F',
    'C',
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


class PlaceHolderClass:
    """ Simple class to represent current calculated value
        (at start it is record itself), in operation list
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


class ComputeState:
    """ Simple class to handle state of computation of SField.
        Instances of this class contains original value and current value.
    """
    def __init__(self, value):
        self._orig_val = value
        self._curr_val = value

    @property
    def orig(self):
        """ Original value, that was passed at start of computation.
        """
        return self._orig_val

    @property
    def curr(self):
        """ Current value, that is computed on previous step.
        """
        return self._curr_val

    @curr.setter
    def curr(self, value):
        """ Setter for current value
        """
        self._curr_val = value

    def resolve(self, arg):
        """ Resolve value. Handle SField, CField.
        """
        # If argument is CField instance, then we have to compute it
        # based on current value, instead of original value
        if isinstance(arg, CField):
            return arg.__calculate__(self.curr)

        # If argument is SField, then let's try to process it by ourselfs
        # thus operator function will work with already computed value
        if isinstance(arg, SField):
            return arg.__calculate__(self.orig)

        return arg

    def __str__(self):
        return "ComputeState(orig=%(orig)s, curr=%(curr)s)" % {
            'orig': self.orig,
            'curr': self.curr,
        }


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
            return self
        else:
            return types.MethodType(self, instance)

    def __repr__(self):
        return "<Operator for %s>" % self.operation


def handle_sfield(fn):
    """ For internal use. This decorators mark function, that handles
        SField instances automatically. Usually used in functions/operations
        like `__q_if__` and `__q_match__`
    """
    fn.__anyfield_handle_sfield__ = True
    return fn


def handle_state(fn):
    """ Mark the function, as that one handles original record
    """
    fn.__anyfield_handle_state__ = True
    return fn


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
        mcs.add_operation(cls, 'q_contains', lambda x, y: y in x,
                          "Check if record contains argument."
                          "Used instead ``arg in F`` expression")
        mcs.add_operation(cls, 'q_in', lambda x, y: x in y,
                          "Check if argument contains record"
                          "Used instead ``F in arg`` expression")
        mcs.add_operation(cls, '__q_not__', lambda x: not x,
                          "Apply not operator to argument"
                          "For example: F.is_success.__q_not__().")

        # Conditional logic
        @handle_sfield
        @handle_state
        def q_if(state, t, f=False):
            """ Represents IF operation on SField.
                Check if argument is evaluated to True or False,
                and if it is evaluated to True, then return `t` else return `f`

                This operation supports SField instances for t and f.
            """
            if state.curr:
                return state.resolve(t)
            return state.resolve(f)


        @handle_sfield
        @handle_state
        def q_match(state, conditions, default=None):
            """ Check find correct match for X from list of condtions.
                This is analog to C-lang switch
            """
            for key, value in conditions:
                k = state.resolve(key)
                if state.curr == k:
                    return state.resolve(value)
            return state.resolve(default)


        @handle_sfield
        @handle_state
        def q_first(state, *args, default=None):
            """ Take first non-null value from arguments.
                This method take SField instances and resolves it automatically.
            """
            for arg in args:
                val = state.resolve(arg)
                if val:
                    return val
            return state.resolve(default)

        mcs.add_operation(cls, '__q_if__', q_if)
        mcs.add_operation(cls, '__q_match__', q_match)
        mcs.add_operation(cls, '__q_first__', q_first)

        return cls

    @classmethod
    def add_operation(mcs, cls, name, fn=None, doc=None):
        if fn and fn.__name__ == '<lambda>':
            fn.__name__ = '<lambda for %s>' % name
        if not getattr(fn, '__doc__', None) and doc is not None:
            fn.__doc__ = doc
        setattr(cls, name, Operator(name, fn))


class SField(metaclass=SFieldMeta):
    """ Class that allows to build simple expressions.
        For example, instead of writing something like::

            >>> l = [{'a': -30, 'b': {'c': 5}, 'd': 4},
            ...      {'a': 2, 'b': {'c': 15}, 'd': 3}]
            >>> l.sort(key=lambda x: x['a'] + x['b']['c'] - x['d'])
            >>> [i['a'] for i in l]  # just print first el from dict
            [-30, 2]

        With this class it is possible to write folowing::

            >>> from anyfield import SField
            >>> l = [{'a': -30, 'b': {'c': 5}, 'd': 4},
            ...      {'a': 2, 'b': {'c': 15}, 'd': 3}]
            >>> SF = SField(dummy=True)
            >>> l.sort(key=(SF['a'] + SF['b']['c'] - SF['d'])._F)
            >>> [i['a'] for i in l]  # just print first el from dict
            [-30, 2]

        Or using SF shortcut and F wrapper defined in this module::

            >>> from anyfield import SField, F
            >>> l = [{'a': -30, 'b': {'c': 5}, 'd': 4},
            ...      {'a': 2, 'b': {'c': 15}, 'd': 3}]
            >>> l.sort(key=(F['a'] + F['b']['c'] - F['d'])._F)
            >>> [i['a'] for i in l]  # just print first el from dict
            [-30, 2]

        Also, SField supports conditional branching:

            >>> data = {'v1': True, 'v2': False, 'v3': 'some text'}
            >>> F['v1'].__q_if__('Ok', 'Fail')._F(data)
            'Ok'
            >>> F['v2'].__q_if__('Ok', 'Fail')._F(data)
            'Fail'
            >>> F['v3'].__q_if__('Ok', 'Fail')._F(data)
            'Ok'
            >>> F['v3'].__q_if__(F['v3'], 'Fail')._F(data)
            'some text'
            >>> F['v3'].__q_if__(F['v3'].capitalize(), 'Fail')._F(data)
            'Some text'
            >>> F['v2'].__q_if__(F['v2'].capitalize(), 'Fail')._F(data)
            'Fail'
            >>> F['v2'].__q_if__(F['v2'].capitalize(), F['v3'])._F(data)
            'some text'
            >>> F['v2'].__q_if__(C.capitalize(), 'Fail')._F(data)
            'Fail'
            >>> F['v3'].__q_if__(C.capitalize(), 'Fail')._F(data)
            'Some text'
            >>> F.get('v7').__q_if__(C, 'Fail')._F(data)
            'Fail'
            >>> F.get('v3').__q_if__(C, 'Fail')._F(data)
            'some text'

        Additionally, SField supports pattern-matching in following way:

            >>> fexpression = F.__q_match__([
            ...    ("one", 1),
            ...    ("two", 2),
            ...    ("three", 3),
            ...    ("four", 4),
            ... ], default="Not defined")
            >>> fexpression.__calculate__("one")
            1
            >>> fexpression.__calculate__("three")
            3
            >>> fexpression.__calculate__("something")
            'Not defined'

        Example of negative expressions:

            >>> F.__q_not__()._F(True)
            False
            >>> F.__q_not__()._F(False)
            True

        :param str name: name of field
        :param bool dummy: if set to True, on next operation new SField instance will be created

    """

    # On this attributes AttributeError will be raised
    # for more info, see __getattr__
    __sf_not_supported_attributes__ = (
        '_ipython_canary_method_should_not_exist_',  # ipython check for 'have everything' object
        '_ipython_display_',                         # attempt to show rich representation for SField instance. it heve no one
        '__wrapped__',                               # make recursion in inspect.unwrap method. first seen, by attempting to run doctests
    )

    def __init__(self, name=None, dummy=False):
        self.__sf_stack__ = []  # operation stack
        self.__sf_dummy__ = dummy  # TODO: do we need this
        self.__sf_name__ = name

    def __apply_fn__(self, fn, *args, **kwargs):
        """ Adds ability to apply specified function to record in expression.
            It is similar to ``map`` but lazy: just adds operation to stack of
            this expression.

            :param callable fn: function to apply to expression result
            :return: SField instance

            For example::

                >>> data = ['10', '23', '1', '21', '53', '3', '4', '16']
                >>> expr = SField().__apply_fn__(int)
                >>> data.sort(key=expr._F)
                >>> print (data)
                ['1', '3', '4', '10', '16', '21', '23', '53']

            Also, we can use shortcut ``_A``::

                >>> data = ['10', '23', '1', '21', '53', '3', '4', '16']
                >>> expr = SField()._A(int)
                >>> data.sort(key=expr._F)
                >>> print (data)
                ['1', '3', '4', '10', '16', '21', '23', '53']
        """
        _logger.debug(
            "__apply_fn__ called with args (fn: %s, args: %s, kwargs: %s)",
            fn, args, kwargs)

        obj = self if self.__sf_dummy__ is False else self.__class__(dummy=False)
        obj.__sf_stack__.append((fn, [PlaceHolder] + list(args), kwargs))
        return obj

    def __calculate__(self, record):
        """ Do final calculation of this SField instances for specified record
        """
        state = ComputeState(record)

        def process_arg(op, arg):
            """ Simple function to process arguments
            """
            if arg is PlaceHolder:
                # If Operator supports handling compute state,
                # then we just pass state to op function.
                # Otherwise we pass current value
                if getattr(op, '__anyfield_handle_state__', False):
                    return state
                return state.curr

            # If operator func handle sfield arguments itself, we do not
            # evaluate SField, operator (op) will evaluate it by itself
            # (if needed)
            if getattr(op, '__anyfield_handle_sfield__', False):
                return arg

            # If argument is CField instance, then we have to compute it
            # based on current value, instead of original value
            if isinstance(arg, CField):
                return arg.__calculate__(state.curr)

            # If argument is SField, then let's try to process it by ourselfs
            # thus operator function will work with already computed value
            if isinstance(arg, SField):
                return arg.__calculate__(state.orig)

            # Return arg unprocessed
            return arg

        for op, args, kwargs in self.__sf_stack__:
            # process arguments
            args = tuple((process_arg(op, arg) for arg in args))
            kwargs = {key: process_arg(op, kwargs[key]) for key in kwargs}

            _logger.debug(
                "calc %s iter (op: %s, args: %s, kwargs: %s)",
                self, op, args, kwargs)

            # do operation
            state.curr = op(*args, **kwargs)
        return state.curr

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

    def __repr__(self):
        name = u"<SField %s>"

        if self.__sf_name__:
            name = name % "[%s]%%s" % self.__sf_name__

        if self.__sf_dummy__:
            name = name % " (dummy)"
        else:
            name = name % len(self.__sf_stack__)

        return name

    def __str__(self):
        return repr(self)

    def __getattr__(self, name):
        # this is required to avoid adding to stack repeating call to tese
        # methods
        if name in self.__sf_not_supported_attributes__:
            raise AttributeError("This attribute name is not supported by SField instances")
        return self.__apply_fn__(getattr, name)


class CField(SField):
    """ Same as SField, but could be used in SField expressions to compute
        value based on current value, instead of original value.

        Could be helpful in __q_if__ and __q_match__ expressions.
    """
    def __repr__(self):
        name = u"<CField %s>"

        if self.__sf_name__:
            name = name % "[%s]%%s" % self.__sf_name__

        if self.__sf_dummy__:
            name = name % " (dummy)"
        else:
            name = name % len(self.__sf_stack__)

        return name


def toFn(fn):
    """ Simple wrapper to adapt SField instances to callables,
        that usualy used in .filter(), .sort() and other methods.

        If some part of Your code may accept SField instances or
        callable of one arg as parametrs, use this function to adapt argument
        for example::

            >>> def my_super_filter_func(my_sequence, filter_fn):
            ...    filter_fn = toFn(filter_fn)
            ...    return list(filter(filter_fn, my_sequence))
            >>> my_super_filter_func(range(15), F % 2 == 0)
            [0, 2, 4, 6, 8, 10, 12, 14]

        This little line of code makes your function be able
        to use SField instances as filter_fn filter functions.

        :param fn: callable or SField instance
        :rtype: callable
        :return: if fn is instance of SField, then it's method .__calculate__ will be returned,
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

    @property
    def headers(self):
        """ List of field names
        """
        return [u"%s" % f for f in self.fields]

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

#: Shortcut for CField(dummy=True).
CF = CField(dummy=True)

#: Shortcut for CField(dummy=True).
C = CField(dummy=True)
