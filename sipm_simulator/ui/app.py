import tkinter as tk
from tkinter import filedialog, messagebox

import customtkinter as ctk
import numpy as np
import yaml

import matplotlib
matplotlib.use('TkAgg')
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg, \
    NavigationToolbar2Tk
from matplotlib.figure import Figure

from core.geometry import SiPMGeometry
from core.source import GaussianSource, UniformSource
from core.simulator import SiPMSimulator
from core.pulse import PulseGenerator
from visualization.hits_plots import plot_hits, plot_occupancy_heatmap
from visualization.beam_plots import plot_beam_profile
from models.datasheets import (DATASHEETS_DIR, parse_hamamatsu_datasheet,
                                list_display_names, apply_overvoltage,
                                apply_wavelength, apply_temperature)
from optics.optical_chain import OpticalConfig, calculate_photons, LED_DATABASE
from sipm_io.data_io import (load_csv_waveform, compare_waveforms,
                              export_full_results)

from .panels.model_selector import ModelSelector
from .dialogs.light_dialog import LightSourceDialog
from .dialogs.curve_editor import CurveEditorDialog

ctk.set_appearance_mode("System")
ctk.set_default_color_theme("blue")


class App(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("SiPM Digital Twin \u2014 Model Comparison")
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
        self._wf_a_primary = None
        self._wf_b_primary = None
        self._wf_a_primary_xt = None
        self._wf_b_primary_xt = None
        self._wf_a_dark = None
        self._wf_b_dark = None
        self._wf_a_ap = None
        self._wf_b_ap = None
        self._show_dcr = tk.BooleanVar(value=False)
        self._show_ap = tk.BooleanVar(value=False)
        self._show_xtalk = tk.BooleanVar(value=False)
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

        quick_frame = ctk.CTkFrame(panel, fg_color="transparent")
        quick_frame.pack(fill="x", pady=4)
        ctk.CTkLabel(quick_frame, text="Quick Pulse",
                     font=ctk.CTkFont(size=13, weight="bold")).pack(
            anchor="w", pady=(0, 4))
        row_qp = ctk.CTkFrame(quick_frame, fg_color="transparent")
        row_qp.pack(fill="x", pady=1)
        ctk.CTkLabel(row_qp, text="Photons", width=55,
                     anchor="w").pack(side="left")
        self.q_photons_var = tk.StringVar(value="1000")
        self.q_photons_entry = ctk.CTkEntry(
            row_qp, width=80, textvariable=self.q_photons_var)
        self.q_photons_entry.pack(side="left", padx=2)
        ctk.CTkLabel(row_qp, text="\u03bb nm", width=55,
                     anchor="w").pack(side="left", padx=(6, 0))
        self.q_lambda_var = tk.StringVar(value="450")
        self.q_lambda_entry = ctk.CTkEntry(
            row_qp, width=80, textvariable=self.q_lambda_var)
        self.q_lambda_entry.pack(side="left", padx=2)
        self.quick_btn = ctk.CTkButton(
            quick_frame, text="Fire Pulse",
            height=34, font=ctk.CTkFont(size=12, weight="bold"),
            fg_color="#f9a825", hover_color="#fdd835",
            text_color="#212121",
            command=self._on_quick_pulse)
        self.quick_btn.pack(fill="x", pady=(6, 0))

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
        self.vov_a_scale = ctk.CTkSlider(row_ov_a, from_=0.5, to=8.0,
                                           number_of_steps=75,
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
        self.vov_b_scale = ctk.CTkSlider(row_ov_b, from_=0.5, to=8.0,
                                          number_of_steps=75,
                                          variable=self.vov_b_var,
                                          command=self._on_vov_b_change)
        self.vov_b_scale.pack(side="left", fill="x", expand=True, padx=4)
        self.vov_b_label = ctk.CTkLabel(row_ov_b, text="3.0 V", width=40)
        self.vov_b_label.pack(side="right")

        row_temp = ctk.CTkFrame(op_frame, fg_color="transparent")
        row_temp.pack(fill="x", pady=1)
        ctk.CTkLabel(row_temp, text="Temp", width=50,
                     anchor="w").pack(side="left")
        self.temp_var = tk.DoubleVar(value=25.0)
        self.temp_scale = ctk.CTkSlider(row_temp, from_=-20.0, to=60.0,
                                         number_of_steps=80,
                                         variable=self.temp_var,
                                         command=self._on_temp_change)
        self.temp_scale.pack(side="left", fill="x", expand=True, padx=4)
        self.temp_label = ctk.CTkLabel(row_temp, text="25 \u00b0C", width=40)
        self.temp_label.pack(side="right")

        note_cond = ctk.CTkLabel(
            op_frame,
            text="\u03bb comes from the light source config.\n"
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
        self.tab_beam = self.tabview.add("Beam Profile")
        self.tab_spec = self.tabview.add("Spectral PDE")
        self.tab_wave = self.tabview.add("Waveform Comparison")
        self.tab_stats = self.tabview.add("Statistics")

        self._build_hits_tab()
        self._build_heat_tab()
        self._build_beam_tab()
        self._build_spec_tab()
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

    def _build_beam_tab(self):
        self.tab_beam.grid_columnconfigure(0, weight=1)
        self.tab_beam.grid_columnconfigure(1, weight=1)
        self.tab_beam.grid_rowconfigure(0, weight=0)
        self.tab_beam.grid_rowconfigure(1, weight=1)
        ctk.CTkLabel(self.tab_beam, text="Model A",
                     font=ctk.CTkFont(weight="bold"),
                     text_color="#1565c0").grid(row=0, column=0, pady=2)
        ctk.CTkLabel(self.tab_beam, text="Model B",
                     font=ctk.CTkFont(weight="bold"),
                     text_color="#e53935").grid(row=0, column=1, pady=2)
        frame_a, self.beam_a_fig, self.beam_a_canvas = \
            self._canvas_with_toolbar(self.tab_beam)
        frame_a.grid(row=1, column=0, sticky="nsew", padx=2, pady=2)
        frame_b, self.beam_b_fig, self.beam_b_canvas = \
            self._canvas_with_toolbar(self.tab_beam)
        frame_b.grid(row=1, column=1, sticky="nsew", padx=2, pady=2)

    def _build_spec_tab(self):
        self.tab_spec.grid_columnconfigure(0, weight=1)
        self.tab_spec.grid_rowconfigure(0, weight=0)
        self.tab_spec.grid_rowconfigure(1, weight=1)
        bar = ctk.CTkFrame(self.tab_spec, fg_color="transparent")
        bar.grid(row=0, column=0, sticky="ew", padx=8, pady=(4, 0))
        self._edit_curves_btn = ctk.CTkButton(
            bar, text="Edit Curves...", width=120, height=28,
            font=ctk.CTkFont(size=11),
            command=self._open_curve_editor)
        self._edit_curves_btn.pack(side="left")
        self._reset_curves_btn = ctk.CTkButton(
            bar, text="Reset to Defaults", width=130, height=28,
            font=ctk.CTkFont(size=11),
            fg_color="transparent", border_width=1,
            command=self._reset_curves)
        self._reset_curves_btn.pack(side="left", padx=6)
        frame, self.spec_fig, self.spec_canvas = \
            self._canvas_with_toolbar(self.tab_spec, figsize=(9, 5))
        frame.grid(row=1, column=0, sticky="nsew", padx=4, pady=4)
        self._update_spec_tab()

    def _build_wave_tab(self):
        self.tab_wave.grid_columnconfigure(0, weight=1)
        self.tab_wave.grid_columnconfigure(1, weight=1)
        self.tab_wave.grid_rowconfigure(0, weight=0)
        self.tab_wave.grid_rowconfigure(1, weight=1)
        ctk.CTkLabel(self.tab_wave, text="Model A",
                     font=ctk.CTkFont(weight="bold"),
                     text_color="#1565c0").grid(row=0, column=0, pady=2)
        ctk.CTkLabel(self.tab_wave, text="Model B",
                     font=ctk.CTkFont(weight="bold"),
                     text_color="#e53935").grid(row=0, column=1, pady=2)
        frame, self.wave_fig, self.wave_canvas = \
            self._canvas_with_toolbar(self.tab_wave, figsize=(10, 5))
        frame.grid(row=1, column=0, columnspan=2, sticky="nsew",
                   padx=2, pady=2)
        ctrl_bar = ctk.CTkFrame(self.tab_wave, fg_color="transparent")
        ctrl_bar.grid(row=2, column=0, columnspan=2, sticky="ew",
                      padx=8, pady=(0, 4))
        self._dcr_cb = ctk.CTkCheckBox(
            ctrl_bar, text="DCR", variable=self._show_dcr,
            command=self._update_waveform)
        self._dcr_cb.pack(side="left", padx=(0, 8))
        self._ap_cb = ctk.CTkCheckBox(
            ctrl_bar, text="Afterpulses", variable=self._show_ap,
            command=self._update_waveform)
        self._ap_cb.pack(side="left", padx=(0, 8))
        self._xt_cb = ctk.CTkCheckBox(
            ctrl_bar, text="Crosstalk", variable=self._show_xtalk,
            command=self._update_waveform)
        self._xt_cb.pack(side="left")

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

        self.export_btn = ctk.CTkButton(
            self.tab_stats, text="Export Results...",
            height=32, font=ctk.CTkFont(size=12, weight="bold"),
            fg_color="#1565c0", hover_color="#1976d2",
            command=self._export_full_results)
        self.export_btn.grid(row=2, column=0, pady=(4, 8), padx=4)

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
        file_menu.add_command(label="Export Results CSV...",
                              command=self._export_full_results)
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

    def _on_temp_change(self, val):
        self.temp_label.configure(text=f"{float(val):.0f} \u00b0C")

    def _on_quick_pulse(self):
        from models.datasheets import get_model
        ma = self.model_a_sel.combo.get()
        mb = self.model_b_sel.combo.get()
        da = get_model(ma)
        db = get_model(mb)
        if not da or not db:
            self._status("Invalid model selected")
            return
        try:
            n_photons = int(float(self.q_photons_var.get()))
            wavelength = float(self.q_lambda_var.get())
        except ValueError:
            self._status("Invalid photon count or wavelength")
            return
        pulse_width_ns = self._optical_config.pulse_width_ns
        r = {
            "photons": max(n_photons, 1),
            "wavelength_nm": wavelength,
            "fwhm_nm": 2,
            "config_type": "LED",
            "led_type": "Quick Pulse",
            "pulse_width_ns": pulse_width_ns,
            "pulse_voltage": 5.0,
            "distance_cm": 10.0,
            "beam_sigma_um": 1e6,
        }
        self._optical_result = r
        temp = self.temp_var.get()
        self._status(f"Quick pulse: {n_photons:,} photons @ {wavelength} nm...")
        try:
            self._run_comparison(da, db, ma, mb, r,
                                 seed=np.random.randint(0, 2**31))
            extra = f" @ {temp:.0f}C" if temp != 25.0 else ""
            self._status(
                f"A: {self._result_a.fired_cells} cells "
                f"({self._result_a.total_firings} firings, "
                f"{self._result_a.occupancy:.1%}) | "
                f"B: {self._result_b.fired_cells} cells "
                f"({self._result_b.total_firings} firings, "
                f"{self._result_b.occupancy:.1%}) | "
                f"{n_photons:,} photons @ {wavelength}nm{extra}")
        except Exception as e:
            self._status(f"Error: {e}")

    def _on_compare(self):
        from models.datasheets import get_model
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
            self._run_comparison(da, db, ma, mb, r,
                                 seed=np.random.randint(0, 2**31))
            extra = ""
            temp = self.temp_var.get()
            if temp != 25.0:
                extra = f" @ {temp:.0f}C"
            self._status(
                f"A: {self._result_a.fired_cells} cells "
                f"({self._result_a.total_firings} firings, "
                f"{self._result_a.occupancy:.1%}) | "
                f"B: {self._result_b.fired_cells} cells "
                f"({self._result_b.total_firings} firings, "
                f"{self._result_b.occupancy:.1%}) | "
                f"{r['photons']:,} photons{extra}")
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

    def _run_comparison(self, da, db, name_a, name_b, opt_result,
                       seed: int = 42):
        vov_a = self.vov_a_var.get()
        vov_b = self.vov_b_var.get()
        wl = opt_result["wavelength_nm"]
        temp = self.temp_var.get()

        temp_a = apply_temperature(da, temp, vov_a)
        temp_b = apply_temperature(db, temp, vov_b)
        ov_a = apply_overvoltage(da, temp_a["vov_effective"])
        ov_b = apply_overvoltage(db, temp_b["vov_effective"])
        pde_a = 0.0
        pde_b = 0.0
        if da["spectral_min_nm"] <= wl <= da["spectral_max_nm"]:
            pde_a = ov_a["pde"] * apply_wavelength(da, wl)
        if db["spectral_min_nm"] <= wl <= db["spectral_max_nm"]:
            pde_b = ov_b["pde"] * apply_wavelength(db, wl)

        area_a = da["area_mm"] * da["area_mm"]
        area_b = db["area_mm"] * db["area_mm"]
        dcr_a = (ov_a["dcr_typ_kcps"] * 1000 * da["pixels"]) / area_a
        dcr_b = (ov_b["dcr_typ_kcps"] * 1000 * db["pixels"]) / area_b

        sipm_a = SiPMGeometry(da["nx"], da["ny"], da["pitch"],
                               da["fill_factor"])
        sipm_b = SiPMGeometry(db["nx"], db["ny"], db["pitch"],
                               db["fill_factor"])

        dcr_window = max(opt_result["pulse_width_ns"], 50.0)
        sim_a = SiPMSimulator(sipm_a, pde=pde_a, gain=ov_a["gain"],
                              dcr=dcr_a,
                              crosstalk_prob=ov_a["crosstalk"],
                              afterpulse_prob=da["afterpulse"],
                              dcr_time_window_ns=dcr_window)
        sim_b = SiPMSimulator(sipm_b, pde=pde_b, gain=ov_b["gain"],
                              dcr=dcr_b,
                              crosstalk_prob=ov_b["crosstalk"],
                              afterpulse_prob=db["afterpulse"],
                              dcr_time_window_ns=dcr_window)

        sim_a.seed(seed)
        sim_b.seed(seed + 1)

        beam_sigma = opt_result.get("beam_sigma_um", 1e6)
        path_type = opt_result.get("config_type", "LED")
        if path_type == "LED":
            src_a = UniformSource()
            src_b = UniformSource()
        else:
            cx_a = sipm_a.width / 2
            cy_a = sipm_a.height / 2
            cx_b = sipm_b.width / 2
            cy_b = sipm_b.height / 2
            src_a = GaussianSource(cx_a, cy_a, beam_sigma)
            src_b = GaussianSource(cx_b, cy_b, beam_sigma)

        n_photons = opt_result["photons"]
        recovery_a = da["recovery_ns"]
        recovery_b = db["recovery_ns"]

        self._result_a = sim_a.run_temporal(
            src_a, n_photons,
            pulse_width_ns=opt_result["pulse_width_ns"],
            recovery_time_ns=recovery_a)
        self._result_b = sim_b.run_temporal(
            src_b, n_photons,
            pulse_width_ns=opt_result["pulse_width_ns"],
            recovery_time_ns=recovery_b)

        pg_a = PulseGenerator(tau_rise=1e-9,
                              tau_fall=da["pulse_fall_ns"] * 1e-9,
                              gain=ov_a["gain"])
        pg_b = PulseGenerator(tau_rise=1e-9,
                              tau_fall=db["pulse_fall_ns"] * 1e-9,
                              gain=ov_b["gain"])

        def _build_waveforms(pg, result, recovery_ns):
            tail_ns = max(recovery_ns, 5.0 * pg.tau_fall * 1e9) + 40
            pri = result.event_times("photon_detected")
            xt = result.event_times("crosstalk")
            ap = result.event_times("afterpulse", fired_only=True)
            dk = result.event_times("dark", fired_only=True)
            max_t = 0.0
            for arr in [pri, xt, ap, dk]:
                if len(arr) > 0:
                    max_t = max(max_t, float(np.max(arr)))
            common_dur = max_t + tail_ns
            wf_pri = pg.generate_from_times(
                primary_times_ns=pri, duration_ns=common_dur)
            wf_pri_xt = pg.generate_from_times(
                primary_times_ns=pri, crosstalk_times_ns=xt,
                duration_ns=common_dur)
            wf_ap = pg.generate_from_times(
                primary_times_ns=pri, crosstalk_times_ns=xt,
                afterpulse_times_ns=ap, duration_ns=common_dur)
            wf_dark = pg.generate_from_times(
                dark_times_ns=dk, duration_ns=common_dur)
            wf_full = pg.generate_from_times(
                primary_times_ns=pri, crosstalk_times_ns=xt,
                afterpulse_times_ns=ap, dark_times_ns=dk,
                duration_ns=common_dur)
            return wf_pri, wf_pri_xt, wf_ap, wf_dark, wf_full

        (self._wf_a_primary, self._wf_a_primary_xt, self._wf_a_ap,
         self._wf_a_dark, self._wf_a) = _build_waveforms(
            pg_a, self._result_a, recovery_a)
        (self._wf_b_primary, self._wf_b_primary_xt, self._wf_b_ap,
         self._wf_b_dark, self._wf_b) = _build_waveforms(
            pg_b, self._result_b, recovery_b)

        self._pg_a = pg_a
        self._pg_b = pg_b

        self._sipm_a = sipm_a
        self._sipm_b = sipm_b
        self._current_model_a = name_a
        self._current_model_b = name_b
        self._temp_a = temp_a
        self._temp_b = temp_b

        self._update_hits()
        self._update_heatmaps()
        self._update_beam_profile()
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

    def _update_beam_profile(self):
        if self._optical_result is None or self._sipm_a is None:
            return
        beam_sigma = self._optical_result.get("beam_sigma_um", 1e6)
        path_type = self._optical_result.get("config_type", "LED")
        wl = self._optical_result.get("wavelength_nm", 450)
        self.beam_a_fig.clear()
        ax = self.beam_a_fig.add_subplot(111)
        plot_beam_profile(self._sipm_a, beam_sigma, path_type, wl, ax=ax)
        self.beam_a_fig.tight_layout()
        self.beam_a_canvas.draw()
        self.beam_b_fig.clear()
        ax = self.beam_b_fig.add_subplot(111)
        plot_beam_profile(self._sipm_b, beam_sigma, path_type, wl, ax=ax)
        self.beam_b_fig.tight_layout()
        self.beam_b_canvas.draw()

    def _update_spec_tab(self):
        from models.datasheets import SPECTRAL_RESPONSE, OV_CURVES
        self.spec_fig.clear()
        gs = self.spec_fig.add_gridspec(2, 3, height_ratios=[1, 1])
        ax_spec = self.spec_fig.add_subplot(gs[0, :])
        wl_raw = np.array(SPECTRAL_RESPONSE["wl"])
        wl_smooth = np.linspace(200, 950, 300)
        colors = {25: '#1e88e5', 50: '#ff8f00', 75: '#00897b'}
        nominal_pde = {25: 0.35, 50: 0.40, 75: 0.50}
        for pitch, key in [(25, "pde25"), (50, "pde50"), (75, "pde75")]:
            pde_raw = np.array(SPECTRAL_RESPONSE[key])
            pde_smooth = np.interp(wl_smooth, wl_raw, pde_raw)
            pde_abs = pde_smooth * nominal_pde[pitch] * 100
            ax_spec.plot(wl_smooth, pde_abs, color=colors[pitch],
                         linewidth=1.5,
                         label=f"{pitch}\u00b5m pitch "
                               f"(peak={max(pde_abs):.0f}%)")
            ax_spec.plot(wl_raw, pde_raw * nominal_pde[pitch] * 100,
                         color=colors[pitch], marker='o',
                         markersize=3, linestyle='', alpha=0.5)
        ax_spec.set_xlabel("Wavelength (nm)")
        ax_spec.set_ylabel("Absolute PDE (%)")
        ax_spec.set_title("Spectral Response (Absolute PDE)")
        ax_spec.set_xlim(200, 950)
        ax_spec.set_ylim(0, None)
        ax_spec.yaxis.set_major_locator(
            matplotlib.ticker.MultipleLocator(5))
        ax_spec.yaxis.set_minor_locator(
            matplotlib.ticker.MultipleLocator(1))
        ax_spec.grid(True, alpha=0.3)
        ax_spec.grid(True, which='minor', alpha=0.1)
        ax_spec.legend(fontsize=8, loc='upper right')
        ax_pde = self.spec_fig.add_subplot(gs[1, 0])
        ax_gain = self.spec_fig.add_subplot(gs[1, 1])
        ax_xt = self.spec_fig.add_subplot(gs[1, 2])
        for pitch in [25, 50, 75]:
            c = OV_CURVES[pitch]
            ax_pde.plot(c["vov"], c["pde"], color=colors[pitch],
                        linewidth=1.5, marker='o', markersize=3,
                        label=f"{pitch}\u00b5m ({max(c['pde']):.0f}%)")
            ax_gain.plot(c["vov"], c["gain"], color=colors[pitch],
                         linewidth=1.5, marker='o', markersize=3,
                         label=f"{pitch}\u00b5m "
                               f"({max(c['gain'])/1e6:.1f}M)")
            ax_xt.plot(c["vov"], c["xtalk"], color=colors[pitch],
                       linewidth=1.5, marker='o', markersize=3,
                       label=f"{pitch}\u00b5m ({max(c['xtalk']):.0f}%)")
        ax_pde.set_xlabel("Overvoltage (V)")
        ax_pde.set_ylabel("PDE (%)")
        ax_pde.set_title("PDE vs Vov")
        ax_pde.set_xlim(0, 10)
        ax_pde.set_ylim(10, 70)
        ax_pde.yaxis.set_major_locator(matplotlib.ticker.MultipleLocator(10))
        ax_pde.yaxis.set_minor_locator(matplotlib.ticker.MultipleLocator(5))
        ax_pde.legend(fontsize=7, loc='upper left')
        ax_pde.grid(True, alpha=0.3)
        ax_pde.grid(True, which='minor', alpha=0.1)
        ax_gain.set_xlabel("Overvoltage (V)")
        ax_gain.set_ylabel("Gain")
        ax_gain.set_title("Gain vs Vov")
        ax_gain.set_xlim(0, 10)
        ax_gain.set_ylim(0, 1.8e7)
        ax_gain.ticklabel_format(axis='y', style='scientific',
                                  scilimits=(0, 0))
        ax_gain.legend(fontsize=7, loc='upper left')
        ax_gain.grid(True, alpha=0.3)
        ax_gain.grid(True, which='minor', alpha=0.1)
        ax_xt.set_xlabel("Overvoltage (V)")
        ax_xt.set_ylabel("Crosstalk (%)")
        ax_xt.set_title("Crosstalk vs Vov")
        ax_xt.set_xlim(0, 10)
        ax_xt.set_ylim(0, 25)
        ax_xt.yaxis.set_major_locator(matplotlib.ticker.MultipleLocator(10))
        ax_xt.yaxis.set_minor_locator(matplotlib.ticker.MultipleLocator(5))
        ax_xt.legend(fontsize=7, loc='upper left')
        ax_xt.grid(True, alpha=0.3)
        ax_xt.grid(True, which='minor', alpha=0.1)
        self.spec_fig.suptitle("Digitalized Datasheet Curves",
                               fontsize=12, fontweight='bold')
        self.spec_fig.tight_layout()
        self.spec_canvas.draw()

    def _update_waveform(self):
        if (self._wf_a is None or self._wf_b is None
                or self._wf_a_primary is None or self._wf_b_primary is None
                or self._wf_a_primary_xt is None or self._wf_b_primary_xt is None
                or self._wf_a_dark is None or self._wf_b_dark is None
                or self._wf_a_ap is None or self._wf_b_ap is None
                or self._pg_a is None or self._pg_b is None):
            return
        show_dcr = self._show_dcr.get()
        show_ap = self._show_ap.get()
        show_xt = self._show_xtalk.get()
        self.wave_fig.clear()
        gs = self.wave_fig.add_gridspec(1, 2)
        ax_a = self.wave_fig.add_subplot(gs[0, 0])
        ax_b = self.wave_fig.add_subplot(gs[0, 1])
        for wf, primary, primary_xt, ap, dark, pg, ax, nm, clr in [
            (self._wf_a, self._wf_a_primary, self._wf_a_primary_xt,
             self._wf_a_ap, self._wf_a_dark, self._pg_a,
             ax_a, self._current_model_a, '#1565c0'),
            (self._wf_b, self._wf_b_primary, self._wf_b_primary_xt,
             self._wf_b_ap, self._wf_b_dark, self._pg_b,
             ax_b, self._current_model_b, '#e53935'),
        ]:
            if show_xt:
                amp = primary_xt.amplitude.copy()
                parts = ["Primary", "Crosstalk"]
            else:
                amp = primary.amplitude.copy()
                parts = ["Primary"]
            if show_dcr:
                amp += dark.amplitude
                parts.append("DCR")
            if show_ap:
                amp += (ap.amplitude - primary_xt.amplitude)
                parts.append("AP")
            label = " + ".join(parts)
            ax.plot(wf.time, amp, color=clr, linewidth=1.2, label=label)
            ax.fill_between(wf.time, 0, amp, alpha=0.1, color=clr)
            ref = pg._single_pulse(wf.time * 1e-9, 0)
            ax.plot(wf.time, ref, color='#333333', linewidth=0.8,
                    linestyle='--', alpha=0.5, label='1 cell (ref)')
            ax.set_xlabel('Time (ns)')
            ax.set_ylabel('Amplitude')
            ax.ticklabel_format(axis='y', style='scientific',
                                scilimits=(0, 0))
            ax.grid(True, alpha=0.3)
            ax.set_xlim(wf.time[0], wf.time[-1])
            ax.legend(fontsize=7, loc='upper right')
            ax.set_title(f"{'A' if ax is ax_a else 'B'}: {nm}", fontsize=9,
                         color=clr)
        self.wave_fig.suptitle(
            f"Waveform \u2014 {self._result_a.total_firings} vs "
            f"{self._result_b.total_firings} primary firings",
            fontsize=11, fontweight='bold')
        self.wave_fig.tight_layout()
        self.wave_canvas.draw()

    def _update_stats(self):
        ra, rb = self._result_a, self._result_b
        wf_a, wf_b = self._wf_a, self._wf_b
        ta = getattr(self, '_temp_a', {})
        tb = getattr(self, '_temp_b', {})
        header = f"{'Metric':<28} {'Model A':>14} {'Model B':>14}"
        sep = "-" * 60
        rows = [
            ("Temperature", ta.get("temperature_c", 25),
             tb.get("temperature_c", 25)),
            ("Vov nominal", ta.get("vov_nominal", 0),
             tb.get("vov_nominal", 0)),
            ("\u0394Vbr shift", ta.get("delta_vbr", 0),
             tb.get("delta_vbr", 0)),
            ("Vov effective", ta.get("vov_effective", 0),
             tb.get("vov_effective", 0)),
            ("", None, None),
            ("Photons generated", ra.photons_generated,
             rb.photons_generated),
            ("Photons detected", ra.photons_detected,
             rb.photons_detected),
            ("Photons blocked", ra.photons_blocked, rb.photons_blocked),
            ("Pixels (total cells)", ra.total_cells, rb.total_cells),
            ("Fired cells", ra.fired_cells, rb.fired_cells),
            ("Total firings", ra.total_firings, rb.total_firings),
            ("Occupancy", ra.occupancy, rb.occupancy),
            ("Effective PDE", ra.effective_pde, rb.effective_pde),
            ("Dark counts", ra.dark_counts, rb.dark_counts),
            ("Crosstalk fires", ra.crosstalk_fires, rb.crosstalk_fires),
            ("Afterpulse fires", ra.afterpulse_fires, rb.afterpulse_fires),
            ("SNR (signal/noise)", ra.snr, rb.snr),
            ("Dynamic range", ra.dynamic_range, rb.dynamic_range),
            ("Peak amplitude", wf_a.peak, wf_b.peak),
            ("Integrated charge", wf_a.charge, wf_b.charge),
        ]

        def fmt_val(v):
            if v is None:
                return ""
            if isinstance(v, float) and abs(v) < 0.1:
                return f"{v:.2%}"
            elif isinstance(v, float) and abs(v) > 1e3:
                return f"{v:.2e}"
            elif isinstance(v, float) and abs(v) < 20:
                return f"{v:.3f}"
            elif isinstance(v, float):
                return f"{v:.1f}"
            return str(v)

        lines = [header, sep]
        for name, va, vb in rows:
            if va is None and vb is None:
                lines.append("")
                continue
            lines.append(
                f"{name:<28} {fmt_val(va):>14} {fmt_val(vb):>14}")
        ratios = []
        if ra.fired_cells > 0 and rb.fired_cells > 0:
            ratios.append(
                f"Peak A/B={wf_a.peak/wf_b.peak:.3f} | "
                f"Charge A/B={wf_a.charge/wf_b.charge:.3f} | "
                f"Occ A/B={ra.occupancy/max(rb.occupancy,1e-9):.3f} | "
                f"SNR A/B={ra.snr/max(rb.snr,1e-9):.3f}")
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
        from models.datasheets import get_model
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
                self._status(
                    "Config contains legacy 'beam' key, ignored")
            self._status(f"Loaded {path}")
        except Exception as e:
            self._status(f"Error loading config: {e}")

    def _load_experimental(self):
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

    def _export_full_results(self):
        if self._result_a is None and self._result_b is None:
            self._status("Run comparison first.")
            return
        path = filedialog.asksaveasfilename(
            defaultextension=".csv",
            filetypes=[("CSV Files", "*.csv"),
                       ("All Files", "*.*")])
        if not path:
            return
        try:
            wl = (self._optical_result.get("wavelength_nm", 450)
                  if self._optical_result else 450)
            export_full_results(
                out_path=path,
                result_a=self._result_a,
                result_b=self._result_b,
                wf_a=self._wf_a,
                wf_b=self._wf_b,
                wf_a_primary=self._wf_a_primary,
                wf_b_primary=self._wf_b_primary,
                wf_a_primary_xt=self._wf_a_primary_xt,
                wf_b_primary_xt=self._wf_b_primary_xt,
                wf_a_ap=self._wf_a_ap,
                wf_b_ap=self._wf_b_ap,
                wf_a_dark=self._wf_a_dark,
                wf_b_dark=self._wf_b_dark,
                sipm_a=self._sipm_a,
                sipm_b=self._sipm_b,
                optical_result=self._optical_result,
                temp_a=getattr(self, '_temp_a', None),
                temp_b=getattr(self, '_temp_b', None),
                optical_config=self._optical_config,
                model_a_id=self._current_model_a,
                model_b_id=self._current_model_b,
                wavelength_nm=wl,
            )
            self._status(f"Exported to {path}")
        except Exception as e:
            self._status(f"Export error: {e}")

    def _show_about(self):
        messagebox.showinfo(
            "About",
            "SiPM Digital Twin \u2014 Model Comparison\n\n"
            "Compare two SiPM models under\n"
            "identical light source conditions.\n\n"
            "Models from datasheet catalog.\n"
            "Parameters: pitch, fill factor, PDE,\n"
            "gain, DCR, crosstalk, afterpulse,\n"
            "recovery time.")

    def _open_curve_editor(self):
        CurveEditorDialog(self, self._on_curves_saved)

    def _on_curves_saved(self):
        self._update_spec_tab()

    def _reset_curves(self):
        from models.datasheets import CURVES_FILE
        if CURVES_FILE.exists():
            CURVES_FILE.unlink()
        import models.datasheets as datasheets
        datasheets._load_user_curves()
        self._update_spec_tab()
        self._status("Curves reset to defaults")


def main():
    app = App()
    try:
        app.mainloop()
    except KeyboardInterrupt:
        app.destroy()


if __name__ == "__main__":
    main()
