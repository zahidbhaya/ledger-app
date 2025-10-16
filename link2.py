# ---------------- scrollable_table_uniform.py ----------------
from kivy.config import Config
Config.set('graphics', 'orientation', 'portrait')
Config.set('graphics', 'width', '450')
Config.set('graphics', 'height', '750')

from kivy.app import App
from kivy.uix.label import Label
from kivy.uix.scrollview import ScrollView
from kivy.uix.gridlayout import GridLayout
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.button import Button
from kivy.uix.textinput import TextInput
from kivy.graphics import Color, Rectangle, Line
from kivy.properties import NumericProperty
from kivy.effects.scroll import ScrollEffect
from kivy.core.window import Window

# ---------------- Styled Button ----------------
def styled_button(text, height=50):
    return Button(
        text=text,
        size_hint_y=None,
        height=height,
        color=(1,1,1,1),
        background_normal='',
        background_color=(0.2,0.6,0.9,1)
    )

# ---------------- Safe TextInput ----------------
class SafeTextInput(TextInput):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.foreground_color = (0.1,0.1,0.1,1)
        self.background_color = (0.95,0.95,0.95,1)

# ---------------- BorderedCell ----------------
class BorderedCell(Label):
    row_height = NumericProperty(40)
    def __init__(self, text="", col_width=100, bold=False, is_header=False, row_height=None, **kwargs):
        super().__init__(text=text, **kwargs)

        # Colors
        header_bg = (0.15,0.3,0.5,1)
        header_text = (1,1,1,1)
        cell_bg = (0.95,0.95,0.9,1)
        cell_text = (0.05,0.05,0.05,1)

        if is_header:
            self.bg_color = header_bg
            self.color = header_text
            self.bold = True
        else:
            self.bg_color = cell_bg
            self.color = cell_text
            self.bold = bold

        self.size_hint_y = None
        self.height = row_height or self.row_height
        self.text_size = (col_width-10, None)
        self.halign = "center"
        self.valign = "middle"
        self.col_width = col_width

        # Draw background and border
        with self.canvas.before:
            Color(*self.bg_color)
            self.rect = Rectangle(pos=self.pos, size=self.size)
            Color(0,0,0,1)
            self.line = Line(rectangle=(self.x,self.y,col_width,self.height), width=1)

        self.bind(pos=self.update_graphics, size=self.update_graphics)

    def update_graphics(self, *args):
        self.rect.pos = self.pos
        self.rect.size = self.size
        self.line.rectangle = (self.x,self.y,self.width,self.height)

# ---------------- ScrollableTable ----------------
class ScrollableTable(ScrollView):
    def __init__(self, cols=6, headers=None, **kwargs):
        super().__init__(**kwargs)
        self.do_scroll_x = False
        self.do_scroll_y = True
        self.bar_width = 10
        self.scroll_type = ['bars','content']
        self.scroll_wheel_distance = 20
        self.effect_y = ScrollEffect()

        self.cols = cols
        self.layout = GridLayout(cols=cols, spacing=2, size_hint_y=None)
        self.layout.bind(minimum_height=self.layout.setter('height'))
        self.add_widget(self.layout)

        if headers:
            for h in headers:
                self.layout.add_widget(BorderedCell(text=h, bold=True, col_width=100, is_header=True))

        Window.bind(on_key_down=self._on_key_down)

    def add_row(self, row_data):
        print(f"Adding row: {row_data}")  # ✅ debug print
        max_height = 40

        # Determine max height for the row
        for item in row_data:
            lbl = Label(text=str(item), text_size=(100-10, None))
            lbl.texture_update()
            h = lbl.texture_size[1]+20
            if h > max_height:
                max_height = h

        # Add actual BorderedCell widgets
        for item in row_data:
            cell = BorderedCell(text=str(item), col_width=100, row_height=max_height)
            self.layout.add_widget(cell)

        # Update total layout height
        self.layout.height = sum(child.height for child in self.layout.children)

    def _on_key_down(self, window, key, scancode, codepoint, modifiers):
        step = 0.05
        if key in [273, ord('w')]:
            self.scroll_y = min(1, self.scroll_y + step)
        elif key in [274, ord('s')]:
            self.scroll_y = max(0, self.scroll_y - step)

# ----------------- Test App -----------------
class TestApp(App):
    def build(self):
        print("Building TestApp...")  # ✅ debug print
        root = BoxLayout(orientation='vertical')

        headers = ["Name", "Mobile", "Detail", "Amount/hour", "Amount deposited", "Pending"]
        self.table = ScrollableTable(cols=6, headers=headers)
        root.add_widget(self.table)

        # Add some test rows
        self.table.add_row(["John Doe", "1234567890", "Some very long detail that needs wrapping", "100", "50", "50"])
        self.table.add_row(["Jane Smith", "0987654321", "Short detail", "80", "80", "0"])
        self.table.add_row(["Ali Bhaya", "5556667777", "Another very long detail that will expand row", "200", "150", "50"])

        return root

if __name__ == "__main__":
    TestApp().run()
