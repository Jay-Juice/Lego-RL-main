# CPython URL parser compatibility asset

`parse.py` is a vendored CPython 3.10 `urllib.parse` implementation used by the
task-specific Furl compatibility adapter. It is not installed into the shared
Python environment. See `../../repair_furl_compat_assets.py` for its use.

The CPython license and notices are retained in [LICENSE](LICENSE), sourced from
https://github.com/python/cpython/blob/v3.10.0/LICENSE.
