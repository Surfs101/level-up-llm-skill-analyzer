"""Errors that carry a user-facing message.

A pipeline step raises PipelineStepError when it can't continue for a reason the
user should see (bad file, unreadable file, no technical skills — design §15). The
`message` is safe, friendly text with no internals; the orchestrator writes it to
runs.error_message and the progress UI shows it. Anything else that goes wrong is a
real bug and should surface as an ordinary exception, not this.
"""


class PipelineStepError(Exception):
    def __init__(self, message: str) -> None:
        super().__init__(message)
        self.message = message
