from asyncio import Task, create_task, ensure_future, gather, to_thread
from collections.abc import Iterable
from functools import cached_property
from logging import getLogger

from PySide6.QtCore import Property, QObject, Signal, Slot

from src._loader import AssembledTemplate, RenderableTemplate, TemplateLibrary
from src._state import PATH
from src.cards import parse_card_info
from src.enums.mtg import LayoutCategory, LayoutType, layout_map_category
from src.gui.qml.models.file_dialog_model import FileDialogModel
from src.gui.qml.models.message_dialog_content_model import MessageDialogContentModel
from src.render.render_queue import RenderQueue, cancel_with_render
from src.render.setup import prepare_render_operations
from src.utils.tests import get_template_render_test_cases, prepare_test_render

_logger = getLogger(__name__)


class TestRendersModel(QObject):
    def __init__(
        self,
        render_queue: RenderQueue,
        template_library: TemplateLibrary,
        file_dialog_model: FileDialogModel,
        message_dialog_model: MessageDialogContentModel,
        /,
        parent: QObject | None = None,
        *,
        objectName: str | None = None,
    ) -> None:
        super().__init__(parent, objectName=objectName)
        self._render_queue = render_queue
        self._template_library = template_library
        self._file_dialog_model = file_dialog_model
        self._message_dialog_model = message_dialog_model
        self._layout_categories = list(LayoutCategory)

    @cached_property
    def template_render_test_cases(self) -> dict[LayoutType, dict[str, str]]:
        return get_template_render_test_cases()

    _layout_categories_changed = Signal()

    @Property(list, notify=_layout_categories_changed)
    def layout_categories(self) -> list[LayoutCategory]:  # pyright: ignore[reportRedeclaration]
        return self._layout_categories

    async def test_render(
        self, template: RenderableTemplate, layout_category: LayoutCategory, quick: bool
    ) -> None:
        layout_types = layout_map_category[layout_category]
        for layout_type in layout_types:
            if test_cases := self.template_render_test_cases.get(layout_type, None):
                for idx, test_case in enumerate(test_cases):
                    if quick and idx > 0:
                        break

                    if render_operations := await to_thread(
                        prepare_render_operations,
                        template,
                        (parse_card_info(PATH.SRC_IMG_TEST, name_override=test_case),),
                        file_dialog=self._file_dialog_model,
                        message_dialog=self._message_dialog_model,
                    ):
                        for op in render_operations:
                            op.before_render_callback = prepare_test_render

                        self._render_queue.enqueue(*render_operations)

    def prepare_test_renders(
        self,
        templates: Iterable[AssembledTemplate],
        layout_category: LayoutCategory | None = None,
        quick: bool = False,
    ) -> list[Task[None]]:
        preparation_routines: list[Task[None]] = []
        for template in templates:
            for category in template.layout_categories:
                if not template.is_installed(category) or (
                    layout_category and not category == layout_category
                ):
                    continue

                preparation_routines.append(
                    create_task(self.test_render(template, category, quick))
                )

                if layout_category:
                    break

        return preparation_routines

    async def test_all_renders(
        self, layout_category: LayoutCategory | None = None, quick: bool = False
    ) -> None:
        preparation_routines: list[Task[None]] = self.prepare_test_renders(
            self._template_library.built_in_templates_by_name.values(),
            layout_category,
            quick,
        )
        for (
            plugin_templates
        ) in self._template_library.plugin_templates_by_name.values():
            preparation_routines += self.prepare_test_renders(
                plugin_templates.values(), layout_category, quick
            )

        _logger.info(
            f"Queueing all {
                layout_category.value + ' ' if layout_category else ''
            }tests for render."
        )
        await gather(*preparation_routines)

    @Slot(str, bool)
    def test_all(self, layout: str | None = None, quick: bool = False) -> None:
        cancel_with_render(
            ensure_future(
                self.test_all_renders(LayoutCategory(layout) if layout else None, quick)
            ),
            self._render_queue,
        )
