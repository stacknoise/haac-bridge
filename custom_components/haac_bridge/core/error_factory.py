"""ErrorFactory: turns any caught exception into a HaacBridgeError (concept 18.2, 18.3)."""

import voluptuous as vol

from .errors import HaacBridgeError, InternalError, RequestError


class ErrorFactory:
    """Maps exceptions to HaacBridgeError; the only place that decides an error's code."""

    def from_exception(self, err: Exception) -> HaacBridgeError:
        """Return a HaacBridgeError for `err`; unknown exceptions become HAB-INT-000."""
        if isinstance(err, HaacBridgeError):
            return err
        if isinstance(err, vol.Invalid):
            return RequestError()
        return InternalError()
