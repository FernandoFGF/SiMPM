import tkinter as tk
import customtkinter as ctk
from optics.optical_chain import LED_DATABASE, OpticalConfig, calculate_photons


def _safe_float(var, default=0.0):
    try:
        return float(var.get())
    except (ValueError, tk.TclError):
        return default


class LightSourceDialog(ctk.CTkToplevel):
    def __init__(self, parent, config: OpticalConfig,
                 sensor_a_size, sensor_b_size, on_apply):
        super().__init__(parent)
        self.title("Light Source Configuration")
        self.geometry("550x780")
        self.resizable(True, True)
        self.minsize(500, 700)
        self.grab_set()

        self.config = config
        self.sensor_a_size = sensor_a_size
        self.sensor_b_size = sensor_b_size
        self.on_apply = on_apply

        self._build()
        self._update_preview()

    def _build(self):
        main = ctk.CTkFrame(self, fg_color="transparent")
        main.pack(fill="both", expand=True, padx=12, pady=12)

        ctk.CTkLabel(main, text="Light Source Configuration",
                     font=ctk.CTkFont(size=16, weight="bold")).pack(
            anchor="w", pady=(0, 8))

        led_group = ctk.CTkFrame(main)
        led_group.pack(fill="x", pady=4)
        ctk.CTkLabel(led_group, text="LED Type",
                     font=ctk.CTkFont(size=12, weight="bold")).pack(
            anchor="w", padx=8, pady=(6, 2))
        self.led_combo = ctk.CTkComboBox(
            led_group, values=list(LED_DATABASE.keys()),
            command=self._on_led_change)
        self.led_combo.set(self.config.led_type)
        self.led_combo.pack(fill="x", padx=8, pady=2)
        self.led_info = ctk.CTkLabel(
            led_group, text="", font=ctk.CTkFont(size=10),
            text_color="gray")
        self.led_info.pack(anchor="w", padx=8, pady=(0, 6))
        self._on_led_change(self.config.led_type)

        config_group = ctk.CTkFrame(main)
        config_group.pack(fill="x", pady=4)
        ctk.CTkLabel(config_group, text="Optical Path",
                     font=ctk.CTkFont(size=12, weight="bold")).pack(
            anchor="w", padx=8, pady=(6, 2))
        self.path_combo = ctk.CTkComboBox(
            config_group,
            values=["LED", "Fiber", "Monochromator",
                    "Fiber + Monochromator"],
            command=self._on_path_change)
        self.path_combo.set(self.config.config_type)
        self.path_combo.pack(fill="x", padx=8, pady=2)

        row_dist = ctk.CTkFrame(config_group, fg_color="transparent")
        row_dist.pack(fill="x", padx=8, pady=2)
        ctk.CTkLabel(row_dist, text="Distance", width=80,
                     anchor="w").pack(side="left")
        self.dist_var = tk.StringVar(
            value=str(self.config.distance_cm))
        self.dist_entry = ctk.CTkEntry(row_dist, width=80,
                                        textvariable=self.dist_var)
        self.dist_entry.pack(side="left")
        ctk.CTkLabel(row_dist, text="cm").pack(side="left", padx=4)

        self.mono_frame = ctk.CTkFrame(config_group, fg_color="transparent")
        ctk.CTkLabel(self.mono_frame, text="Mono \u03bb", width=80,
                     anchor="w").pack(side="left")
        self.mono_var = tk.StringVar(
            value=str(self.config.monochromator_wl_nm))
        self.mono_entry = ctk.CTkEntry(self.mono_frame, width=80,
                                        textvariable=self.mono_var)
        self.mono_entry.pack(side="left")
        ctk.CTkLabel(self.mono_frame, text="nm").pack(side="left", padx=4)
        self._on_path_change(self.config.config_type)

        att_frame = ctk.CTkFrame(config_group, fg_color="transparent")
        att_frame.pack(fill="x", padx=8, pady=2)
        ctk.CTkLabel(att_frame, text="Attenuator", width=80,
                     anchor="w").pack(side="left")
        self.att_var = tk.StringVar(value=str(self.config.attenuation_db))
        self.att_entry = ctk.CTkEntry(att_frame, width=80,
                                       textvariable=self.att_var)
        self.att_entry.pack(side="left")
        ctk.CTkLabel(att_frame, text="dB (0=none)").pack(
            side="left", padx=4)

        pulse_group = ctk.CTkFrame(main)
        pulse_group.pack(fill="x", pady=4)
        ctk.CTkLabel(pulse_group, text="Pulse Settings",
                     font=ctk.CTkFont(size=12, weight="bold")).pack(
            anchor="w", padx=8, pady=(6, 2))

        self._pulse_vars = {}
        defaults = {
            "pulse_voltage": self.config.pulse_voltage,
            "pulse_width_ns": self.config.pulse_width_ns,
            "resistance_ohm": self.config.resistance_ohm,
        }
        for label, var_attr, unit in [
            ("Voltage", "pulse_voltage", "V"),
            ("Width", "pulse_width_ns", "ns"),
            ("Resistance", "resistance_ohm", "\u03a9"),
        ]:
            row = ctk.CTkFrame(pulse_group, fg_color="transparent")
            row.pack(fill="x", padx=8, pady=2)
            ctk.CTkLabel(row, text=label, width=80,
                         anchor="w").pack(side="left")
            var = tk.StringVar(value=str(defaults[var_attr]))
            self._pulse_vars[var_attr] = var
            entry = ctk.CTkEntry(row, width=80, textvariable=var)
            entry.pack(side="left")
            ctk.CTkLabel(row, text=unit).pack(side="left", padx=4)

        self.preview = ctk.CTkTextbox(
            main, height=160, font=ctk.CTkFont(family="Consolas", size=11),
            wrap="none")
        self.preview.pack(fill="x", pady=8)

        btn_row = ctk.CTkFrame(main, fg_color="transparent")
        btn_row.pack(fill="x", pady=(4, 0))
        ctk.CTkButton(
            btn_row, text="Apply && Simulate", height=36,
            font=ctk.CTkFont(size=13, weight="bold"),
            command=self._apply).pack(side="right", padx=4)
        ctk.CTkButton(
            btn_row, text="Cancel", height=36,
            fg_color="transparent", border_width=1,
            command=self.destroy).pack(side="right", padx=4)

    def _on_led_change(self, choice):
        led = LED_DATABASE.get(choice, {})
        self.led_info.configure(
            text=f"\u03bb={led.get('wavelength_nm','?')}nm, "
                 f"\u0394\u03bb={led.get('fwhm_nm','?')}nm, "
                 f"Vf={led.get('vf','?')}V, "
                 f"\u03b7={led.get('efficiency',0)*100:.0f}%")

    def _on_path_change(self, choice):
        if choice in ("Monochromator", "Fiber + Monochromator"):
            self.mono_frame.pack(fill="x", padx=8, pady=2,
                                 after=self.path_combo)
        else:
            self.mono_frame.pack_forget()

    def _update_preview(self):
        self._sync_config()
        wa = (self.sensor_a_size[0] if self.sensor_a_size
              and self.sensor_a_size[0] > 0 else 3000)
        ha = (self.sensor_a_size[1] if self.sensor_a_size
              and self.sensor_a_size[1] > 0 else 3000)
        r = calculate_photons(self.config, wa, ha)

        lines = [
            f"LED: {self.config.led_type}",
            f"Path: {self.config.config_type}",
            f"Distance: {self.config.distance_cm} cm",
            f"Pulse: {self.config.pulse_voltage}V, "
            f"{self.config.pulse_width_ns}ns, "
            f"R={self.config.resistance_ohm}\u03a9",
            "",
        ]
        if "error" in r:
            lines.append(f"ERROR: {r['error']}")
        else:
            lines.extend([
                f"I_LED = {r['i_led_ma']} mA",
                f"P_opt  = {r['p_opt_mw']} mW",
                f"Photons emitted:  {r['photons_emitted']:,}",
                f"Photons at sensor: {r['photons']:,}",
                f"Wavelength: {r['wavelength_nm']} nm "
                f"(FWHM={r['fwhm_nm']} nm)",
            ])
            beam_info = {
                "LED": "Beam: Lambertian (wide cone)",
                "Fiber": "Beam: NA=0.22 (focused cone)",
                "Monochromator": "Beam: 5mrad (collimated)",
                "Fiber + Monochromator": "Beam: 5mrad (collimated fiber)",
            }
            lines.append(
                beam_info.get(r["config_type"], "Beam: unknown"))

        self.preview.configure(state="normal")
        self.preview.delete("1.0", "end")
        self.preview.insert("1.0", "\n".join(lines))
        self.preview.configure(state="disabled")

    def _sync_config(self):
        self.config.led_type = self.led_combo.get()
        self.config.config_type = self.path_combo.get()
        self.config.distance_cm = _safe_float(self.dist_var,
                                              self.config.distance_cm)
        self.config.monochromator_wl_nm = _safe_float(
            self.mono_var, self.config.monochromator_wl_nm)
        self.config.pulse_voltage = _safe_float(
            self._pulse_vars["pulse_voltage"],
            self.config.pulse_voltage)
        self.config.pulse_width_ns = _safe_float(
            self._pulse_vars["pulse_width_ns"],
            self.config.pulse_width_ns)
        self.config.resistance_ohm = _safe_float(
            self._pulse_vars["resistance_ohm"],
            self.config.resistance_ohm)
        self.config.attenuation_db = _safe_float(
            self.att_var, self.config.attenuation_db)

    def _apply(self):
        self._sync_config()
        self._update_preview()
        wa = (self.sensor_a_size[0] if self.sensor_a_size
              and self.sensor_a_size[0] > 0 else 3000)
        ha = (self.sensor_a_size[1] if self.sensor_a_size
              and self.sensor_a_size[1] > 0 else 3000)
        r = calculate_photons(self.config, wa, ha)
        if r.get("error"):
            return
        self.on_apply(self.config, r)
        self.destroy()
