# ---------------- remove_popup.py ----------------
from kivy.uix.popup import Popup
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.textinput import TextInput
from kivy.uix.button import Button
from kivy.uix.label import Label

PASSWORD = "ZAB"


class RemovePopup(Popup):
    """
    Handles password prompt and single-entry removal.
    Expects:
      - page2: the Page2 instance
      - entry_index: index (0-based) of the entry to remove
    """
    def __init__(self, page2, entry_index, **kwargs):
        super().__init__(title="Remove Entry (Password Required)", size_hint=(0.75, 0.45), **kwargs)
        self.page2 = page2
        self.entry_index = entry_index

        root = BoxLayout(orientation="vertical", spacing=10, padding=10)

        self.info = Label(
            text=f"Remove entry #{entry_index+1} for {self.page2.client_mobile}?",
            size_hint_y=None,
            height=40,
        )
        root.add_widget(self.info)

        self.pin = TextInput(
            password=True, multiline=False, hint_text="Enter Password", size_hint_y=None, height=44
        )
        root.add_widget(self.pin)

        btns = BoxLayout(size_hint_y=None, height=44, spacing=10)
        cancel = Button(text="Cancel")
        confirm = Button(text="Remove")
        cancel.bind(on_press=lambda *_: self.dismiss())
        confirm.bind(on_press=self._confirm)
        btns.add_widget(cancel)
        btns.add_widget(confirm)

        root.add_widget(btns)
        self.add_widget(root)

    def _confirm(self, *_):
        if self.pin.text != PASSWORD:
            self.pin.text = ""
            self.pin.hint_text = "Wrong Password!"
            return

        # Remove the entry
        ledger = self.page2.main_app.clients[self.page2.client_mobile]["ledger"]
        if 0 <= self.entry_index < len(ledger):
            removed = ledger.pop(self.entry_index)
            print(f"Removed entry: {removed}")

            # Re-number SR column after removal
            for i, row in enumerate(ledger):
                row[0] = str(i + 1)

            # Refresh table on Page2
            self.page2.show_table()

        self.dismiss()
