# Validation evidence

Inspected source for parse_limit:

```python
def parse_limit(value):
    if value < 0:
        raise ValueError("limit must be nonnegative")
    return value
```

No runtime invocation of parse_limit was performed. The source is complete for this function and establishes its negative-value guard.

A separate endpoint check ran against a local test build. The tester configured a limit of ten requests per minute, sent twelve requests in a loop, and observed status 429 on requests eleven and twelve. This was a test-specific configured limit, not the production default. Production behavior and defaults were not checked.
