from pydantic import BaseModel


class HexproofMeta(BaseModel):
    resource: str
    version: str
    date: str
    uri: str | None
