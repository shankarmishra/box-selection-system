"""
Pure packing/selection domain.

This package has ZERO Django imports and ZERO database access. It takes
plain dataclasses in, returns plain dataclasses out. That's deliberate:
the box-fit algorithm is the actual assignment, so it needs to be
testable in milliseconds without a database, and portable to a worker
process / serverless function unchanged.

See docs/ALGORITHM.md for the full write-up of how this works.
"""
