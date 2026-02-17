from asyncio import ensure_future, gather, to_thread
from functools import cached_property

from pydantic import BaseModel
from PySide6.QtCore import Property, QObject, Signal, Slot

from src._loader import AppTemplate, TemplateLibrary
from src._state import AppEnvironment
from src.enums.mtg import LayoutCategory
from src.gui.qml.models.pydantic_q_list_model import PydanticQListModel
from src.utils.hexapi import check_api_keys


class DownloadableTemplateDetails(BaseModel):
    file_name: str
    google_drive_id: str | None
    img: str
    plugin: str
    template_names: list[str]
    template_classes: list[str]
    layout_categories: list[LayoutCategory]
    installed_version: str
    available_version: str
    download_size: int
    """bytes"""
    downloading: bool = False

    @cached_property
    def handler(self) -> AppTemplate:
        raise ValueError("Download handler is not specified")


class TemplateUpdaterModel(PydanticQListModel[DownloadableTemplateDetails]):
    item_model = DownloadableTemplateDetails

    def __init__(
        self,
        app_env: AppEnvironment,
        template_library: TemplateLibrary,
        parent: QObject | None = None,
        items: list[DownloadableTemplateDetails] = [],
        selected_index: int = -1,
    ) -> None:
        self._app_env = app_env
        self._template_library = template_library

        self._fetching_data = False

        super().__init__(parent, items, selected_index)

    _fetching_data_changed = Signal(name="fetchingDataChanged")

    @Property(bool, notify=_fetching_data_changed)
    def fetching_data(self) -> bool:  # pyright: ignore[reportRedeclaration]
        return self._fetching_data

    @fetching_data.setter
    def fetching_data(self, value: bool) -> None:
        if value != self._fetching_data:
            self._fetching_data = value
            self._fetching_data_changed.emit()

    @Slot()
    def fetch_data(self) -> None:
        ensure_future(self._handle_fetch_data())

    async def _handle_fetch_data(self) -> None:
        self.fetching_data = True  # pyright: ignore[reportAttributeAccessIssue]

        await check_api_keys(self._app_env)

        await gather(
            *[
                to_thread(template.check_for_update)
                for template in self._template_library.templates
            ]
        )

        self.beginResetModel()
        self.items = [
            DownloadableTemplateDetails(
                file_name=template.file_name,
                google_drive_id=template.google_drive_id,
                img=str(
                    template.get_path_preview(
                        class_name=(
                            first_item := next(
                                iter(template.all_classes_and_layouts.items())
                            )
                        )[0],
                        class_type=first_item[1][0],
                    ).as_uri()
                ),
                plugin=template.plugin.id if template.plugin else "",
                template_names=template.all_names,
                template_classes=template.all_classes,
                layout_categories=template.supported_layout_categories,
                installed_version=template.version or "",
                available_version=template.update_version or "",
                download_size=template.update_size or 0,
            )
            for template in self._template_library.templates
        ]
        for item, template in zip(self.items, self._template_library.templates):
            item.handler = template
        self.selected_index = 0  # pyright: ignore[reportAttributeAccessIssue]
        self.endResetModel()

        self.fetching_data = False  # pyright: ignore[reportAttributeAccessIssue]

    @Slot(int)
    def download_template(self, index: int) -> None:
        if index < 0 or index >= self.rowCount():
            return

        ensure_future(self._handle_template_download(index))

    async def _handle_template_download(self, index: int) -> None:
        item = self.items[index]
        q_index = self.createIndex(index, 0)

        item.downloading = True
        changed_fields: list[int] = [self.get_role("downloading")]
        self.dataChanged.emit(q_index, q_index, changed_fields)
        if await to_thread(item.handler.update_template):
            item.installed_version = item.handler.version or ""
            changed_fields.append(self.get_role("installed_version"))
        item.downloading = False
        self.dataChanged.emit(q_index, q_index, changed_fields)

    @Slot()
    def save_versions(self) -> None:
        self._template_library.save_template_versions()
