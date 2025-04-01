from fsion.backends.drive import GoogleDriveFS
from fsion.models.fs import Filesystem
from fsion.models.fs.backend import FilesystemBackend, GoogleDrive


class FilesystemFactory:
    def create(
        self,
        backend: FilesystemBackend,
    ) -> Filesystem:
        if isinstance(backend, GoogleDrive):
            return GoogleDriveFS(backend.drive_id, backend.credentials)
        else:
            # TODO: Implement other backends
            raise NotImplementedError
