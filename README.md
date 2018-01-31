# python-model-library
Python Model Library

This is a small library designed to make it simpler to build API integrations.
Most modern APIs use some form of JSON for communication over a TLS channel.
This library helps speed the development of structures in Python that mimick
these API endpoints without having to perform much work. It also allows for
the developer to quickly build objects from nested JSON, or to build JSON
strings from nested objects.

For examples, check out a non-release branch and use the test scripts.

# Usage
First, create an object that is based on any object tree you like, which is
rooted with modellib.Model.Model. 

Next, create Schema objects within. The Schema classes comprise the names that
shall be used as dict keys objects with metadata. 

class Foo(object):
    class bar(Schema):
        required = True
        strict = True
    class baz(Schema):
        type = int

# Type
The 'type' parameter dictates what type of data should be stored at this
namespace. It can be any Python type or custom class.

# Required
The 'required' parameter dictates whether the namespace is included as
output even if it were never set. For example, when creating a schema
to interact with a remote API, you may not want (or need) to set all
parameters in the API call. However, the API call may require the presence
of the name. 'required' ensures that the name will always appear when the
string version of the object is generated, helping guarantee that the
remote API will never raise an exception because of a missing parameter.

For example, in the above class, if we did:
    f = Foo()
    f[f.baz] = 127
    api_call = str(f)

The following would be sent via JSON to the remote API:
    {"bar": "","baz": 127}

This makes it faster and simpler to both generate API schemas and interact
with the remote endpoint.

# Strict
The 'strict' keyword ensures that the type of object used in a set on the
schema namespace adheres to the 'type' parameter. If it does not, a
StrictTypeException is raised.

# Subtype
For lists or similar python constructs, where a facet of the primary object
can be any type, the facet itself may be strictly checked. This is done by
setting the subtype.

It is also necessary to set the subtype so the get action can interpret the
data within the facet correctly. This is especially necessary when a custom
class has been placed within a list, for example, and we're converting JSON
to actual objects. The 'get' action will convert the name to the appropriate
type seamlessly and transparently.
