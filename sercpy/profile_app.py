# -*- coding: utf-8 -*-
"""
Created on Mon Aug 31 14:38:54 2026

@author: adria
"""

from pathlib import Path

import tkinter as tk
from tkinter import ttk
from tkinter import font as tkfont

# tkinter's own clipboard (clipboard_append) hands text to the OS only
# lazily -- another program has to actually request a paste (or the window
# has to survive long enough to respond to the OS's request) before the
# text is really transferred. If the app is closed first, the text can be
# lost. `pyperclip` avoids this: it writes straight through the OS's own
# clipboard API (immediate, not lazy), so the copied text survives the app
# closing. Install it with: pip install pyperclip
try:
    import pyperclip
except ImportError:
    pyperclip = None
    print(
        'Note: the "pyperclip" package is not installed, so copied text '
        'may not survive after this app is closed. Install it with: '
        "pip install pyperclip"
    )


class ProfileApp(tk.Tk):
    PROFILE_OPTIONS = ["Day", "Week", "Year"]
 
    INTERVAL_OPTIONS = [
        "2 (12 hours per value)",
        "3 (8 hours per value)",
        "4 (6 hours per value)",
        "6 (4 hours per value)",
        "8 (3 hours per value)",
        "12 (2 hours per value)",
        "24 (1 hour per value)",
        "48 (1/2 hour per value)",
    ]
 
    # Whenever the profile combobox is set to "Day" (including on
    # startup, since that's the default profile), the interval combobox is
    # forced to this option.
    DEFAULT_DAILY_INTERVAL = "24 (1 hour per value)"
 
    # --- Bottom-label lists -------------------------------------------------
    # Week always has 7 sliders -> 7 labels.
    WEEKLY_LABELS = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
 
    # Year always has 12 sliders -> 12 labels.
    YEARLY_LABELS = [
        "Jan", "Feb", "Mar", "Apr", "May", "Jun",
        "Jul", "Aug", "Sep", "Oct", "Nov", "Dec",
    ]
 
    # Day: the number of sliders depends on the interval combobox,
    # so define one list per possible slider count (1, 2, 3, 4, 6, 8, 12, 24,
    # 48). Replace/extend any of these with your own text; entries you don't
    # define here fall back to auto-generated time-range labels (see
    # _generate_daily_labels below).
    DAILY_LABELS = {
        # Example -- uncomment and edit to override the auto-generated ones:
        # 24: ["00h", "01h", "02h", ... , "23h"],
    }
 
    # Slider range (top value, bottom value). Change these to whatever scale
    # your data uses. With a resolution of 0.01, each slider has 101
    # possible positions: 0.00, 0.01, 0.02, ..., 1.00.
    SLIDER_TOP_VALUE = 1.0
    SLIDER_BOTTOM_VALUE = 0.0
    SLIDER_RESOLUTION = 0.01
    SLIDER_INITIAL_VALUE = 0.5
    SLIDER_DECIMALS = 2   # decimal places shown -- keep in sync with SLIDER_RESOLUTION
    SLIDER_WIDTH = 15   # width (in pixels) of the trough/handle

    # Logo shown in the top-right corner of the window. Must live in the
    # same folder as this script.
    LOGO_FILENAME = "serc_logo.png"

    def __init__(self):
        super().__init__()
        self.title("SERCpy - Profile App")
        self.geometry("900x400")

        self.sliders = []        # tk.Scale widgets, one per slider
        self.value_labels = []   # top labels showing the current value

        self._build_top_row()
        self._build_slider_area()
        self._rebuild_sliders()
        self._build_output_area()
 
    # ------------------------------------------------------------------ #
    # Row 1: the two comboboxes
    # ------------------------------------------------------------------ #
    def _build_top_row(self):
        top_row = ttk.Frame(self)
        top_row.grid(row=0, column=0, sticky="ew", padx=10, pady=10)
 
        # --- Profile combobox (left one, always visible) ---
        self.profile_var = tk.StringVar(value=self.PROFILE_OPTIONS[0])
        self.profile_combo = ttk.Combobox(
            top_row,
            textvariable=self.profile_var,
            values=self.PROFILE_OPTIONS,
            state="readonly",
            width=15,
        )
        self.profile_combo.grid(row=1, column=0, padx=(0, 5))
        self.profile_combo.bind("<<ComboboxSelected>>", self._on_profile_change)
 
        # --- Interval combobox (right one, only shown for "Day") ---
        # Starts on DEFAULT_DAILY_INTERVAL since "Day" (the first
        # PROFILE_OPTIONS entry) is the default profile shown on startup.
        self.interval_var = tk.StringVar(value=self.DEFAULT_DAILY_INTERVAL)
        self.interval_combo = ttk.Combobox(
            top_row,
            textvariable=self.interval_var,
            values=self.INTERVAL_OPTIONS,
            state="readonly",
            width=22,
        )
        self.interval_combo.bind("<<ComboboxSelected>>", self._on_interval_change)

        # --- "Total" label + entry, only shown for "Year".
        # It sits in the same slot the interval combobox uses -- the two
        # are never visible at the same time, so they can share the space
        # next to the profile combobox.
        self.total_demand_var = tk.StringVar(value="")
        self.total_demand_entry = ttk.Entry(
            top_row, textvariable=self.total_demand_var, width=20
        )

        # Top row widet labels

        separator_length = 15
        self.first_row_separator = ttk.Label(top_row, text = " "*separator_length )
        self.profile_combo_label = ttk.Label(top_row, text = "Profile type" )
        self.interval_combo_label = ttk.Label( top_row, text = "Number of values" )

        # --- "Total" label + checkbutton, both above the "Total" entry ---
        # A small frame holds the two side by side (packed, not gridded)
        # and is itself gridded as one unit directly above the entry (same
        # row/column the other labels use), so together they sit right
        # over the entry rather than trailing off to its right.
        # Active by default. Turning it off clears and locks the entry;
        # turning it back on unlocks it again (see
        # _on_total_demand_checkbox_toggle). Its state also decides how
        # _generate_list behaves for "Year" -- see there.
        self.total_demand_header = ttk.Frame(top_row)
        self.total_demand_label = ttk.Label(self.total_demand_header, text="Total")
        self.total_demand_checkbox_var = tk.BooleanVar(value=True)
        self.total_demand_checkbox = tk.Checkbutton(
            self.total_demand_header,
            variable=self.total_demand_checkbox_var,
            command=self._on_total_demand_checkbox_toggle,
        )
        self.total_demand_label.pack(side="left")
        # ~10px of separation between the label and the checkbutton.
        self.total_demand_checkbox.pack(side="left", padx=(10, 0))

        self.profile_combo_label.grid(row=0, column=0, sticky = 'w')
        self.first_row_separator.grid( row = 0, column = 1 )
        self._update_top_row_visibility()

        # --- Logo, pinned to the top-right corner of the window ---
        # Deliberately NOT gridded inside top_row. A grid widget as tall as
        # the logo, spanning the label row and the combobox row, forces Tk
        # to stretch one of those two rows to fit it -- and since the
        # comboboxes/entry below the labels have no sticky setting (so
        # they're centered in their cell), that stretched row was pushing
        # them down, away from their labels above.
        # `place()` sidesteps this entirely: it positions the logo purely
        # relative to the window's own size, completely independent of
        # top_row's grid, so it can never affect that layout. relx=1.0 +
        # anchor="ne" keeps it pinned to the top-right corner, and Tk
        # automatically recomputes that position whenever the window is
        # resized (e.g. when switching profiles resizes it via
        # `geometry("")` in `_rebuild_sliders`).
        logo_path = Path(__file__).resolve().parent / "img" / self.LOGO_FILENAME
        try:
            # Keep a reference on `self` -- if the PhotoImage object were
            # only a local variable here, Python would garbage-collect it
            # as soon as this method returns, and the image would vanish
            # from the label (a classic Tkinter gotcha).
            self.logo_image = tk.PhotoImage(file=str(logo_path))
        except tk.TclError:
            self.logo_image = None
            print(
                f'Note: could not load the logo image at "{logo_path}" -- '
                f'make sure "{self.LOGO_FILENAME}" is in the same folder as '
                "profile_app.py."
            )

        if self.logo_image is not None:
            logo_label = tk.Label(self, image=self.logo_image)
            logo_label.place(relx=1.0, x=-10, y=10, anchor="ne")

            # Guarantee the window can never shrink enough for the logo to
            # overlap the controls to its left (e.g. for "Week",
            # whose slider row is fairly narrow).
            top_row.update_idletasks()
            controls_width = top_row.winfo_reqwidth()
            self.minsize(controls_width + self.logo_image.width() + 30, 1)

    def _on_profile_change(self, event=None):
        # Every time the profile switches to "Day", reset the
        # interval combobox to the default (24 -- 1 hour per value) rather
        # than leaving whatever was last selected there.
        if self.profile_var.get() == "Day":
            self.interval_var.set(self.DEFAULT_DAILY_INTERVAL)
        self._update_top_row_visibility()
        self._rebuild_sliders()

    def _on_interval_change(self, event=None):
        self._rebuild_sliders()

    def _update_top_row_visibility(self):
        profile = self.profile_var.get()
        
        if profile == "Day":
            self.interval_combo_label.grid( row = 0, column = 2, sticky = 'w' )
            self.interval_combo.grid( row = 1, column = 2, )
        else:
            self.interval_combo_label.grid_remove()
            self.interval_combo.grid_remove()

        if profile == "Year":
            self.total_demand_header.grid( row = 0, column = 2, sticky = 'w' )
            self.total_demand_entry.grid( row = 1, column = 2, )
        else:
            self.total_demand_header.grid_remove()
            self.total_demand_entry.grid_remove()

    def _on_total_demand_checkbox_toggle(self):
        """Turning the checkbutton off clears the "Total" entry and locks
        it (so the user can't type into it while it's off); turning it
        back on unlocks it again for a fresh value. The checkbutton's
        state is also read directly by _generate_list."""
        if self.total_demand_checkbox_var.get():
            self.total_demand_entry.config(state="normal")
        else:
            self.total_demand_var.set("")
            self.total_demand_entry.config(state="disabled")


    # ------------------------------------------------------------------ #
    # Row 2: the sliders
    # ------------------------------------------------------------------ #
    def _build_slider_area(self):
        # Container that will hold one sub-frame per slider. It gets
        # cleared and repopulated every time the slider count changes.
        self.slider_area = ttk.Frame(self)
        # Top padding of 20 (on top of top_row's own bottom padding of 10)
        # gives ~30px of separation between the comboboxes/logo row above
        # and the sliders below.
        self.slider_area.grid(row=1, column=0, sticky="nsew", padx=10, pady=(20, 10))
 
    def _current_slider_count(self):
        profile = self.profile_var.get()
        if profile == "Week":
            return 7
        if profile == "Year":
            return 12
        # "Day" -> depends on the interval combobox
        combo_option = self.interval_var.get()
        return int(combo_option.split(" ")[0])
 
    def _current_bottom_labels(self, n):
        profile = self.profile_var.get()
        if profile == "Week":
            return self.WEEKLY_LABELS
        if profile == "Year":
            return self.YEARLY_LABELS
        # Day
        return self.DAILY_LABELS.get(n, self._generate_daily_labels(n))
 
    @staticmethod
    def _generate_daily_labels(n):
        """Fallback labels for a daily profile: time ranges covering 24h,
        split into n equal slices (e.g. n=24 -> "00:00-01:00", ...)."""
        hours_per_value = 24 / n
 
        def fmt(h):
            hh = int(h) % 24
            mm = int(round((h - int(h)) * 60))
            return f"{hh:02d}:{mm:02d}"
 
        labels = []
        for i in range(n):
            start = i * hours_per_value
            end = (i + 1) * hours_per_value
            if i == n - 1:
                end_string = '24:00'
            else:
                end_string = fmt(end)
            labels.append(f"{fmt(start)}-{end_string}")
        return labels
 
    def _rebuild_sliders(self):
        # Remove any previously built sliders
        for widget in self.slider_area.winfo_children():
            widget.destroy()
        self.sliders = []
        self.value_labels = []
 
        profile = self.profile_var.get()
        n = self._current_slider_count()
        bottom_labels = self._current_bottom_labels(n)
 
        # For "Week" and "Year" only: give every
        # slider-plus-label column the same fixed width, a bit larger than
        # the widest bottom label, so a long label (e.g. "September")
        # doesn't widen just its own column and throw off the spacing.
        # ("Day" is excluded -- its labels are rotated 90°, so
        # they take up hardly any horizontal space to begin with.)
        fixed_col_width = None
        if profile in ("Week", "Year"):
            default_font = tkfont.nametofont("TkDefaultFont")
            longest_label_width = max(default_font.measure(lbl) for lbl in bottom_labels)
            fixed_col_width = longest_label_width + 20  # margin beyond the longest label
 
        for i in range(n):
            col_frame = ttk.Frame(self.slider_area)
            col_frame.grid(row=0, column=i, padx=2, sticky="ns")
 
            # --- Top label: shows the slider's current value ---
            value_label = tk.Label(col_frame, text=self._format_slider_value(self.SLIDER_INITIAL_VALUE))
            value_label.grid(row=0, column=0)
            self.value_labels.append(value_label)
 
            # --- The vertical slider itself ---
            # showvalue=0 hides tkinter's built-in value display (which is
            # drawn beside the slider for vertical scales); we show the
            # value ourselves in `value_label` instead, updated by
            # `_on_slider_move` every time the slider is moved.
            scale = tk.Scale(
                col_frame,
                from_=self.SLIDER_TOP_VALUE,
                to=self.SLIDER_BOTTOM_VALUE,
                orient=tk.VERTICAL,
                resolution=self.SLIDER_RESOLUTION,
                showvalue=0,
                length=200,
                width=self.SLIDER_WIDTH,
                sliderlength=self.SLIDER_WIDTH,
                command=lambda val, lbl=value_label: self._on_slider_move(val, lbl),
            )
            scale.grid(row=1, column=0)
            # Start the slider at SLIDER_INITIAL_VALUE instead of defaulting
            # to the bottom of the track. .set() fires the `command`
            # callback too, but we already set the label text above so the
            # two stay in sync even before that fires.
            scale.set(self.SLIDER_INITIAL_VALUE)
            self.sliders.append(scale)
 
            # --- Bottom label: fixed text from the label list. Only the
            # "Day" case gets its labels rotated 90° (there can be
            # up to 48 of them, and the time-range text is long); Weekly and
            # Yearly stay as normal horizontal labels.
            text = bottom_labels[i] if i < len(bottom_labels) else str(i + 1)
            if profile == "Day":
                bottom_label = self._create_vertical_label(col_frame, text)
            else:
                bottom_label = tk.Label(col_frame, text=text)
            bottom_label.grid(row=2, column=0, pady=(10, 0))
 
            # Lock this column's width so the label text can't stretch it.
            # grid_propagate(False) freezes the frame at whatever width/
            # height we hand it, instead of auto-sizing to its children, so
            # we first read off the natural (content-driven) height and
            # only override the width.
            if fixed_col_width is not None:
                col_frame.update_idletasks()
                natural_height = col_frame.winfo_reqheight()
                col_frame.configure(width=fixed_col_width, height=natural_height)
                col_frame.grid_propagate(False)
 
        # The window was given a fixed initial size (see __init__), which
        # does not grow on its own as slider/label content changes size.
        # Without this, taller content (e.g. the rotated daily labels)
        # could end up clipped below the window's bottom edge. Clearing the
        # explicit geometry lets Tk resize the window to fit whatever was
        # just built.
        self.update_idletasks()
        self.geometry("")

    # ------------------------------------------------------------------ #
    # Row 2: "Generate list" button + output box
    # ------------------------------------------------------------------ #
    def _build_output_area(self):
        output_row = ttk.Frame(self)
        # Extra space above (gap from the slider row) and below.
        output_row.grid(row=2, column=0, sticky="ew", padx=10, pady=(20, 10))
        output_row.columnconfigure(0, weight=1)

        # A larger font + padding for the button, via a dedicated ttk style
        # (ttk widgets take their font from a style, not a `font=` option).
        style = ttk.Style(self)
        style.configure("Generate.TButton", font=("TkDefaultFont", 10, "bold"), padding=8)

        # Button + status message side by side, left-aligned (not stretched
        # across the row -- that's what keeps the status message right next
        # to the button instead of drifting to the far right).
        button_row = ttk.Frame(output_row)
        button_row.grid(row=0, column=0, sticky="w", pady=(0, 20))

        self.generate_button = ttk.Button(
            button_row,
            text="Generate list",
            command=self._generate_list,
            style="Generate.TButton",
        )
        self.generate_button.grid(row=0, column=0)

        # Shown next to the button when the list couldn't be generated
        # (currently: an invalid "Total" value in Yearly profile).
        self.status_var = tk.StringVar(value="")
        self.status_label = ttk.Label(button_row, textvariable=self.status_var, foreground="red")
        self.status_label.grid(row=0, column=1, padx=(10, 0))

        # Read-only (state="disabled") so the user can't accidentally edit
        # the generated list, but selection/copying still works fine even
        # while disabled.
        self.output_text = tk.Text(output_row, height=5, wrap="word")
        self.output_text.grid(row=1, column=0, sticky="ew")
        self.output_text.config(state="disabled")

        # Right-clicking the output box doesn't show a system context menu
        # with a "Copy" entry (Ctrl+C still works, but not everyone knows
        # that) -- this button is the visible substitute for it. Placed
        # below the output box, and disabled until there's actually
        # something in it to copy (see `_generate_list`).
        self.copy_button = ttk.Button(
            output_row,
            text="Copy to clipboard",
            command=self._copy_button_clicked,
            state="disabled",
        )
        self.copy_button.grid(row=2, column=0, sticky="w", pady=(10, 0))

        # Route Ctrl+C / right-click-copy / Ctrl+Insert (all of these fire
        # the <<Copy>> virtual event) through pyperclip too, in case the
        # user selects only part of the text and copies that instead of
        # using the auto-copy in `_generate_list`. Returning "break" stops
        # tkinter's own (less reliable) copy handler from running as well.
        self.output_text.bind("<<Copy>>", self._on_copy_event)

    def _generate_list(self):
        """Reads every slider's current value, multiplies it (for "Year"
        only, and only while the "Total" checkbutton is active) by the
        "Total" entry, and writes the result into `output_text` as
        "[ value_1, value_2, ..., value_n ]"."""
        self.status_var.set("")

        profile = self.profile_var.get()
        # The "Total" entry/checkbutton only exist for "Year" -- and even
        # there, the demand-scaling behavior only applies while the
        # checkbutton is checked. Unchecked, "Year" behaves just like "Day"
        # and "Week": the raw slider values go straight into the list.
        use_total_demand = profile == "Year" and self.total_demand_checkbox_var.get()

        if use_total_demand:
            try:
                multiplier = float(self.total_demand_var.get())
                assert multiplier > 0
            except (ValueError, AssertionError):
                self.status_var.set('Invalid "Total" value -- please enter a number greater than 0.')
                return

            values = [ scale.get() for scale in self.sliders ]
            sum_values = sum( values )
            if sum_values <= 0:
                self.status_var.set("At least one slider must be set above 0 in order to generate the list.")
                return
            values = [ value/sum_values for value in values ]
            values = [ self._format_value( multiplier*value ) for value in values ]
        else:
            # Raw slider positions -- formatted with the same fixed decimal
            # places as the 0.00-1.00 grid they move on (unlike the
            # demand-scaling branch above, whose values are scaled
            # proportions, not raw slider positions, so they keep the
            # flexible formatting).
            values = [self._format_slider_value(scale.get()) for scale in self.sliders]

        
        list_str = "[ " + ", ".join(values) + " ]"

        self.output_text.config(state="normal")
        self.output_text.delete("1.0", tk.END)
        self.output_text.insert("1.0", list_str)
        self.output_text.config(state="disabled")

        # There's now something to copy.
        self.copy_button.config(state="normal")

        # Pre-select everything so the user can see/re-copy it manually too.
        self.output_text.tag_add("sel", "1.0", "end-1c")
        self.output_text.focus_set()

    def _copy_button_clicked(self):
        """"Copy to clipboard" button -- a visible substitute for the
        right-click "Copy" menu, which doesn't appear on output_text."""
        self._copy_output_to_clipboard(self._selection_or_all())

    def _on_copy_event(self, event=None):
        """Handles Ctrl+C / right-click-copy / Ctrl+Insert on output_text
        (all fire the <<Copy>> virtual event): copies the current selection
        (or the whole box, if nothing is selected) via the reliable
        clipboard path instead of tkinter's own. Returning "break" stops
        tkinter's default (less reliable) copy handler from also running."""
        self._copy_output_to_clipboard(self._selection_or_all())
        return "break"

    def _selection_or_all(self):
        """The currently selected text in output_text, or its full
        contents if nothing is selected."""
        try:
            return self.output_text.get("sel.first", "sel.last")
        except tk.TclError:
            return self.output_text.get("1.0", "end-1c")

    def _copy_output_to_clipboard(self, text):
        """Copy `text` to the OS clipboard. Prefers pyperclip, which writes
        straight through the OS's clipboard API (so the copied text is
        still there even after this app has closed); falls back to
        tkinter's own clipboard if pyperclip isn't installed."""
        if pyperclip is not None:
            try:
                pyperclip.copy(text)
                return
            except Exception:
                pass  # fall through to the tkinter fallback below

        self.clipboard_clear()
        self.clipboard_append(text)
        self.update()

    @staticmethod
    def _format_value(value):
        """Format a value without a redundant trailing ".0" when it's a
        whole number. Used for the Yearly-profile output, where values are
        demand-scaled proportions rather than raw slider positions, so a
        fixed number of decimal places wouldn't necessarily fit them."""
        if float(value).is_integer():
            return str(int(value))
        return str(value)

    @classmethod
    def _format_slider_value(cls, value):
        """Format a raw slider value with a fixed number of decimal places
        (SLIDER_DECIMALS), matching the slider's own 0.00-1.00 grid."""
        return f"{value:.{cls.SLIDER_DECIMALS}f}"

    @staticmethod
    def _on_slider_move(value, label):
        """Custom callback: updates the top label with the slider's
        current value whenever the slider is moved."""
        label.config(text=str(value))
 
    def _create_vertical_label(self, parent, text):
        """Return a small Canvas that draws `text` rotated 90° (reading
        bottom-to-top), used in place of a tk.Label since plain Labels
        can't rotate their text. The canvas is sized from the *actual*
        rendered bounding box of the rotated text (via bbox()), with extra
        padding -- particularly above the text -- since bbox() can slightly
        under-report the rendered extent on some platforms/fonts, which was
        clipping the top of the text (the end of the string, since it reads
        bottom-to-top)."""
        default_font = tkfont.nametofont("TkDefaultFont")
        canvas = tk.Canvas(parent, highlightthickness=0)
 
        # Draw once to measure the real bounding box, then resize the
        # canvas and re-position the text inside it with generous padding.
        item = canvas.create_text(0, 0, text=text, angle=90, font=default_font, anchor="center")
        x1, y1, x2, y2 = canvas.bbox(item)
        text_width = x2 - x1
        text_height = y2 - y1
 
        side_pad = 0
        top_pad = 6   # extra headroom above the text (the end that was clipping)
        bottom_pad = 6
 
        width = text_width + 2 * side_pad
        height = text_height + top_pad + bottom_pad
        canvas.config(width=width, height=height)
        canvas.coords(item, width / 2, top_pad + text_height / 2)
        return canvas
 
 
def launch():
    """Open the app in a brand-new, separate process, instead of running it
    inside whatever process/kernel calls this function.

    Why this exists: creating a ProfileApp() and calling .mainloop() runs
    the Tk/Tcl GUI loop directly inside the calling process. That's exactly
    what happens when this file is run as a script (see the __main__ block
    below) -- each run gets its own fresh, disposable Python process, so if
    anything ever goes wrong tearing down the Tcl interpreter when the
    window closes, only that one disposable process is affected.

    A Jupyter notebook's kernel is not disposable like that -- it's a single
    long-lived process that stays alive across many cells. If a Tk window
    created directly inside that kernel crashes while being torn down on
    close (a known source of hard, silent crashes with Tkinter on some
    platforms, especially Windows), it takes the *entire kernel* down with
    it -- which is exactly the "kernel appears to have died" message. Spyder
    doesn't show this problem because running a script there normally
    launches its own separate console process to begin with, so the same
    kind of crash simply can't reach Spyder itself.

    `launch()` sidesteps this the same way Spyder already does: it starts
    this file as a new, independent `python profile_app.py` process (via
    `subprocess.Popen`) rather than creating the Tk window in-process. The
    notebook's kernel is then never at risk, no matter what happens in the
    GUI. You can still use the "Copy to clipboard" button in the app window
    and paste the result back into a notebook cell as usual.

    Usage from a notebook cell:
        import profile_app
        profile_app.launch()
    """
    import subprocess
    import sys
    from pathlib import Path

    script_path = str(Path(__file__).resolve())
    subprocess.Popen([sys.executable, script_path])


if __name__ == "__main__":
    app = ProfileApp()
    app.mainloop()