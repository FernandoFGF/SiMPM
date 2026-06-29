import customtkinter as ctk

from models.datasheets import get_model, list_display_names


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
