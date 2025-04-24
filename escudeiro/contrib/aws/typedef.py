from escudeiro.misc import ValueEnum, SnakeEnum


class Methods(ValueEnum):
    GET = "GET"
    HEAD = "HEAD"
    POST = "POST"
    PUT = "PUT"
    PATCH = "PATCH"
    DELETE = "DELETE"


GET = Methods.GET
HEAD = Methods.HEAD
POST = Methods.POST
PUT = Methods.PUT
PATCH = Methods.PATCH
DELETE = Methods.DELETE


class Services(ValueEnum, SnakeEnum):
    S3 = "s3"
