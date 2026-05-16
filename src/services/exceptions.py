class ServiceError(Exception):
    pass

class NotFoundError(ServiceError):
    pass

class ValidationError(ServiceError):
    pass

class InsufficientFundsError(ServiceError):
    pass

class AccountClosedError(ServiceError):
    pass