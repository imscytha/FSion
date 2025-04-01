from typing import Literal
from pydantic import BaseModel, Field

from fsion.models.drive import OAuthCreds


class GoogleDrive(BaseModel):
    """Configuartion model for Google Drive filesystem"""

    type: Literal["drive"] = "drive"
    drive_id: str = Field(
        ..., description="ID of the Drive you want to lookup"
    )
    credentials: OAuthCreds = Field(
        ..., description="Credentials for Google Drive"
    )


FilesystemBackend = GoogleDrive
