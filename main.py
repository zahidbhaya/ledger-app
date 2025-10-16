import sys, traceback, os
if os.environ.get("FLASK_RUN_FROM_CLI"):
    # Skip all Kivy code when Flask runs
    raise ImportError("Skip Kivy when running Flask")

#from kivy.app import App
#from kivy.uix.label import Label

def handle_exception(exc_type, exc_value, exc_traceback):
    # format the traceback
    tb_str = "".join(traceback.format_exception(exc_type, exc_value, exc_traceback))

    # save to a file in the app's private storage
    try:
        from kivy.utils import platform
        if platform == "android":
            from android.storage import app_storage_path
            log_dir = app_storage_path()
        else:
            log_dir = os.getcwd()
        with open(os.path.join(log_dir, "ledger_error.log"), "a", encoding="utf-8") as f:
            f.write("\n\n=== Crash ===\n")
            f.write(tb_str)
    except Exception as e:
        print("Failed to write error log:", e)

    # also print to logcat
    print("=== Unhandled Exception ===")
    print(tb_str)

    # optional: replace app UI with the error message
    try:
        app = App.get_running_app()
        if app:
            app.root.clear_widgets()
            app.root.add_widget(Label(text="Error:\n" + tb_str[-500:]))  # show last 500 chars
    except Exception:
        pass

# install global exception hook
sys.excepthook = handle_exception
# ---------------- main.py ----------------
from kivy.config import Config
Config.set('graphics', 'orientation', 'portrait')
Config.set('graphics', 'width', '400')
Config.set('graphics', 'height', '700')

from kivy.app import App
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.gridlayout import GridLayout
from kivy.uix.button import Button
from kivy.uix.label import Label
from kivy.uix.scrollview import ScrollView
from kivy.uix.popup import Popup
from kivy.graphics import Color, Rectangle, RoundedRectangle
from functools import partial
from datetime import datetime

from save_page2_pdf import save_page2_table_as_pdf
from save_clients_pdf import save_clients_as_pdf
from scrollable_table_uniform import ScrollableTable, styled_button, SafeTextInput
from remove_popup import RemovePopup

# ---------------- Title Widget ----------------
class TitleWithShadow(BoxLayout):
    def __init__(self, **kwargs):
        super().__init__(orientation="vertical", **kwargs)

        with self.canvas.before:
            Color(0.4, 0.2, 0.2, 0.6)  # background shadow
            self.rect = Rectangle(size=self.size, pos=self.pos)
        self.bind(pos=self._update_rect, size=self._update_rect)

        self.add_widget(Label(
            text="LEDg3R\nbY\nz.A.BhaYa...!",
            font_name="Suissnord.otf",  # must exist in folder
            font_size="50sp",
            halign="center",
            valign="middle",
            color=(.9, 0.84, 0.4, 0.8),  # golden
            size_hint=(1, None),
            height=225
        ))

    def _update_rect(self, *args):
        self.rect.pos = self.pos
        self.rect.size = self.size


# ---------------- Page1 ----------------
class Page1(BoxLayout):
    def __init__(self, main_app, **kwargs):
        super().__init__(orientation='vertical', padding=8, spacing=8, **kwargs)
        self.main_app = main_app
        self.clients = main_app.clients

        # Background
        with self.canvas.before:
            Color(0.9, 0.7, 0.9, 0.7)
            self.bg_rect = Rectangle(size=self.size, pos=self.pos)
        self.bind(size=self._update_bg, pos=self._update_bg)

        # Header
        header = BoxLayout(orientation='vertical',
                           padding=[10, 15],
                           spacing=8,
                           size_hint_y=None,
                           height=300)
        with header.canvas.before:
            Color(0.15, 0.22, 0.3, 0.6)
            header._bg = RoundedRectangle(pos=header.pos,
                                          size=header.size,
                                          radius=[20, 20, 20, 20])
        header.bind(pos=lambda w, v: setattr(header._bg, 'pos', w.pos),
                    size=lambda w, v: setattr(header._bg, 'size', w.size))
        header.add_widget(TitleWithShadow())
        self.add_widget(header)

        # Controls
        controls = BoxLayout(orientation='vertical', spacing=8, padding=12)
        with controls.canvas.before:
            Color(1, 1, 1, 0.08)
            controls._bg = RoundedRectangle(pos=controls.pos, size=controls.size, radius=[16, 16, 16, 16])
        controls.bind(pos=lambda w, v: setattr(controls._bg, 'pos', w.pos),
                      size=lambda w, v: setattr(controls._bg, 'size', w.size))

        # Registration
        reg_layout = BoxLayout(size_hint_y=None, height=50, spacing=6)
        self.reg_name = SafeTextInput(hint_text="Name", multiline=False, size_hint_x=0.4)
        self.reg_mobile = SafeTextInput(hint_text="Mobile", multiline=False, size_hint_x=0.4)
        reg_btn = Button(text="Register", size_hint_x=0.2)
        reg_btn.bind(on_press=self.register_client)
        reg_layout.add_widget(self.reg_name)
        reg_layout.add_widget(self.reg_mobile)
        reg_layout.add_widget(reg_btn)

        # Search
        search_layout = BoxLayout(size_hint_y=None, height=50, spacing=6)
        self.search_input = SafeTextInput(hint_text="Search by Name or Mobile", multiline=False, size_hint_x=0.8)
        search_btn = Button(text="Search", size_hint_x=0.2)
        search_btn.bind(on_press=self.search_client)
        search_layout.add_widget(self.search_input)
        search_layout.add_widget(search_btn)

        # Download / Show list buttons
        download_btn = Button(text="Download Clients List", size_hint_y=None, height=50,
                              background_color=(0.2, 0.6, 0.2, 1), color=(1, 1, 1, 1))
        download_btn.bind(on_press=self.download_clients_pdf)

        show_list_btn = Button(text="Show Clients List", size_hint_y=None, height=50,
                               background_color=(0.2, 0.4, 0.6, 1), color=(1, 1, 1, 1))
        show_list_btn.bind(on_press=self.toggle_client_list)

        controls.add_widget(reg_layout)
        controls.add_widget(search_layout)
        controls.add_widget(download_btn)
        controls.add_widget(show_list_btn)
        self.add_widget(controls)

        # Client Table (hidden initially)
        headers = ["Name", "Mobile"]
        self.client_table = ScrollableTable(cols=2, headers=headers, size_hint_y=None, height=0)
        self.add_widget(self.client_table)

    # --- helpers ---
    def _update_bg(self, *args):
        self.bg_rect.size = self.size
        self.bg_rect.pos = self.pos

    def register_client(self, instance):
        name = self.reg_name.text.strip()
        mobile = self.reg_mobile.text.strip()
        if not name or not mobile:
            print("Name and Mobile required")
            return
        if mobile in self.clients:
            print("Mobile already registered")
            return
        self.clients[mobile] = {'name': name, 'ledger': []}
        print(f"Registered {name} ({mobile})")
        self.clear_inputs()

    def search_client(self, instance):
        query = self.search_input.text.strip().lower()
        results = [(mob, data['name']) for mob, data in self.clients.items()
                   if query in mob or query in data['name'].lower()]

        if not results:
            print("No results found")
            return

        if query.isdigit() and len(results) == 1:
            mobile, _ = results[0]
            self.main_app.show_page2(mobile)
            return

        if len(results) > 1 and not query.isdigit():
            self.show_selection_list(results)
            return

        mobile, _ = results[0]
        self.main_app.show_page2(mobile)

    def show_selection_list(self, results):
        layout = BoxLayout(orientation="vertical", spacing=5, padding=5)
        scroll = ScrollView(size_hint=(1, 1))
        grid = GridLayout(cols=1, spacing=5, size_hint_y=None)
        grid.bind(minimum_height=grid.setter('height'))

        for mobile, name in results:
            btn = Button(text=f"{name}  ({mobile})", size_hint_y=None, height=40)
            btn.bind(on_release=partial(self.open_client_from_list, mobile))
            grid.add_widget(btn)

        scroll.add_widget(grid)
        layout.add_widget(scroll)

        close_btn = Button(text="Close", size_hint_y=None, height=40)
        layout.add_widget(close_btn)

        popup = Popup(title="Select Client", content=layout, size_hint=(0.9, 0.9))
        close_btn.bind(on_release=popup.dismiss)
        popup.open()
        self._popup = popup

    def open_client_from_list(self, mobile, instance):
        if hasattr(self, "_popup"):
            self._popup.dismiss()
        self.main_app.show_page2(mobile)

    def download_clients_pdf(self, instance):
        if not self.clients:
            print("No clients registered yet.")
            return
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"Clients_List_{timestamp}.pdf"
        save_clients_as_pdf(self.clients, filename)
        print(f"Clients PDF saved as {filename}")

    def toggle_client_list(self, instance):
        if self.client_table.height == 0:
            self.refresh_client_table()
        else:
            self.client_table.height = 0

    def refresh_client_table(self):
        self.client_table.layout.clear_widgets()
        self.client_table.add_row(["Name", "Mobile"])
        for mobile, data in self.clients.items():
            self.client_table.add_row([data['name'], mobile])
        self.client_table.height = sum(child.height for child in self.client_table.layout.children)

    def clear_inputs(self):
        self.reg_name.text = ""
        self.reg_mobile.text = ""
        self.search_input.text = ""


# ---------------- Page2 (same as before) ----------------
class Page2(BoxLayout):
    def __init__(self, main_app, client_mobile, **kwargs):
        super().__init__(orientation='vertical', padding=5, spacing=5, **kwargs)
        self.main_app = main_app
        self.client_mobile = client_mobile
        self.clients = main_app.clients
        client = self.clients[self.client_mobile]

        # --- Background ---
        with self.canvas.before:
            Color(0.9, 0.7, 0.9, 0.7)  # light purple
            self.bg_rect = Rectangle(size=self.size, pos=self.pos)
        self.bind(size=self._update_bg, pos=self._update_bg)

        # --- Heading ---
        heading = Label(
            text=f"{client['name']} ({self.client_mobile})",
            size_hint_y=None,
            height=40,
            bold=True,
            color=(0.1, 0.1, 0.1, 1)  # dark text for contrast
        )
        self.add_widget(heading)

        # --- Entry layout ---
        entry_layout = GridLayout(cols=4, spacing=5, size_hint_y=None, height=40)
        self.date_input = SafeTextInput(hint_text="Date", multiline=False)
        self.detail_input = SafeTextInput(hint_text="Detail", multiline=False)
        self.amount_hour_input = SafeTextInput(hint_text="Amount/hour", multiline=False)
        self.amount_deposit_input = SafeTextInput(hint_text="Amount deposited", multiline=False)
        for inp in [self.date_input, self.detail_input, self.amount_hour_input, self.amount_deposit_input]:
            inp.size_hint_x = 1
            entry_layout.add_widget(inp)
        self.add_widget(entry_layout)

        # --- Add entry button ---
        add_btn = styled_button("Add Entry")
        add_btn.bind(on_press=self.add_entry)
        self.add_widget(add_btn)

        # --- Ledger table ---
        headers = ["Sr", "Date", "Detail", "Amount/hour", "Amount deposited", "Pending"]
        self.table = ScrollableTable(cols=6, headers=headers)
        self.add_widget(self.table)

        # --- Buttons layout ---
        buttons_layout = BoxLayout(size_hint_y=None, height=50, spacing=5)
        back_btn = styled_button("Back to Page1")
        back_btn.bind(on_press=lambda x: self.main_app.show_page1())
        download_btn = styled_button("Download PDF")
        download_btn.bind(on_press=self.download_pdf)
        buttons_layout.add_widget(back_btn)
        buttons_layout.add_widget(download_btn)
        self.add_widget(buttons_layout)

        # Show existing ledger entries
        self.show_table()

    # --- Background update ---
    def _update_bg(self, *args):
        self.bg_rect.size = self.size
        self.bg_rect.pos = self.pos

    # --- Add ledger entry ---
    def add_entry(self, instance):
        ledger = self.clients[self.client_mobile]['ledger']
        sr = str(len(ledger) + 1)
        date = self.date_input.text
        detail = self.detail_input.text
        try:
            amount_hour = float(self.amount_hour_input.text)
        except:
            amount_hour = 0.0
        try:
            amount_deposit = float(self.amount_deposit_input.text)
        except:
            amount_deposit = 0.0
        pending = amount_deposit - amount_hour
        row = [sr, date, detail, str(amount_hour), str(amount_deposit), str(pending)]
        ledger.append(row)
        self.clear_inputs()
        self.show_table()

    # --- Show table ---
    def show_table(self):
        self.table.layout.clear_widgets()
        headers = ["Sr", "Date", "Detail", "Amount/hour", "Amount deposited", "Pending"]
        self.table.add_row(headers)

        ledger = self.clients[self.client_mobile]['ledger']
        for idx, row in enumerate(ledger):
            self.table.add_row(row)
            try:
                sr_cell = self.table.layout.children[5]
                sr_cell.bind(on_touch_down=partial(self._on_sr_touch, idx))
            except Exception as e:
                print("Failed to bind SR cell:", e)

        total_hour = sum(float(row[3]) for row in ledger) if ledger else 0.0
        total_deposit = sum(float(row[4]) for row in ledger) if ledger else 0.0
        totals_row = ["", "", "Total", str(total_hour), str(total_deposit), str(total_deposit - total_hour)]
        self.table.add_row(totals_row)

        self.table.height = sum(child.height for child in self.table.layout.children)

    # --- SR cell touch handler ---
    def _on_sr_touch(self, row_index, instance, touch):
        if instance.collide_point(*touch.pos):
            RemovePopup(self, row_index).open()

    # --- Clear inputs ---
    def clear_inputs(self):
        for inp in [self.date_input, self.detail_input, self.amount_hour_input, self.amount_deposit_input]:
            inp.text = ""

    # --- Download PDF ---
    def download_pdf(self, instance):
        client = self.clients[self.client_mobile]
        ledger = client['ledger']
        if not ledger:
            print("No entries to save.")
            return
        save_page2_table_as_pdf(client['name'], self.client_mobile, ledger)



# ---------------- Main App ----------------
class MainApp(App):
    def build(self):
        self.clients = {}
        self.main_layout = BoxLayout(orientation='vertical', padding=5, spacing=5)
        self.show_page1()
        return self.main_layout

    def show_page1(self):
        self.main_layout.clear_widgets()
        self.page1 = Page1(self)
        self.main_layout.add_widget(self.page1)

    def show_page2(self, client_mobile):
        self.main_layout.clear_widgets()
        self.page2 = Page2(self, client_mobile)
        self.main_layout.add_widget(self.page2)


if __name__ == "__main__":
    MainApp().run()
