import inspect
import json


class StrictTypeException(Exception):
    pass


class Schema(object):
    required = False
    strict = False
    hidden = False
    subtype = None
    type = str


class Model(dict):
    __BUILTIN__ = [
        bytes,
        float,
        str,
        int,
        bool,
        dict,
        tuple,
        object,
        slice,
        ]

    __iter_i = 0
    __iter_l = []
    __tostring = False

    def _getmembers(self):
        x = inspect.getmembers(self.__class__, lambda a: Model._find(a))
        return [i[1] for i in x]

    def _find(a):
        if not inspect.isclass(a):
            return False

        if issubclass(a, Schema):
            return True

        return False

    def instring(self):
        return self.__tostring

    def __init__(self, *args, **kw):
        # Init the dict with nothing in it.
        dict.__init__(self, (), **kw)

        # If we were loaded with a dict, process each name by class.
        if len(args) == 0:
            return

        self.__do_update(args[0])

    def __do_update(self, d):
        for k in d.keys():
            # Try and resolve the class. If we can't do so, just fall-back to
            # the name.
            c = ''
            try:
                c = getattr(self, k)
            except Exception as e:
                c = k

            dict.__setitem__(self, c, d[k])

    def keys(self):
        # Only return keys that exist or are required.
        r = []
        l = self._getmembers()
        for i in l:
            if ((i not in self) and (type(i) != str and issubclass(i, Schema) and (i.required is True))) or (i in self):
                r += [i]

        return r

    def update(self, K):
        self.__do_update(K)

    def __iter__(self):
        """
        This does not return strings, so that the result can be useful to
        functions that would use classes as indicies.
        """
        self.__iter_l = self._getmembers()
        self.__iter_i = 0

        while self.__iter_i < len(self.__iter_l):
            k = self.__iter_l[self.__iter_i]
            self.__iter_i += 1
            if k.hidden is True:
                continue

            # Feign an object.
            if k not in self and (type(k) != str and issubclass(k, Schema) and (k.required is True)):
                yield (k, k.type())
            elif k in self:
                yield (k, self[k])

    def __test_strict(self, _v, _t):
        if not isinstance(_v, _t):
            raise StrictTypeException("Model.set: strict ({0}!={1})".format(
                            _t,
                            type(_v)))

    def __setitem__(self, k, v):
        if k.strict is True:
            _t = k.type
            _v = v

            # We only validate two levels deep.
            if _t == list and k.subtype is not None:
                # First, make sure the list is a list.
                self.__test_strict(v, list)

                # Now, ensure each facet of the list is valid.
                _t = k.subtype
                for i in v:
                    self.__test_strict(i, _t)
            else:
                self.__test_strict(_v, _t)

        return dict.__setitem__(self, k, v)

    def __getitem__(self, x):
        # Handle custom types
        if ((x in self) and
           (x.type not in self.__BUILTIN__)):
            o = None
            if ((x.type == list) and
               ((x.subtype != list) and
               (x.subtype != tuple))):

                l = []
                for i in dict.__getitem__(self, x):
                    o = x.subtype

                    # If the object has an update method, use it.
                    up = getattr(o, 'update', None)
                    if (up is not None) and (o in self.__BUILTIN__):
                        o.update(i)
                    elif (up is not None) and (o not in self.__BUILTIN__):
                        o = o(i)
                    else:
                        o = i

                    l += [o]
                return l

            elif ((x.type == list) and
                  ((x.subtype == list) or
                  (x.subtype == tuple))):
                return dict.__getitem__(self, x)

            else:
                o = x.type()
                o.update(dict.__getitem__(self, x))
                return o

        elif ((x not in self) and (issubclass(x, Schema) and (x.required is True))):
            return x.type()

        # If the type is a builtin, just return the value
        return dict.__getitem__(self, x)

    def __repr__(self):
        # We have to override repr or it will leak keys not in KEYS. And
        # frankly, I don't care about the single-quote versus double-quote
        # regression. If we see this as a problem in the future, we'll fix it.
        return self.__str__()

    def items(self):
        x = dict.items(self)

        # Don't let items() ruin transitions from normal models to Shorts
        d = []
        for i in x:
            if i[0] not in self:
                continue
            d += [i]

        return d

    def __hash__(self):
        return hash(tuple(sorted(self.items())))

    def __str__(self):
        d = {}
        self.__tostring = True

        for i in self:
            # __iter__ should always return the set of attributes based on the
            # Schema class.
            i = i[0]

            # We ignore the required attribute and skip an object if it is
            # contained within this list. This is to ensure the name doesn't
            # appear in strings at all; i.e. internal objects only.
            if i.hidden is True:
                continue

            # If the type is required then generate a default value regardless
            # of whether or not it was defined by the writer.
            q = i.required
            t = i.type

            # Don't use __getitem__ because it may unpickle things that we
            # presume will be handled properly.
            if i in self:
                d[i.__name__] = self[i]
            elif q is True:
                # If the type is required but hasn't been set, and has a get
                # function, let it autogenerate the variable using the get
                # function.
                if getattr(i, 'get'):
                    d[i.__name__] = i.get(self[self.data])
                else:
                    d[i.__name__] = t()

        x = self.__json_dumps(d)
        self.__tostring = False
        return x

    def className(self):
        return self.__class__.__name__

    def __json_dumps(self, d):
        if isinstance(d, dict):
            return self.__json_dict(d)
        elif isinstance(d, list):
            return self.__json_list(d)
        elif isinstance(d, tuple):
            return self.__json_list(d)

    def __json_dict(self, d):
        s = []
        for k in d.keys():
            v = d[k]
            if type(k) != str and issubclass(k, Schema):
                k = k.__name__

            if (isinstance(v, list) or
                    isinstance(v, tuple) or
                    isinstance(v, dict)):
                v = self.__json_dumps(v)
                s += ["\"{0}\": {1}".format(k, v)]
            else:
                if isinstance(v, int) or isinstance(v, float):
                    # Bool is a sub of int. Make json happy.
                    if isinstance(v, bool):
                        if v is True:
                            v = 'true'
                        else:
                            v = 'false'

                    s += ["\"{0}\": {1}".format(k, v)]
                else:
                    if isinstance(v, str):
                        v = v.replace('"', '\\"')
                    s += ["\"{0}\": \"{1}\"".format(k, v)]

        s = ",".join(s)

        return "{0}{1}{2}".format('{', s, '}')

    def __json_list(self, d):
        s = []
        for v in d:
            if (isinstance(v, list) or
                    isinstance(v, tuple) or
                    isinstance(v, dict)):
                v = self.__json_dumps(v)
                s += [v]
            else:
                if isinstance(v, int) or isinstance(v, float):
                    s += ["{0}".format(v)]
                else:
                    if isinstance(v, str):
                        v = v.replace('"', '\\"')
                    s += ["\"{0}\"".format(v)]

        s = ",".join(s)

        return "[{0}]".format(s)
