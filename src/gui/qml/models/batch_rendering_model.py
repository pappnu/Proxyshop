from asyncio import Task, create_task, ensure_future, gather, to_thread
from functools import cached_property
from logging import getLogger
from pathlib import Path
from typing import override
from urllib.request import url2pathname

from pydantic import BaseModel, RootModel, ValidationError
from PySide6.QtCore import QModelIndex, QObject, QPersistentModelIndex, QUrl, Slot

from src._loader import (
    AppPlugin,
    AssembledTemplate,
    AssembledTemplateInstalledArgs,
    RenderableTemplate,
    TemplateLibrary,
)
from src.enums.mtg import LayoutCategory
from src.gui.qml.models.file_dialog_model import FileDialogModel
from src.gui.qml.models.message_dialog_content_model import MessageDialogContentModel
from src.gui.qml.models.pydantic_q_list_model import PydanticQListModel
from src.gui.qml.models.test_renders_model import TestRendersModel
from src.render.render_queue import RenderQueue, cancel_with_render
from src.render.setup import prepare_render_operations
from src.utils.images import match_images_with_data_files

_logger = getLogger(__name__)


class TemplateOption(BaseModel):
    name: str
    plugin: str
    is_installed: bool
    preview_img_path: str

    @cached_property
    def full_name(self) -> str:
        return self.name + (f" ({self.plugin})" if self.plugin else "")


class LayoutCategoryItem(BaseModel):
    name: str
    options_details: list[TemplateOption]
    options: list[str]
    options_installed: list[bool]
    options_preview_img_path: list[str]
    selected: int


class _TemplateSelectionPreferences(RootModel[dict[str, str]]):
    root: dict[str, str] = {}


class BatchRenderingModel(PydanticQListModel[LayoutCategoryItem]):
    item_model = LayoutCategoryItem

    def __init__(
        self,
        file_dialog_model: FileDialogModel,
        message_dialog_model: MessageDialogContentModel,
        render_queue: RenderQueue,
        plugins: dict[str, AppPlugin],
        template_library: TemplateLibrary,
        test_renders_model: TestRendersModel,
        parent: QObject | None = None,
        selected_index: int = -1,
    ) -> None:
        self._file_dialog_model = file_dialog_model
        self._message_dialog_model = message_dialog_model
        self._render_queue = render_queue
        self._test_renders_model = test_renders_model

        self.built_in_templates_by_layout: dict[
            LayoutCategory, dict[str, AssembledTemplate]
        ] = {}
        self.plugin_templates_by_layout: dict[
            LayoutCategory, dict[str, dict[str, AssembledTemplate]]
        ] = {}
        """dict[layout, dict[plugin, dict[template_name, template]]]"""

        for layout_category in LayoutCategory:
            self.built_in_templates_by_layout.setdefault(layout_category, {})
            self.plugin_templates_by_layout.setdefault(
                layout_category, {plugin.id: {} for plugin in plugins.values()}
            )

        for name, template in template_library.built_in_templates_by_name.items():
            for layout_category in template.layout_categories:
                self.built_in_templates_by_layout[layout_category][name] = template

            template.template_installed.add_listener(self._on_template_installed)

        for plugin, templates in template_library.plugin_templates_by_name.items():
            for name, template in templates.items():
                for layout_category in template.layout_categories:
                    self.plugin_templates_by_layout[layout_category].setdefault(
                        plugin, {}
                    )
                    self.plugin_templates_by_layout[layout_category][plugin][name] = (
                        template
                    )

                template.template_installed.add_listener(self._on_template_installed)

        layout_cat_items: list[LayoutCategoryItem] = []
        for (
            layout_category,
            template_options,
        ) in self.built_in_templates_by_layout.items():
            opts = [
                TemplateOption(
                    name=opt_name,
                    plugin="",
                    is_installed=opt.is_installed(layout_category),
                    preview_img_path=path.as_uri()
                    if (path := opt.get_preview_image_path(layout_category))
                    else "",
                )
                for opt_name, opt in template_options.items()
            ]

            for plugin, plugin_opts in self.plugin_templates_by_layout[
                layout_category
            ].items():
                for opt_name, opt in plugin_opts.items():
                    opts.append(
                        TemplateOption(
                            name=opt_name,
                            plugin=plugin,
                            is_installed=opt.is_installed(layout_category),
                            preview_img_path=path.as_uri()
                            if (path := opt.get_preview_image_path(layout_category))
                            else "",
                        )
                    )

            layout_cat_item = LayoutCategoryItem(
                name=layout_category,
                selected=-1,
                options_details=opts,
                options=[opt.full_name for opt in opts],
                options_installed=[opt.is_installed for opt in opts],
                options_preview_img_path=[opt.preview_img_path for opt in opts],
            )
            layout_cat_items.append(layout_cat_item)

        super().__init__(parent, layout_cat_items, selected_index)

    @override
    def columnCount(self, parent: QModelIndex | QPersistentModelIndex) -> int:
        return 2

    @property
    def template_choices(self) -> dict[LayoutCategory, RenderableTemplate]:
        template_choices: dict[LayoutCategory, RenderableTemplate] = {}
        for item in self.items:
            if item.selected < 0:
                continue

            selected_opt = item.options_details[item.selected]

            if not selected_opt.is_installed:
                continue

            layout_category = LayoutCategory(item.name)
            if selected_opt.plugin:
                template_choices[layout_category] = self.plugin_templates_by_layout[
                    layout_category
                ][selected_opt.plugin][selected_opt.name]
            else:
                template_choices[layout_category] = self.built_in_templates_by_layout[
                    layout_category
                ][selected_opt.name]
        return template_choices

    # layout, selected index
    @Slot(int, int)
    def select_template_for_layout(
        self, layout_category_idx: int, selected_index: int
    ) -> None:
        item = self.items[layout_category_idx]
        item.selected = selected_index
        q_idx = self.createIndex(layout_category_idx, 0)
        self.dataChanged.emit(q_idx, q_idx, [self.get_role("selected")])

    def render_files(self, paths: list[Path]) -> None:
        if paths:
            _logger.info(
                f"Queueing {
                    len(paths)
                } batch mode entries for render. Do note that the actual amount of renders might be lower if you selected JSON files or art for split cards."
            )
            if render_operations := prepare_render_operations(
                self.template_choices,
                match_images_with_data_files(paths),
                file_dialog=self._file_dialog_model,
                message_dialog=self._message_dialog_model,
            ):
                self._render_queue.enqueue(*render_operations)

    @Slot()
    def render_selections(self) -> None:
        async def action():
            # Choose images
            selections = await self._file_dialog_model.select_images(
                dialog_id="batch_mode_render",
                filters=[
                    FileDialogModel.IMAGES_AND_JSON_FILTER,
                    FileDialogModel.ALL_FILTER,
                ],
            )

            self.render_files(selections)

        cancel_with_render(ensure_future(action()), self._render_queue)

    @Slot("QVariantList")
    def render_targets(self, urls: list[QUrl]) -> None:
        paths: list[Path] | None = None
        try:
            paths = [Path(url2pathname(url.path())) for url in urls]
        except Exception:
            _logger.exception("Failed to process drag & dropped files.")
        if paths:
            cancel_with_render(
                ensure_future(to_thread(self.render_files, paths)), self._render_queue
            )

    @Slot(str, bool)
    def test_render(self, layout: str | None = None, quick: bool = False) -> None:
        async def action() -> None:
            layout_category = LayoutCategory(layout) if layout else None

            preparation_routines: list[Task[None]] = []
            for category, template in self.template_choices.items():
                if layout_category and category != layout_category:
                    continue

                preparation_routines.append(
                    create_task(
                        self._test_renders_model.test_render(template, category, quick)
                    )
                )

                if layout_category:
                    break

            _logger.info(
                f"Queueing {
                    layout_category.value + ' ' if layout_category else ''
                }tests for batch mode selections."
            )
            await gather(*preparation_routines)

        cancel_with_render(ensure_future(action()), self._render_queue)

    @Slot(result=str)
    def get_template_selections_json(self) -> str:
        selections = _TemplateSelectionPreferences()
        for item in self.items:
            if item.selected > -1:
                selections.root[item.name] = item.options[item.selected]
        return selections.model_dump_json() if selections.root else ""

    @Slot(str)
    def restore_template_selections(self, data: str) -> None:
        try:
            parsed_data = _TemplateSelectionPreferences.model_validate_json(data).root
            for item_idx, item in enumerate(self.items):
                if selection := parsed_data.get(item.name):
                    for idx, opt in enumerate(item.options):
                        if opt == selection:
                            item.selected = idx
                            q_idx = self.index(item_idx, 0)
                            self.dataChanged.emit(q_idx, q_idx, ["selected"])
        except ValidationError:
            _logger.exception("Failed to restore batch model selection preferences.")

    @Slot(result="QVariantList")
    def layout_names(self) -> list[str]:
        return [item.name for item in self.items]

    def _on_template_installed(
        self, event_args: AssembledTemplateInstalledArgs
    ) -> None:
        origin = event_args["origin"]
        for idx, item in enumerate(self.items):
            for opt_idx, opt in enumerate(item.options_details):
                if (
                    opt.plugin if origin.plugin else not opt.plugin
                ) and opt.name in origin.named_templates:
                    opt.is_installed = True
                    item.options_installed[opt_idx] = True
                    q_idx = self.createIndex(idx, 0)
                    self.dataChanged.emit(
                        q_idx, q_idx, [self.get_role("options_installed")]
                    )
