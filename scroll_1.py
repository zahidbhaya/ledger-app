# scroll_1.py
from kivy.uix.scrollview import ScrollView
from kivy.uix.gridlayout import GridLayout
from kivy.uix.label import Label
from kivy.graphics import Color, Rectangle, Line
from kivy.properties import NumericProperty
from kivy.effects.scroll import ScrollEffect

# ---------------- BorderedCell ----------------
class BorderedCell(Label):
    row_height = NumericProperty(40)
    def __init__(self, text="", col_width=100, bold=False, header=False, **kwargs):
        if header:
            super().__init__(text=text, bold=True, color=(1,1,1,1), **kwargs)
            self.bg_color = (0.2,0.2,0.2,1)
        else:
            super().__init__(text=text, bold=bold, color=(0.1,0.1,0.1,1), **kwargs)
            self.bg_color = (0.95,0.95,0.95,1)

        self.size_hint_y = None
        self.height = self.row_height
        self.text_size = (col_width-10, None)
        self.halign = "center"
        self.valign = "middle"
        self.col_width = col_width

        with self.canvas.before:
            Color(*self.bg_color)
            self.rect = Rectangle(pos=self.pos, size=self.size)
            Color(0,0,0,1)
            self.line = Line(rectangle=(self.x, self.y, col_width, self.height), width=1)
        self.bind(pos=self.update_graphics, size=self.update_graphics)

    def update_graphics(self, *args):
        self.rect.pos = self.pos
        self.rect.size = self.size
        self.line.rectangle = (self.x, self.y, self.width, self.height)


# ---------------- ScrollableTable ----------------
class ScrollableTable(ScrollView):
    def __init__(self, cols=6, headers=None, col_widths=None, **kwargs):
        super().__init__(**kwargs)
        self.do_scroll_x = False
        self.do_scroll_y = True
        self.bar_width = 10
        self.scroll_type = ['bars','content']
        self.effect_y = ScrollEffect()

        self.cols = cols
        self.col_widths = col_widths if col_widths else [100]*cols

        self.layout = GridLayout(cols=cols, spacing=2, size_hint_y=None)
        self.layout.bind(minimum_height=self.layout.setter('height'))
        self.add_widget(self.layout)

        if headers:
            for i,h in enumerate(headers):
                w = self.col_widths[i] if i < len(self.col_widths) else 100
                self.layout.add_widget(BorderedCell(text=h, bold=True, col_width=w, header=True))

    def add_row(self, row_items):
        max_height = 40
        for i, item in enumerate(row_items):
            temp_label = Label(text=str(item), text_size=(self.col_widths[i]-10,None),
                               size_hint_y=None, halign="center", valign="middle")
            temp_label.texture_update()
            cell_height = temp_label.texture_size[1]+20
            if cell_height>max_height:
                max_height = cell_height
        for i, item in enumerate(row_items):
            cell = BorderedCell(text=str(item), col_width=self.col_widths[i], row_height=max_height)
            self.layout.add_widget(cell)
        self.layout.height = sum(child.height for child in self.layout.children)

    def clear(self):
        self.layout.clear_widgets()

