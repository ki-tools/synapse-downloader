class SynToolsError(Exception):
    """Generic exception."""


class FileSizeMismatchError(SynToolsError, IOError):
    """Error raised when the size for a download file fails to match the size of its file handle."""


class Md5MismatchError(SynToolsError, IOError):
    """Error raised when MD5 computed for a download file fails to match the MD5 of its file handle."""
