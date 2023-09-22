from enum import Enum
from typing import Any, Optional, Sequence, TypedDict


class ParamTypesEnum(str, Enum):
    INT = "int"
    STR = "str"
    USER = "user"
    ROLE = "role"


class FieldType(TypedDict):
    name: str
    value: str


class AuthorType(TypedDict):
    name: str
    url: Optional[str]
    icon_url: Optional[str]


class FooterType(TypedDict):
    text: str
    icon_url: Optional[str]


class ImageType(TypedDict):
    url: str


class ThumbnailType(TypedDict):
    url: str


class EmbedType(TypedDict):
    title: Optional[str]
    description: str
    url: Optional[str]
    color: Optional[int]
    fields: Sequence[FieldType]
    author: Optional[AuthorType]
    footer: Optional[FooterType]
    timestamp: Optional[str]
    image: Optional[ImageType]
    thumbnail: Optional[ThumbnailType]


class ResponseObjectType(TypedDict):
    content: Optional[str]
    embeds: Optional[Sequence[EmbedType]]


class CommandDescriptor(TypedDict):
    actions: list[int]
    param_types: list[ParamTypesEnum]
    static_params: list[list[Any]]
    res: ResponseObjectType
    delete_trigger: bool
    delete_after: Optional[int]
    is_enabled: bool
    do_format: bool
    min_role_req: Optional[int]


