"""Business errors. Each one already knows which HTTP status code it represents."""


class BusinessError(Exception):
    status = 400


class ValidationError(BusinessError):
    status = 400


class NotFound(BusinessError):
    status = 404


class Conflict(BusinessError):
    status = 409
