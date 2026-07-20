class JobCancellationRequested(Exception):
    pass


class WorkerLeaseLostError(Exception):
    pass


class RetryableJobError(Exception):
    pass


class TerminalJobError(Exception):
    pass
