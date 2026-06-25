import sys
import tkinter as tk
from pathlib import Path

import customtkinter as ctk
import numpy as np
import yaml

import matplotlib
matplotlib.use('TkAgg')
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg, \
    NavigationToolbar2Tk
from matplotlib.figure import Figure

from geometry import SiPMGeometry
from source import GaussianSource, PointSource, UniformSource
from simulator import SiPMSimulator
from pulse import PulseGenerator
from visualization import plot_hits, plot_occupancy_heatmap
from datasheets import list_models, get_model, DATASHEETS_DIR, \
    parse_hamamatsu_datasheet, list_display_names, base_id_to_display, \
    apply_overvoltage, apply_wavelength
from optical_chain import OpticalConfig, calculate_photons, LED_DATABASE
from light_dialog import LightSourceDialog
from data_io import load_csv_waveform, compare_waveforms

ctk.set_appearance_mode("System")
ctk.set_default_color_theme("blue")


class NumberEntry(ctk.CTkFrame):
    def __init__(self, parent, value=0.0, is_int=False, **kwargs):
        super().__init__(parent, fg_color="transparent", **kwargs)
        self.is_int = is_int
        vcmd = (self.register(self._validate), '%P')
        self.entry = ctk.CTkEntry(self, width=100, validate="key",
                                   validatecommand=vcmd)
        self.entry.pack(side="left", fill="x", expand=True)
        self.set_value(value)

    def _validate(self, new_value):
        if new_value == "" or new_value == "-":
            return True
        try:
            float(new_value)
            return True
        except ValueError:
            return False

    def get_value(self):
        try:
            val = float(self.entry.get())
            return int(val) if self.is_int else val
        except ValueError:
            return 0

    def set_value(self, value):
        self.entry.delete(0, "end")
        if self.is_int:
            self.entry.insert(0, str(int(value)))
        else:
            self.entry.insert(0, f"{float(value):.2f}")




class ModelSelector(ctk.CTkFrame):
    def __init__(self, parent, label_text, default_model, **kwargs):
        super().__init__(parent, **kwargs)

        ctk.CTkLabel(self, text=label_text,
                     font=ctk.CTkFont(size=13, weight="bold")).pack(
            anchor="w")

        display_names = list_display_names()
        self.combo = ctk.CTkComboBox(self, values=display_names,
                                     command=self._on_select)
        if default_model in display_names:
            self.combo.set(default_model)
        elif display_names:
            self.combo.set(display_names[0])
        self.combo.pack(fill="x", pady=2)

        self.info = ctk.CTkTextbox(self, height=195, font=ctk.CTkFont(
            family="Consolas", size=11), wrap="none")
        self.info.pack(fill="x", pady=4)
        self._refresh_info()

    def _refresh_info(self):
        self._on_select(self.combo.get())

    def _on_select(self, choice):
        d = get_model(choice)
        if not d:
            self.info.delete("1.0", "end")
            self.info.insert("1.0", "Model not found")
            return
        lines = [
            f"Pixels:     {d['pixels']} ({d['nx']}x{d['ny']})",
            f"Pitch:      {d['pitch']} um",
            f"Area:       {d['area_mm']}x{d['area_mm']} mm",
            f"Fill Factor:{d['fill_factor']:.0%}",
            f"PDE:        {d['pde']:.0%} (@450nm)",
            f"Gain:       {d['gain']:.2e}",
            f"Vbr:        {d['breakdown_v']} V",
            f"Nominal Vop:{d['vop']}",
            f"DCR typ:    {d['dcr_typ_kcps']:.0f} kcps",
            f"DCR max:    {d['dcr_max_kcps']:.0f} kcps",
            f"Capacitance:{d['capacitance_pf']:.0f} pF",
            f"Crosstalk:  {d['crosstalk']*100:.1f}%",
            f"Pulse fall: {d['pulse_fall_ns']:.0f} ns",
            f"Recovery:   {d['recovery_ns']:.0f} ns",
            f"Spectral:   {d['spectral_min_nm']}-{d['spectral_max_nm']} nm",
            f"dV/dT:      {d['temp_coeff_mv']} mV/C",
            f"Package:    {', '.join(d['packages'])}",
        ]
        self.info.delete("1.0", "end")
        self.info.insert("1.0", "\n".join(lines))


class App(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("SiPM Digital Twin — Model Comparison")
        self.geometry("1480x920")
        self.minsize(1200, 750)

        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=0)

        self._current_model_a = "S13360-3050CS"
        self._current_model_b = "S13360-3075CS"
        self._sipm_a = None
        self._sipm_b = None
        self._result_a = None
        self._result_b = None
        self._wf_a = None
        self._wf_b = None
        self._optical_config = OpticalConfig()
        self._optical_result = None

        self._build_left_panel()
        self._build_tabs()
        self._build_statusbar()
        self._build_menu()

        self.protocol("WM_DELETE_WINDOW", self._on_close)

    def _on_close(self):
        import matplotlib.pyplot as plt
        plt.close('all')
        self.quit()
        self.destroy()

    def _build_left_panel(self):
        panel = ctk.CTkScrollableFrame(self, width=370, corner_radius=0)
        panel.grid(row=0, column=0, sticky="nsew", padx=2, pady=2)

        names = list_display_names()
        default_a = names[0] if names else "S13360-3050 (CS/PE)"
        default_b = names[1] if len(names) > 1 else default_a

        self.model_a_sel = ModelSelector(panel, "Model A",
                                          default_a,
                                          fg_color="transparent")
        self.model_a_sel.pack(fill="x", pady=(4, 8))

        self.model_b_sel = ModelSelector(panel, "Model B",
                                          default_b,
                                          fg_color="transparent")
        self.model_b_sel.pack(fill="x", pady=(0, 8))

        light_frame = ctk.CTkFrame(panel, fg_color="transparent")
        light_frame.pack(fill="x", pady=4)
        ctk.CTkLabel(light_frame, text="Light Source",
                     font=ctk.CTkFont(size=13, weight="bold")).pack(
            anchor="w", pady=(0, 4))

        self.light_btn = ctk.CTkButton(
            light_frame, text="Configure Light Source...",
            height=36, font=ctk.CTkFont(size=12),
            command=self._open_light_dialog)
        self.light_btn.pack(fill="x")

        self.light_info = ctk.CTkLabel(
            light_frame, text="LED: Red | Direct | 10cm | 50ns/5V",
            font=ctk.CTkFont(size=10), text_color="gray",
            wraplength=340, justify="left")
        self.light_info.pack(fill="x", pady=(4, 0))

        op_frame = ctk.CTkFrame(panel, fg_color="transparent")
        op_frame.pack(fill="x", pady=4)
        ctk.CTkLabel(op_frame, text="Operating Conditions",
                     font=ctk.CTkFont(size=13, weight="bold")).pack(
            anchor="w", pady=(0, 4))

        row_ov_a = ctk.CTkFrame(op_frame, fg_color="transparent")
        row_ov_a.pack(fill="x", pady=1)
        ctk.CTkLabel(row_ov_a, text="Vov A", width=50,
                     anchor="w", text_color="#1565c0").pack(side="left")
        self.vov_a_var = tk.DoubleVar(value=3.0)
        self.vov_a_scale = ctk.CTkSlider(row_ov_a, from_=0.5, to=7.0,
                                          number_of_steps=65,
                                          variable=self.vov_a_var,
                                          command=self._on_vov_a_change)
        self.vov_a_scale.pack(side="left", fill="x", expand=True, padx=4)
        self.vov_a_label = ctk.CTkLabel(row_ov_a, text="3.0 V", width=40)
        self.vov_a_label.pack(side="right")

        row_ov_b = ctk.CTkFrame(op_frame, fg_color="transparent")
        row_ov_b.pack(fill="x", pady=1)
        ctk.CTkLabel(row_ov_b, text="Vov B", width=50,
                     anchor="w", text_color="#e53935").pack(side="left")
        self.vov_b_var = tk.DoubleVar(value=3.0)
        self.vov_b_scale = ctk.CTkSlider(row_ov_b, from_=0.5, to=7.0,
                                          number_of_steps=65,
                                          variable=self.vov_b_var,
                                          command=self._on_vov_b_change)
        self.vov_b_scale.pack(side="left", fill="x", expand=True, padx=4)
        self.vov_b_label = ctk.CTkLabel(row_ov_b, text="3.0 V", width=40)
        self.vov_b_label.pack(side="right")

        note_cond = ctk.CTkLabel(
            op_frame,
            text="λ comes from the light source config.\n"
                 "Overvoltage affects PDE, gain, crosstalk.",
            font=ctk.CTkFont(size=9, slant="italic"),
            text_color="gray")
        note_cond.pack(anchor="w", pady=(2, 0))

        self.compare_btn = ctk.CTkButton(
            panel, text="Compare Models", height=42,
            font=ctk.CTkFont(size=14, weight="bold"),
            command=self._on_compare)
        self.compare_btn.pack(fill="x", pady=(10, 4))

        scan_btn = ctk.CTkButton(
            panel, text="Scan Datasheets", height=28,
            font=ctk.CTkFont(size=11),
            fg_color="transparent", border_width=1,
            command=self._on_scan)
        scan_btn.pack(fill="x")

    def _build_tabs(self):
        self.tabview = ctk.CTkTabview(self, corner_radius=6)
        self.tabview.grid(row=0, column=1, sticky="nsew", padx=4, pady=4)

        self.tab_hits = self.tabview.add("Hit Maps")
        self.tab_heat = self.tabview.add("Occupancy Heatmaps")
        self.tab_wave = self.tabview.add("Waveform Comparison")
        self.tab_stats = self.tabview.add("Statistics")

        self._build_hits_tab()
        self._build_heat_tab()
        self._build_wave_tab()
        self._build_stats_tab()

    def _canvas_with_toolbar(self, parent, figsize=(5.5, 5.5)):
        frame = ctk.CTkFrame(parent, fg_color="transparent")
        fig = Figure(figsize=figsize, dpi=100)
        canvas = FigureCanvasTkAgg(fig, frame)
        toolbar = NavigationToolbar2Tk(canvas, frame)
        toolbar.update()
        toolbar.pack(side="top", fill="x")
        canvas.get_tk_widget().pack(side="top", fill="both", expand=True)
        return frame, fig, canvas

    def _build_hits_tab(self):
        self.tab_hits.grid_columnconfigure(0, weight=1)
        self.tab_hits.grid_columnconfigure(1, weight=1)
        self.tab_hits.grid_rowconfigure(0, weight=0)
        self.tab_hits.grid_rowconfigure(1, weight=1)

        ctk.CTkLabel(self.tab_hits, text="Model A",
                     font=ctk.CTkFont(weight="bold"),
                     text_color="#1565c0").grid(row=0, column=0, pady=2)
        ctk.CTkLabel(self.tab_hits, text="Model B",
                     font=ctk.CTkFont(weight="bold"),
                     text_color="#e53935").grid(row=0, column=1, pady=2)

        frame_a, self.hits_a_fig, self.hits_a_canvas = \
            self._canvas_with_toolbar(self.tab_hits)
        frame_a.grid(row=1, column=0, sticky="nsew", padx=2, pady=2)

        frame_b, self.hits_b_fig, self.hits_b_canvas = \
            self._canvas_with_toolbar(self.tab_hits)
        frame_b.grid(row=1, column=1, sticky="nsew", padx=2, pady=2)

    def _build_heat_tab(self):
        self.tab_heat.grid_columnconfigure(0, weight=1)
        self.tab_heat.grid_columnconfigure(1, weight=1)
        self.tab_heat.grid_rowconfigure(0, weight=0)
        self.tab_heat.grid_rowconfigure(1, weight=1)

        ctk.CTkLabel(self.tab_heat, text="Model A",
                     font=ctk.CTkFont(weight="bold"),
                     text_color="#1565c0").grid(row=0, column=0, pady=2)
        ctk.CTkLabel(self.tab_heat, text="Model B",
                     font=ctk.CTkFont(weight="bold"),
                     text_color="#e53935").grid(row=0, column=1, pady=2)

        frame_a, self.heat_a_fig, self.heat_a_canvas = \
            self._canvas_with_toolbar(self.tab_heat)
        frame_a.grid(row=1, column=0, sticky="nsew", padx=2, pady=2)

        frame_b, self.heat_b_fig, self.heat_b_canvas = \
            self._canvas_with_toolbar(self.tab_heat)
        frame_b.grid(row=1, column=1, sticky="nsew", padx=2, pady=2)

    def _build_wave_tab(self):
        self.tab_wave.grid_columnconfigure(0, weight=1)
        self.tab_wave.grid_rowconfigure(0, weight=1)

        frame, self.wave_fig, self.wave_canvas = \
            self._canvas_with_toolbar(self.tab_wave, figsize=(10, 5))
        frame.grid(row=0, column=0, sticky="nsew")

    def _build_stats_tab(self):
        self.tab_stats.grid_columnconfigure(0, weight=1)
        self.tab_stats.grid_rowconfigure(0, weight=1)
        self.tab_stats.grid_rowconfigure(1, weight=0)

        self.stats_text = ctk.CTkTextbox(
            self.tab_stats, font=ctk.CTkFont(family="Consolas", size=12),
            wrap="none")
        self.stats_text.grid(row=0, column=0, sticky="nsew", padx=4, pady=4)
        self.stats_text.configure(state="disabled")

        self.ratios_label = ctk.CTkLabel(
            self.tab_stats, text="",
            font=ctk.CTkFont(size=12, weight="bold"))
        self.ratios_label.grid(row=1, column=0, pady=(0, 4))

    def _build_statusbar(self):
        self.status_var = tk.StringVar(value="Select models and Compare")
        status = ctk.CTkLabel(self, textvariable=self.status_var,
                              anchor="w", height=24,
                              font=ctk.CTkFont(size=11))
        status.grid(row=1, column=0, columnspan=2, sticky="ew", padx=6,
                    pady=(0, 4))

    def _build_menu(self):
        menubar = tk.Menu(self)

        file_menu = tk.Menu(menubar, tearoff=0)
        file_menu.add_command(label="Save Config...",
                              command=self._save_config)
        file_menu.add_command(label="Load Config...",
                              command=self._load_config)
        file_menu.add_separator()
        file_menu.add_command(label="Load Experimental CSV...",
                              command=self._load_experimental)
        file_menu.add_command(label="Export Waveform CSV...",
                              command=self._export_csv)
        file_menu.add_separator()
        file_menu.add_command(label="Exit", command=self.destroy)
        menubar.add_cascade(label="File", menu=file_menu)

        help_menu = tk.Menu(menubar, tearoff=0)
        help_menu.add_command(label="About", command=self._show_about)
        menubar.add_cascade(label="Help", menu=help_menu)

        self.configure(menu=menubar)

    def _status(self, msg):
        self.status_var.set(msg)
        self.update_idletasks()

    def _on_vov_a_change(self, val):
        self.vov_a_label.configure(text=f"{float(val):.1f} V")

    def _on_vov_b_change(self, val):
        self.vov_b_label.configure(text=f"{float(val):.1f} V")

    def _on_compare(self):
        ma = self.model_a_sel.combo.get()
        mb = self.model_b_sel.combo.get()
        da = get_model(ma)
        db = get_model(mb)
        if not da or not db:
            self._status("Invalid model selected")
            return

        wa = self._sipm_a.width if self._sipm_a else da["nx"] * da["pitch"]
        ha = self._sipm_a.height if self._sipm_a else da["ny"] * da["pitch"]
        wb = self._sipm_b.width if self._sipm_b else db["nx"] * db["pitch"]
        hb = self._sipm_b.height if self._sipm_b else db["ny"] * db["pitch"]

        r = calculate_photons(self._optical_config, wa, ha)
        if r.get("error"):
            self._status(r["error"])
            self._open_light_dialog()
            return
        self._optical_result = r

        self._status(f"Simulating {ma} vs {mb} with "
                     f"{r['photons']:,} photons...")
        try:
            self._run_comparison(da, db, ma, mb, r)
            self._status(
                f"A: {self._result_a.fired_cells} cells "
                f"({self._result_a.occupancy:.1%}) | "
                f"B: {self._result_b.fired_cells} cells "
                f"({self._result_b.occupancy:.1%}) | "
                f"{r['photons']:,} photons")
        except Exception as e:
            self._status(f"Error: {e}")

    def _open_light_dialog(self):
        wa = (self._sipm_a.width if self._sipm_a else 3000,
              self._sipm_a.height if self._sipm_a else 3000)
        wb = (self._sipm_b.width if self._sipm_b else 3000,
              self._sipm_b.height if self._sipm_b else 3000)

        def on_apply(config, result):
            self._optical_config = config
            self._optical_result = result
            led_info = LED_DATABASE.get(config.led_type, {})
            path = config.config_type
            self.light_info.configure(
                text=f"LED: {config.led_type.split()[0]} | {path} | "
                     f"{config.distance_cm}cm | "
                     f"{config.pulse_width_ns}ns/"
                     f"{config.pulse_voltage}V | "
                     f"{result['photons']:,} photons")
            self._on_compare()

        LightSourceDialog(self, self._optical_config, wa, wb, on_apply)

    def _run_comparison(self, da, db, name_a, name_b, opt_result):
        vov_a = self.vov_a_var.get()
        vov_b = self.vov_b_var.get()
        wl = opt_result["wavelength_nm"]

        ov_a = apply_overvoltage(da, vov_a)
        ov_b = apply_overvoltage(db, vov_b)
        pde_a = 0.0
        pde_b = 0.0
        if da["spectral_min_nm"] <= wl <= da["spectral_max_nm"]:
            pde_a = apply_wavelength(da, wl)
        if db["spectral_min_nm"] <= wl <= db["spectral_max_nm"]:
            pde_b = apply_wavelength(db, wl)

        area_a = da["area_mm"] * da["area_mm"]
        area_b = db["area_mm"] * db["area_mm"]
        dcr_a = (ov_a["dcr_typ_kcps"] * 1000 * da["pixels"]) / area_a
        dcr_b = (ov_b["dcr_typ_kcps"] * 1000 * db["pixels"]) / area_b

        sipm_a = SiPMGeometry(da["nx"], da["ny"], da["pitch"],
                               da["fill_factor"])
        sipm_b = SiPMGeometry(db["nx"], db["ny"], db["pitch"],
                               db["fill_factor"])

        sim_a = SiPMSimulator(sipm_a, pde=pde_a, gain=ov_a["gain"],
                              dcr=dcr_a,
                              crosstalk_prob=ov_a["crosstalk"],
                              afterpulse_prob=da["afterpulse"],
                              dcr_time_window_ns=opt_result["pulse_width_ns"])
        sim_b = SiPMSimulator(sipm_b, pde=pde_b, gain=ov_b["gain"],
                              dcr=dcr_b,
                              crosstalk_prob=ov_b["crosstalk"],
                              afterpulse_prob=db["afterpulse"],
                              dcr_time_window_ns=opt_result["pulse_width_ns"])

        seed = 42
        sim_a.seed(seed)
        sim_b.seed(seed)

        src_a = UniformSource()
        src_b = UniformSource()

        n_photons = opt_result["photons"]
        self._result_a = sim_a.run(src_a, n_photons)
        self._result_b = sim_b.run(src_b, n_photons)

        pg_a = PulseGenerator(tau_rise=1e-9,
                              tau_fall=da["pulse_fall_ns"] * 1e-9,
                              gain=ov_a["gain"])
        pg_b = PulseGenerator(tau_rise=1e-9,
                              tau_fall=db["pulse_fall_ns"] * 1e-9,
                              gain=ov_b["gain"])

        rng = np.random.default_rng(seed)
        self._wf_a = pg_a.generate_temporal(
            n_pulses=self._result_a.fired_cells,
            pulse_start_ns=0,
            pulse_width_ns=opt_result["pulse_width_ns"],
            n_afterpulses=self._result_a.afterpulse_fires,
            rng=rng)
        rng_b = np.random.default_rng(seed + 1)
        self._wf_b = pg_b.generate_temporal(
            n_pulses=self._result_b.fired_cells,
            pulse_start_ns=0,
            pulse_width_ns=opt_result["pulse_width_ns"],
            n_afterpulses=self._result_b.afterpulse_fires,
            rng=rng_b)
        self._wf_b = pg_b.generate(
            n_pulses=self._result_b.fired_cells,
            n_afterpulses=self._result_b.afterpulse_fires,
            duration_ns=80)

        self._sipm_a = sipm_a
        self._sipm_b = sipm_b
        self._current_model_a = name_a
        self._current_model_b = name_b

        self._update_hits()
        self._update_heatmaps()
        self._update_waveform()
        self._update_stats()

    def _update_hits(self):
        self.hits_a_fig.clear()
        ax = self.hits_a_fig.add_subplot(111)
        plot_hits(self._sipm_a, ax=ax)
        self.hits_a_fig.tight_layout()
        self.hits_a_canvas.draw()

        self.hits_b_fig.clear()
        ax = self.hits_b_fig.add_subplot(111)
        plot_hits(self._sipm_b, ax=ax)
        self.hits_b_fig.tight_layout()
        self.hits_b_canvas.draw()

    def _update_heatmaps(self):
        self.heat_a_fig.clear()
        ax = self.heat_a_fig.add_subplot(111)
        plot_occupancy_heatmap(self._sipm_a, ax=ax)
        self.heat_a_fig.tight_layout()
        self.heat_a_canvas.draw()

        self.heat_b_fig.clear()
        ax = self.heat_b_fig.add_subplot(111)
        plot_occupancy_heatmap(self._sipm_b, ax=ax)
        self.heat_b_fig.tight_layout()
        self.heat_b_canvas.draw()

    def _update_waveform(self):
        self.wave_fig.clear()
        gs = self.wave_fig.add_gridspec(2, 2, height_ratios=[3, 1])
        ax_a = self.wave_fig.add_subplot(gs[0, 0])
        ax_b = self.wave_fig.add_subplot(gs[0, 1])
        ax_diff = self.wave_fig.add_subplot(gs[1, :])

        wf_a, wf_b = self._wf_a, self._wf_b

        ax_a.plot(wf_a.time, wf_a.amplitude, color='#1565c0', linewidth=1.2)
        ax_a.fill_between(wf_a.time, 0, wf_a.amplitude, alpha=0.1,
                          color='#1565c0')
        ax_a.set_title(f"A: {self._current_model_a}", fontsize=9,
                       color='#1565c0')
        ax_a.set_ylabel('Amplitude')
        ax_a.ticklabel_format(axis='y', style='scientific', scilimits=(0, 0))
        ax_a.grid(True, alpha=0.3)
        ax_a.set_xlim(wf_a.time[0], wf_a.time[-1])

        ax_b.plot(wf_b.time, wf_b.amplitude, color='#e53935', linewidth=1.2)
        ax_b.fill_between(wf_b.time, 0, wf_b.amplitude, alpha=0.1,
                          color='#e53935')
        ax_b.set_title(f"B: {self._current_model_b}", fontsize=9,
                       color='#e53935')
        ax_b.ticklabel_format(axis='y', style='scientific', scilimits=(0, 0))
        ax_b.grid(True, alpha=0.3)
        ax_b.set_xlim(wf_b.time[0], wf_b.time[-1])

        ref_time = wf_a.time
        wf_b_resampled = np.interp(ref_time, wf_b.time, wf_b.amplitude)
        diff = wf_a.amplitude - wf_b_resampled
        ax_diff.plot(ref_time, diff, color='#7b1fa2', linewidth=0.8)
        ax_diff.fill_between(ref_time, 0, diff, alpha=0.15, color='#7b1fa2')
        ax_diff.axhline(y=0, color='#333', linewidth=0.5, linestyle='-')
        ax_diff.set_xlabel('Time (ns)')
        ax_diff.set_ylabel('A - B')
        ax_diff.grid(True, alpha=0.3)
        ax_diff.set_xlim(ref_time[0], ref_time[-1])

        self.wave_fig.suptitle(
            f"Waveform — {self._result_a.fired_cells} vs "
            f"{self._result_b.fired_cells} cells fired",
            fontsize=11, fontweight='bold')
        self.wave_fig.tight_layout()
        self.wave_canvas.draw()

    def _update_stats(self):
        ra, rb = self._result_a, self._result_b
        wf_a, wf_b = self._wf_a, self._wf_b

        header = f"{'Metric':<24} {'Model A':>14} {'Model B':>14}"
        sep = "-" * 56
        rows = [
            ("Photons generated", ra.photons_generated,
             rb.photons_generated),
            ("Photons detected", ra.photons_detected,
             rb.photons_detected),
            ("Photons blocked", ra.photons_blocked, rb.photons_blocked),
            ("Pixels (total cells)", ra.total_cells, rb.total_cells),
            ("Fired cells", ra.fired_cells, rb.fired_cells),
            ("Occupancy", ra.occupancy, rb.occupancy),
            ("Effective PDE", ra.effective_pde, rb.effective_pde),
            ("Dark counts", ra.dark_counts, rb.dark_counts),
            ("Crosstalk fires", ra.crosstalk_fires, rb.crosstalk_fires),
            ("Afterpulse fires", ra.afterpulse_fires, rb.afterpulse_fires),
            ("Peak amplitude", wf_a.peak, wf_b.peak),
            ("Integrated charge", wf_a.charge, wf_b.charge),
        ]

        def fmt_val_a(v):
            if isinstance(v, float) and abs(v) < 0.1:
                return f"{v:.2%}"
            elif isinstance(v, float) and abs(v) > 1e3:
                return f"{v:.2e}"
            elif isinstance(v, float):
                return f"{v:.3f}"
            return str(v)

        def fmt_val_b(v):
            if isinstance(v, float) and abs(v) < 0.1:
                return f"{v:.2%}"
            elif isinstance(v, float) and abs(v) > 1e3:
                return f"{v:.2e}"
            elif isinstance(v, float):
                return f"{v:.3f}"
            return str(v)

        lines = [header, sep]
        for name, va, vb in rows:
            lines.append(
                f"{name:<24} {fmt_val_a(va):>14} {fmt_val_b(vb):>14}")

        ratios = []
        if ra.fired_cells > 0 and rb.fired_cells > 0:
            ratios.append(
                f"Peak A/B={wf_a.peak/wf_b.peak:.3f} | "
                f"Charge A/B={wf_a.charge/wf_b.charge:.3f} | "
                f"Occ A/B={ra.occupancy/max(rb.occupancy,1e-9):.3f}")

        self.stats_text.configure(state="normal")
        self.stats_text.delete("1.0", "end")
        self.stats_text.insert("1.0", "\n".join(lines))
        self.stats_text.configure(state="disabled")

        self.ratios_label.configure(text="  ".join(ratios))

    def _on_scan(self):
        pdfs = list(DATASHEETS_DIR.glob("*.pdf"))
        if not pdfs:
            self._status(f"No PDFs in {DATASHEETS_DIR}")
            return
        found = 0
        for p in pdfs:
            try:
                models = parse_hamamatsu_datasheet(str(p))
                found += len(models)
            except Exception as e:
                self._status(f"Warning: {p.name}: {e}")

        display_names = list_display_names()
        self.model_a_sel.combo.configure(values=display_names)
        self.model_b_sel.combo.configure(values=display_names)
        self._status(f"Scanned {len(pdfs)} PDF(s), catalog: {len(display_names)} groups")

    def _save_config(self):
        from tkinter import filedialog
        path = filedialog.asksaveasfilename(
            defaultextension=".yaml",
            filetypes=[("YAML Files", "*.yaml"), ("All Files", "*.*")])
        if not path:
            return
        data = {
            "model_a": self.model_a_sel.combo.get(),
            "model_b": self.model_b_sel.combo.get(),
            "optical": self._optical_config.to_dict(),
        }
        with open(path, "w") as f:
            yaml.dump(data, f, default_flow_style=False)
        self._status(f"Config saved to {path}")

    def _load_config(self):
        from tkinter import filedialog
        path = filedialog.askopenfilename(
            filetypes=[("YAML Files", "*.yaml"), ("All Files", "*.*")])
        if not path:
            return
        try:
            with open(path, "r") as f:
                data = yaml.safe_load(f)
            if "model_a" in data:
                m = data["model_a"]
                display = get_model(m)
                if display:
                    self.model_a_sel.combo.set(display["display_name"])
                    self.model_a_sel._refresh_info()
            if "model_b" in data:
                m = data["model_b"]
                display = get_model(m)
                if display:
                    self.model_b_sel.combo.set(display["display_name"])
                    self.model_b_sel._refresh_info()
            if "optical" in data:
                self._optical_config = OpticalConfig.from_dict(
                    data["optical"])
            elif "beam" in data:
                pass
            self._status(f"Loaded {path}")
        except Exception as e:
            self._status(f"Error loading config: {e}")

    def _load_experimental(self):
        from tkinter import filedialog
        path = filedialog.askopenfilename(
            filetypes=[("CSV Files", "*.csv"), ("All Files", "*.*")])
        if not path:
            return
        try:
            exp_time, exp_amp = load_csv_waveform(path)

            self.wave_fig.clear()
            gs = self.wave_fig.add_gridspec(2, 2, height_ratios=[3, 1])
            ax_a = self.wave_fig.add_subplot(gs[0, 0])
            ax_b = self.wave_fig.add_subplot(gs[0, 1])
            ax_diff = self.wave_fig.add_subplot(gs[1, :])

            for wf, ax, label, color in [
                (self._wf_a, ax_a, "Model A", '#1565c0'),
                (self._wf_b, ax_b, "Model B", '#e53935'),
            ]:
                if wf is None:
                    continue
                ax.plot(wf.time, wf.amplitude, color=color, linewidth=1.2,
                        label='Simulated', zorder=3)
                ax.fill_between(wf.time, 0, wf.amplitude, alpha=0.08,
                                color=color)
                ax.plot(exp_time, exp_amp, color='#333', linewidth=1.0,
                        linestyle='--', label='Experimental', zorder=2)

                _, diff, _ = compare_waveforms(
                    wf.time, wf.amplitude, exp_time, exp_amp)
                ax_diff.plot(wf.time, diff, color=color, linewidth=0.8,
                             alpha=0.6, label=label)
                ax.set_title(f"{label} vs Experimental", fontsize=9)
                ax.legend(fontsize=7)
                ax.grid(True, alpha=0.3)

            ax_diff.axhline(y=0, color='#333', linewidth=0.5, linestyle='-')
            ax_diff.set_xlabel('Time (ns)')
            ax_diff.set_ylabel('Residual')
            ax_diff.legend(fontsize=7)
            ax_diff.grid(True, alpha=0.3)

            self.wave_fig.suptitle("Simulated vs Experimental",
                                  fontsize=11, fontweight='bold')
            self.wave_fig.tight_layout()
            self.wave_canvas.draw()
            self._status(f"Loaded {path}")
        except Exception as e:
            self._status(f"Error: {e}")

    def _export_csv(self):
        from tkinter import filedialog
        if self._wf_a is None:
            self._status("Run comparison first.")
            return
        path = filedialog.asksaveasfilename(
            defaultextension=".csv",
            filetypes=[("CSV Files", "*.csv"), ("All Files", "*.*")])
        if not path:
            return
        np.savetxt(path,
                   np.column_stack((self._wf_a.time, self._wf_a.amplitude)),
                   delimiter=",", header="time_ns,amplitude", comments="")
        self._status(f"Exported to {path}")

    def _show_about(self):
        from tkinter import messagebox
        messagebox.showinfo(
            "About",
            "SiPM Digital Twin — Model Comparison\n\n"
            "Compare two SiPM models under\n"
            "identical light source conditions.\n\n"
            "Models from datasheet catalog.\n"
            "Parameters: pitch, fill factor, PDE,\n"
            "gain, DCR, crosstalk, afterpulse,\n"
            "recovery time.")


def main():
    app = App()
    app.mainloop()


if __name__ == "__main__":
    main()
