
import json
import inspect
from rich import print as rprint
from io import StringIO
from rich.syntax import Syntax
from rich.text import Text
from rich.box import SQUARE
from rich.panel import Panel
from rich.console import Console
from rich.highlighter import ReprHighlighter
from rich.pretty import Pretty

highlighter = ReprHighlighter()


PUBLIC = "PUBLIC"
PRIVATE = "PRIVATE"

console = Console()


class CachedObject:

    def __init__(
        self,
        obj,
        name='',
        parent_name=''
    ):
        self.obj = obj
        self.name = name
        self.parent_name = parent_name
        self.attribute_type = PUBLIC
        self.public_attribute_index = 0
        self.private_attribute_index = 0
        self.public_attribute_window = 0
        self.private_attribute_window = 0

        self.attrs = dir(self.obj)
        if '__weakref__' in self.attrs:
            # Ignore weakrefs
            self.attrs.remove('__weakref__')

        self.plain_public_attributes = sorted(
            attr for attr in self.attrs if not attr.startswith('_')
        )
        self.plain_private_attributes = sorted(
            attr for attr in self.attrs if attr.startswith('_')
        )
        self.cached_attributes = {}

        self.typeof = highlighter(str(type(self.obj)))
        self.docstring = f"[green]{self.obj.__doc__}" if self.obj.__doc__ else Pretty(None)
        self.preview = Pretty(self.obj)
        self._source = None

    @property
    def fullname(self):
        return self.parent_name + '.' +  self.name

    def cache_attributes(self):
        if not self.cached_attributes:
            for attr in self.attrs:
                self.cached_attributes[attr] = CachedObject(getattr(self.obj, attr), name=attr, parent_name=self.display_name)

    def __getitem__(self, key):
        return self.cached_attributes[key]

    @property
    def source(self):
        if not self._source:
            try:
                self._source = Syntax(inspect.getsource(self.obj), "python", line_numbers=True, background_color="default")
            except Exception as e:
                self._source = "[red italic]Source code unavailable"

        return self._source

    @property
    def display_name(self):
        return f"{self.parent_name}.{self.name}" if self.name else repr(self.obj)

    @property
    def selected_public_attribute(self) -> str:
        return self.plain_public_attributes[self.public_attribute_index]

    @property
    def selected_private_attribute(self) -> str:
        return self.plain_private_attributes[self.private_attribute_index]

    @property
    def selected_cached_attribute(self):
        if self.attribute_type == PUBLIC:
            return self[self.selected_public_attribute]

        elif self.attribute_type == PRIVATE:
            return self[self.selected_private_attribute]

    def get_current_obj_attr_panel(self) -> Panel:
        """ TODO """
        if self.attribute_type == PUBLIC:
            attribute_text = [
                Text(attr, overflow="elipses", style=f"reverse") if attr == self.selected_public_attribute
                else Text(attr, overflow="elipses")
                for attr in self.plain_public_attributes[self.public_attribute_window:]
            ]
            title = "[u]public[/u] [dim]private[/dim]"
            subtitle = f"[white]([/white][magenta]{self.public_attribute_index + 1}[/magenta][white]/[/white][magenta]{len(self.plain_public_attributes)}[/magenta][white])"

        elif self.attribute_type == PRIVATE:
            attribute_text = [
                Text(attr, overflow="elipses", style="reverse") if attr == self.selected_private_attribute
                else Text(attr, overflow="elipses")
                for attr in self.plain_private_attributes[self.private_attribute_window:]
            ]
            title = "[dim]public[/dim] [underline]private[/underline]"
            subtitle = f"[white]([/white][magenta]{self.private_attribute_index + 1}[/magenta][white]/[/white][magenta]{len(self.plain_private_attributes)}[/magenta][white])"

        renderable_text = None
        for t in attribute_text:
            if not renderable_text:
                # Start with an empty text object, all following Text objects will steal the styles from this one
                renderable_text = Text("", overflow="elipses")
            renderable_text += t + '\n'

        panel = Panel(
            renderable_text,
            title=title,
            subtitle=subtitle,
            subtitle_align="right",
            style="white"
        )

        return panel

    def move_down(self, panel_height):
        """ Move the current selection down one """
        if self.attribute_type == PUBLIC:
            if self.public_attribute_index < len(self.plain_public_attributes) - 1:
                self.public_attribute_index += 1
                if self.public_attribute_index > self.public_attribute_window + panel_height:
                    self.public_attribute_window += 1

        elif self.attribute_type == PRIVATE:
            if self.private_attribute_index < len(self.plain_private_attributes) - 1:
                self.private_attribute_index += 1
                if self.private_attribute_index > self.private_attribute_window + panel_height:
                    self.private_attribute_window += 1

    def move_up(self):
        if self.attribute_type == PUBLIC:
            if self.public_attribute_index > 0:
                self.public_attribute_index -= 1
                if self.public_attribute_index < self.public_attribute_window:
                    self.public_attribute_window -= 1

        elif self.attribute_type == PRIVATE:
            if self.private_attribute_index > 0:
                self.private_attribute_index -= 1
                if self.private_attribute_index < self.private_attribute_window:
                    self.private_attribute_window -= 1

    def move_top(self):
        if self.attribute_type == PUBLIC:
            self.public_attribute_index = 0
            self.public_attribute_window = 0

        elif self.attribute_type == PRIVATE:
            self.private_attribute_index = 0
            self.private_attribute_window = 0

    def move_bottom(self, panel_height):
        if self.attribute_type == PUBLIC:
            self.public_attribute_index = len(self.plain_public_attributes) - 1
            self.public_attribute_window = max(0, self.public_attribute_index - panel_height)

        elif self.attribute_type == PRIVATE:
            self.private_attribute_index = len(self.plain_private_attributes) - 1
            self.private_attribute_window = max(0, self.private_attribute_index - panel_height)