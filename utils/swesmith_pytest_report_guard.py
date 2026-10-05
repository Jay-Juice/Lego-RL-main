"""Keep optional exception-name suggestions from breaking pytest reports.

Old Patsy passes a non-dict locals mapping to eval(). exceptiongroup's optional
suggestion renderer assumes it can iterate that mapping and raises KeyError.
This only omits the failed suggestion; it does not change test outcomes.
"""
def pytest_configure(config):
    import exceptiongroup._formatting as formatting
    original = getattr(formatting, '_compute_suggestion_error', None)
    if original is None:
        return

    def safe_suggestion(*args, **kwargs):
        try:
            return original(*args, **kwargs)
        except (KeyError, TypeError, AttributeError):
            return None

    formatting._compute_suggestion_error = safe_suggestion
