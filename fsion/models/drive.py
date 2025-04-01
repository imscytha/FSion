import io
import json
from datetime import datetime
from hashlib import sha256
from typing import Callable, TypedDict

from pydantic import BaseModel, model_validator


class OAuthCreds(BaseModel):
    scopes: list[str]
    oauth_creds_json: str | None = None
    service_account_json: str | None = None
    token_filepath: str = "token.json"

    @model_validator(mode="after")
    def oauth_filepath_validator(self):
        if not (self.oauth_creds_json or self.service_account_json):
            raise ValueError("You need to provide at least one.")
        return self


# TODO: Currently the `Filesystem` interface is intentionally using
# GoogleDriveEntry model directly.
# We need to design a common model for polling filesystem entries that is
# independent of Google Drive and other backends specific implementations.
class GoogleDriveEntry(BaseModel):
    id: str
    name: str
    mimeType: str
    parents: list[str] | None = None
    createdTime: datetime | None = None
    modifiedTime: datetime | None = None
    sha256Checksum: str | None = None

    @property
    def isDir(self) -> bool:
        return self.mimeType == "application/vnd.google-apps.folder"

    @property
    def digest(self) -> str:
        return sha256(
            json.dumps(self.model_dump(mode="json"), sort_keys=True).encode()
        ).hexdigest()


class ParamsBuilder(TypedDict):
    q: io.StringIO
    orderBy: list[str]


class ParamsBuilderHandlers(TypedDict):
    q: Callable[[io.StringIO], str]
    orderBy: Callable[[list[str]], str]
