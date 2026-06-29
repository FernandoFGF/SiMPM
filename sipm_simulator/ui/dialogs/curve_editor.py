import customtkinter as ctk
import matplotlib
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib.figure import Figure


class CurveEditorDialog(ctk.CTkToplevel):
    def __init__(self, parent, on_save):
        super().__init__(parent)
        self.title("Edit Datasheet Curves")
        self.geometry("950x700")
        self.minsize(800, 600)
        self.grab_set()
        self.on_save = on_save
        from models.datasheets import SPECTRAL_RESPONSE, OV_CURVES, save_user_curves
        self._save_fn = save_user_curves
        self._spectral = {k: list(v) for k, v in SPECTRAL_RESPONSE.items()}
        self._ov = {int(k): {sk: list(sv) for sk, sv in v.items()}
                    for k, v in OV_CURVES.items()}
        self._ov_axes = {}
        self._ov_markers = {}
        self._ov_lines = {}
        self._ov_key_map = {}
        self._ov_figs = []
        self._dragging = None
        self._drag_index = None
        self._drag_curve_key = None
        self._drag_curve_type = None
        self._build()

    def _build(self):
        self._notebook = ctk.CTkTabview(self, width=920, height=580)
        self._notebook.pack(fill="both", expand=True, padx=8, pady=8)
        self._build_spectral_tab()
        self._build_ov_tab()

    def _build_spectral_tab(self):
        tab = self._notebook.add("Spectral Response")
        tab.grid_columnconfigure(0, weight=1)
        tab.grid_rowconfigure(0, weight=0)
        tab.grid_rowconfigure(1, weight=1)
        header = ctk.CTkFrame(tab, fg_color="transparent")
        header.grid(row=0, column=0, sticky="ew", pady=(2, 0))
        ctk.CTkLabel(header, text="Drag points to adjust",
                     font=ctk.CTkFont(size=10, slant="italic"),
                     text_color="gray").pack(side="left")
        ctk.CTkButton(header, text="Save && Close", width=90, height=24,
                      font=ctk.CTkFont(size=10, weight="bold"),
                      command=self._save).pack(side="right", padx=4)
        self._spec_fig = Figure(figsize=(8, 4.5), dpi=100)
        self._spec_canvas = FigureCanvasTkAgg(self._spec_fig, tab)
        self._spec_canvas.get_tk_widget().grid(row=1, column=0, sticky="nsew",
                                                padx=4, pady=4)
        self._spec_ax = self._spec_fig.add_subplot(111)
        self._draw_spectral()
        self._spec_canvas.mpl_connect("button_press_event",
                                       self._on_spec_click)
        self._spec_canvas.mpl_connect("motion_notify_event",
                                       self._on_spec_drag)
        self._spec_canvas.mpl_connect("button_release_event",
                                       self._on_spec_release)

    def _draw_spectral(self):
        self._spec_ax.clear()
        self._spec_lines = {}
        self._spec_markers = {}
        colors = {'pde25': '#1e88e5', 'pde50': '#ff8f00', 'pde75': '#00897b'}
        nominal_pde = {'pde25': 0.35, 'pde50': 0.40, 'pde75': 0.50}
        wl = self._spectral["wl"]
        for key, label in [("pde25", "25um"), ("pde50", "50um"),
                           ("pde75", "75um")]:
            y_abs = [v * nominal_pde[key] * 100 for v in self._spectral[key]]
            line, = self._spec_ax.plot(wl, y_abs, color=colors[key],
                                       linewidth=1.2, alpha=0.4)
            marker, = self._spec_ax.plot(wl, y_abs, 'o', color=colors[key],
                                         markersize=8, picker=8,
                                         label=f"{label} "
                                               f"(peak={max(y_abs):.0f}%)")
            self._spec_lines[key] = line
            self._spec_markers[key] = marker
        self._spec_ax.set_xlabel("Wavelength (nm)")
        self._spec_ax.set_ylabel("Absolute PDE (%)")
        self._spec_ax.set_title("Drag points to adjust")
        self._spec_ax.set_ylim(0, None)
        self._spec_ax.yaxis.set_major_locator(
            matplotlib.ticker.MultipleLocator(5))
        self._spec_ax.yaxis.set_minor_locator(
            matplotlib.ticker.MultipleLocator(1))
        self._spec_ax.grid(True, alpha=0.3)
        self._spec_ax.grid(True, which='minor', alpha=0.1)
        self._spec_ax.legend(fontsize=9)
        self._spec_fig.tight_layout()
        self._spec_canvas.draw()

    def _on_spec_click(self, event):
        if event.inaxes != self._spec_ax:
            return
        if self._dragging is not None:
            return
        for key, marker in self._spec_markers.items():
            contains, info = marker.contains(event)
            if contains:
                idx = info["ind"][0]
                self._dragging = "spectral"
                self._drag_curve_key = key
                self._drag_index = idx
                return

    def _on_spec_drag(self, event):
        if self._dragging != "spectral":
            return
        if event.inaxes != self._spec_ax or event.ydata is None:
            return
        nominal_pde = {'pde25': 0.35, 'pde50': 0.40, 'pde75': 0.50}
        scale = nominal_pde[self._drag_curve_key] * 100
        new_norm = max(0.0, min(1.0, event.ydata / max(scale, 1)))
        self._spectral[self._drag_curve_key][self._drag_index] = new_norm
        self._redraw_spectral_fast()

    def _on_spec_release(self, event):
        if self._dragging == "spectral":
            self._dragging = None
            self._redraw_spectral_fast()

    def _redraw_spectral_fast(self):
        nominal_pde = {'pde25': 0.35, 'pde50': 0.40, 'pde75': 0.50}
        for key in self._spec_markers:
            y_abs = [v * nominal_pde[key] * 100
                     for v in self._spectral[key]]
            self._spec_lines[key].set_ydata(y_abs)
            self._spec_markers[key].set_ydata(y_abs)
        self._spec_canvas.draw_idle()

    def _build_ov_tab(self):
        for tab_name, tab_id, data_key, ylabel, divider, ylims, yticks in [
            ("PDE vs Vov", "pde", "pde", "PDE (%)", 1,
             (10, 70), (10, 5)),
            ("Crosstalk vs Vov", "xtalk", "xtalk", "Crosstalk (%)", 1,
             (0, 25), (10, 5)),
        ]:
            self._build_single_ov_tab(tab_name, tab_id, data_key,
                                      ylabel, divider, ylims, yticks,
                                      all_pitches=True)
        gain_info = [(25, 1.6e6, 0), (50, 6e6, 0), (75, 1.6e7, 0)]
        for pitch, ymax, ymin in gain_info:
            self._build_single_ov_tab(
                f"Gain {pitch}\u00b5m", f"gain{pitch}", "gain",
                f"Gain {pitch}\u00b5m", 1,
                (ymin, ymax * 1.05), None,
                single_pitch=pitch)

    def _build_single_ov_tab(self, tab_name, tab_id, data_key,
                             ylabel, divider, ylims, yticks,
                             all_pitches=False, single_pitch=None,
                             use_log=False):
        tab = self._notebook.add(tab_name)
        tab.grid_columnconfigure(0, weight=1)
        tab.grid_rowconfigure(0, weight=0)
        tab.grid_rowconfigure(1, weight=1)
        header = ctk.CTkFrame(tab, fg_color="transparent")
        header.grid(row=0, column=0, sticky="ew", pady=(2, 0))
        ctk.CTkLabel(header, text="Drag points to adjust",
                     font=ctk.CTkFont(size=10, slant="italic"),
                     text_color="gray").pack(side="left")
        ctk.CTkButton(header, text="Save && Close", width=90, height=24,
                      font=ctk.CTkFont(size=10, weight="bold"),
                      command=self._save).pack(side="right", padx=4)
        fig = Figure(figsize=(7, 4.5), dpi=100)
        canvas = FigureCanvasTkAgg(fig, tab)
        canvas.get_tk_widget().grid(row=1, column=0, sticky="nsew",
                                     padx=4, pady=4)
        ax = fig.add_subplot(111)
        self._ov_axes[tab_id] = ax
        self._ov_markers[tab_id] = {}
        self._ov_lines[tab_id] = {}
        self._ov_key_map[tab_id] = data_key
        self._ov_figs.append((fig, canvas))
        colors = {25: '#1e88e5', 50: '#ff8f00', 75: '#00897b'}
        pitches = [single_pitch] if single_pitch else [25, 50, 75]
        for pitch in pitches:
            c = self._ov[pitch]
            y_vals = [v / divider for v in c[data_key]]
            label = f"{pitch}\u00b5m" if all_pitches else None
            line, = ax.plot(c["vov"], y_vals, color=colors[pitch],
                            linewidth=1.5, alpha=0.4, label=label)
            marker, = ax.plot(c["vov"], y_vals, 'o',
                              color=colors[pitch],
                              markersize=8, picker=8, label=label)
            self._ov_lines[tab_id][pitch] = line
            self._ov_markers[tab_id][pitch] = marker
        ax.set_xlabel("Overvoltage (V)")
        ax.set_ylabel(ylabel)
        ax.set_title(tab_name)
        ax.set_xlim(0, 10)
        if use_log:
            ax.set_yscale("log")
        if ylims:
            ax.set_ylim(ylims[0], ylims[1])
        if yticks:
            ax.yaxis.set_major_locator(
                matplotlib.ticker.MultipleLocator(yticks[0]))
            ax.yaxis.set_minor_locator(
                matplotlib.ticker.MultipleLocator(yticks[1]))
        if all_pitches:
            ax.legend(fontsize=9, loc='upper left')
        ax.grid(True, alpha=0.3)
        ax.grid(True, which='minor', alpha=0.1)
        canvas.mpl_connect("button_press_event",
                           lambda e, p=tab_id: self._on_ov_click(e, p))
        canvas.mpl_connect("motion_notify_event",
                           lambda e, p=tab_id: self._on_ov_drag(e, p))
        canvas.mpl_connect("button_release_event",
                           self._on_ov_release)

    def _on_ov_click(self, event, param):
        if event.inaxes != self._ov_axes.get(param):
            return
        if self._dragging is not None:
            return
        for pitch, marker in self._ov_markers[param].items():
            contains, info = marker.contains(event)
            if contains:
                idx = info["ind"][0]
                self._dragging = "ov"
                self._drag_curve_type = param
                self._drag_curve_key = pitch
                self._drag_index = idx
                return

    def _on_ov_drag(self, event, param):
        if self._dragging != "ov" or self._drag_curve_type != param:
            return
        ax = self._ov_axes.get(param)
        if ax is None or event.inaxes != ax or event.ydata is None:
            return
        new_raw = max(0.0, event.ydata)
        pitch = self._drag_curve_key
        dk = self._ov_key_map.get(param, param)
        self._ov[pitch][dk][self._drag_index] = new_raw
        y_disp = list(self._ov[pitch][dk])
        self._ov_lines[param][pitch].set_ydata(y_disp)
        self._ov_markers[param][pitch].set_ydata(y_disp)
        idx = list(self._ov_axes.keys()).index(param)
        self._ov_figs[idx][1].draw_idle()

    def _on_ov_release(self, event):
        if self._dragging == "ov":
            self._dragging = None

    def _save(self):
        new_spectral = {
            "wl": self._spectral["wl"],
            "pde25": self._spectral["pde25"],
            "pde50": self._spectral["pde50"],
            "pde75": self._spectral["pde75"],
        }
        new_ov = {pitch: dict(self._ov[pitch]) for pitch in [25, 50, 75]}
        self._save_fn(new_spectral, new_ov)
        self.on_save()
        self.destroy()
