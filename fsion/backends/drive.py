import io
import os
import shutil as tty
from collections.abc import Iterator
from typing import Any, Callable, Literal, final, override

from googleapiclient.http import MediaIoBaseDownload

from fsion.models.drive import (
    GoogleDriveEntry,
    OAuthCreds,
    ParamsBuilder,
    ParamsBuilderHandlers,
)
from fsion.models.fs import Filesystem, ListFlags, ReadFlags


@final
class GoogleDriveFS(Filesystem):
    def __init__(
        self,
        drive_id: str,
        credentials: OAuthCreds,
    ) -> None:
        self.drive_id: str = drive_id
        self.service = self.__builder(credentials)
        self.cwd: GoogleDriveEntry = self.__init_cwd()

    @override
    def traverse(
        self,
        root: str | None = None,
        mode: Literal["bfs", "dfs"] = "dfs",
        max_depth: int | None = None,
    ) -> Iterator[GoogleDriveEntry]:
        """Iterator that traverses a Google Drive folder recursively, yielding
            all non-folder items.

        Args:
            root: ID of the folder to traverse.
            max_depth: Maximum recursion depth. None for unlimited depth.

        Yields:
            dict: File metadata for each non-folder item.
        """

        if mode == "dfs":
            yield from self.__traverse_dfs(root, max_depth)
        elif mode == "bfs":
            yield from self.__traverse_bfs(root, max_depth)

        # NOTE: Revise traversal
        #
        # folders: list[GoogleDriveEntry] = []
        # items = self.ls(root)
        #
        # for item in items:
        #     if not item.isDir:
        #         yield item
        #     else:
        #         folders.append(item)
        #
        # for folder in folders:
        #     if max_depth is not None:
        #         if max_depth <= 0:
        #             continue
        #         next_depth = max_depth - 1
        #     else:
        #         next_depth = None
        #     yield from self.traverse(folder.id, mode, next_depth)

    def __traverse_dfs(
        self,
        root: str | None = None,
        max_depth: int | None = None,
    ) -> Iterator[GoogleDriveEntry]:
        """Depth-First Search traversal"""
        items = self.ls(root)

        for item in items:
            if not item.isDir:
                yield item
            else:
                if max_depth is not None:
                    if max_depth <= 0:
                        continue
                    next_depth = max_depth - 1
                else:
                    next_depth = None
                yield from self.__traverse_dfs(item.id, next_depth)

    def __traverse_bfs(
        self,
        root: str | None = None,
        max_depth: int | None = None,
    ) -> Iterator[GoogleDriveEntry]:
        """Breadth-First Search traversal"""

        from collections import deque

        queue = deque([(root, 0)]) if root else deque()

        while queue:
            current_root, current_depth = queue.popleft()

            if current_root is None:
                continue

            items = self.ls(current_root)

            for item in items:
                if not item.isDir:
                    yield item
                else:
                    if max_depth is not None:
                        if current_depth + 1 <= max_depth:
                            queue.append((item.id, current_depth + 1))
                    else:
                        queue.append((item.id, current_depth + 1))

    @override
    def ls(
        self,
        dir: str | None = None,
        flags: ListFlags = ListFlags.NONE,
    ) -> list[GoogleDriveEntry]:
        # TODO: define type for listParams
        def list_files(listParams: dict[str, Any]) -> list[GoogleDriveEntry]:
            return_fields = [
                "id",
                "name",
                "mimeType",
                # "createdTime",
                "modifiedTime",
                # "parents",
                # "sha256Checksum",
            ]
            default_list_params = {
                "driveId": self.drive_id,
                "includeItemsFromAllDrives": True,
                "supportsAllDrives": True,
                "corpora": "drive",
                "fields": f"nextPageToken, files({','.join(return_fields)})",
            }

            entries = []
            page_token = None

            while True:
                result = (
                    self.service.files()
                    .list(
                        **(default_list_params | listParams),
                        pageToken=page_token,
                    )
                    .execute()
                )
                entries.extend(result.get("files", []))
                page_token = result.get("nextPageToken")

                if not page_token:
                    break

            return [GoogleDriveEntry(**entry) for entry in entries]

        return self.__parse_ls_flags(dir, flags, list_files)

    def __parse_ls_flags(
        self,
        dir: str | None,
        flags: ListFlags,
        ls_callback: Callable[[dict[str, Any]], list[GoogleDriveEntry]],
    ) -> list[Any]:
        params_builder: ParamsBuilder = {
            "q": io.StringIO(),
            "orderBy": [],
        }

        dir = dir if dir else self.drive_id

        params_builder["q"].write(f"'{dir}' in parents")

        if ListFlags.ONLY_DIRS in flags:
            params_builder["q"].write(
                " and mimeType = 'application/vnd.google-apps.folder'"
            )
        if ListFlags.ONLY_FILES in flags:
            params_builder["q"].write(
                " and mimeType != 'application/vnd.google-apps.folder'"
            )

        sort_mapping = {
            ListFlags.SORT_TIME: "recency",
            ListFlags.SORT_TIME_DESC: "recency desc",
            ListFlags.SORT_NAME: "name",
            ListFlags.SORT_NAME_DESC: "name desc",
        }

        for flag, sort_value in sort_mapping.items():
            if flag in flags:
                params_builder["orderBy"].append(sort_value)

        entries = ls_callback(self.__params_builder_handlers(params_builder))

        if ListFlags.PRINT_TO_STDOUT in flags:
            term_width = tty.get_terminal_size().columns
            names = (entry.name for entry in entries)

            title = f"📁 {dir}"
            t_pad = (term_width - len(title)) // 2
            print("#" * term_width)
            print(f"{' '*t_pad}{title}{' '*t_pad}")
            print("\t".join(names))
            print("#" * term_width)

        return entries

    def __params_builder_handlers(
        self,
        params_builder: ParamsBuilder,
    ) -> dict[str, object]:
        params_builder_handlers: ParamsBuilderHandlers = {
            "q": lambda query_sb: query_sb.getvalue(),
            "orderBy": lambda orderBy_list: ", ".join(orderBy_list),
        }

        return {
            key: params_builder_handlers[key](value)
            for key, value in params_builder.items()
        }

    @override
    def read(
        self,
        file: str,
        flags: ReadFlags = ReadFlags.NONE,
    ) -> io.BytesIO | None:
        """"""

        with io.BytesIO() as fd:
            request = self.service.files().get_media(fileId=file)

            downloader = MediaIoBaseDownload(fd, request)

            done = False
            while done is False:
                status, done = downloader.next_chunk()
                if flags and ReadFlags.SHOW_PROGRESS in flags:
                    print(
                        f"\rDownload: {int(status.progress() * 100)}%.", end=""
                    )

            return fd

    def __init_cwd(self) -> GoogleDriveEntry:
        # TODO: Implement setting initial current working directory especially
        # if a drive is initially provided, we need to handle this case since
        # it requires a separate api call.
        #
        # result = self.service.drives().get(driveId=self.drive_id,).execute()
        # return GoogleDriveEntry(**result)
        ...

    def __builder(
        self,
        credentials: OAuthCreds,
    ) -> Any:
        from googleapiclient.discovery import build

        return build(
            "drive",
            "v3",
            credentials=self.__auth(credentials),
        )

    def __auth(
        self,
        credentials: OAuthCreds,
    ):
        from google.auth.transport.requests import Request
        from google.oauth2 import service_account
        from google.oauth2.credentials import Credentials
        from google_auth_oauthlib.flow import InstalledAppFlow

        creds = None
        if not (
            credentials.oauth_creds_json or credentials.service_account_json
        ):
            raise ValueError("No valid credential files provided")
        if credentials.service_account_json:
            creds = service_account.Credentials.from_service_account_file(
                credentials.service_account_json
            )
        else:
            if os.path.exists(credentials.token_filepath):
                creds = Credentials.from_authorized_user_file(
                    credentials.token_filepath, credentials.scopes
                )

            if not creds or not creds.valid:
                if creds and creds.expired and creds.refresh_token:
                    creds.refresh(Request())
                else:
                    flow = InstalledAppFlow.from_client_secrets_file(
                        credentials.oauth_creds_json, credentials.scopes
                    )
                    creds = flow.run_local_server(port=0)

                with open(credentials.token_filepath, "w") as token:
                    token.write(creds.to_json())

        return creds
