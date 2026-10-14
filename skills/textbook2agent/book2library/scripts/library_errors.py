"""The one exception type for expected problems with the learner's input or workspace."""


class LibraryError(Exception):
    """Reported to the user as a message with exit code 1, never as a traceback."""
