"""FVG Story Editor – magyar nyelvű asztali forgatókönyvíró."""

import json
import traceback
import importlib.util
import tempfile
import sys
from datetime import datetime
from html import escape
from pathlib import Path
import tkinter as tk
from tkinter import filedialog, messagebox, simpledialog, ttk


class UvegGomb(tk.Canvas):
    """Lekerekített, üvegszerű gomb kizárólag Tkinterrel - Windows és Linux alatt is azonos."""
    def __init__(self, szulo, text, command, accent=False, width=None, hatter="#1a1f2b", **kwargs):
        self.accent = accent
        self.command = command
        self.szinek = {
            "alap": "#2d374a", "aktiv": "#3a4961", "keret": "#52617a",
            "kiemelt": "#f5a623", "kiemelt_aktiv": "#ffc04d", "szoveg": "#f4f7fb", "sotet": "#15191f",
        }
        betu = ("Sans", 10, "bold" if accent else "normal")
        self.felirat = text
        szelesseg = width or max(94, len(text) * 8 + 30)
        super().__init__(szulo, width=szelesseg, height=38, highlightthickness=0, bd=0, cursor="hand2", **kwargs)
        self.configure(bg=hatter, takefocus=1)
        self.bind("<Configure>", lambda _e: self.rajzol())
        self.bind("<Enter>", lambda _e: self.rajzol(True))
        self.bind("<Leave>", lambda _e: self.rajzol(False))
        self.bind("<Button-1>", lambda _e: self.command())
        self.bind("<Return>", lambda _e: self.command())
        self.bind("<space>", lambda _e: self.command())
        self.bind("<ButtonRelease-1>", lambda _e: self.focus_set())
        self.betutipus = betu
        self.rajzol()

    def lekerekitett_teglalap(self, x1, y1, x2, y2, sugar, **kwargs):
        pontok = [x1+sugar, y1, x2-sugar, y1, x2, y1, x2, y1+sugar, x2, y2-sugar, x2, y2,
                  x2-sugar, y2, x1+sugar, y2, x1, y2, x1, y2-sugar, x1, y1+sugar, x1, y1]
        return self.create_polygon(pontok, smooth=True, splinesteps=18, **kwargs)

    def rajzol(self, aktiv=False):
        self.delete("all")
        w, h = max(self.winfo_width(), 20), max(self.winfo_height(), 20)
        if self.accent:
            hatter = self.szinek["kiemelt_aktiv"] if aktiv else self.szinek["kiemelt"]
            szoveg = self.szinek["sotet"]
            keret = self.szinek["kiemelt_aktiv"]
        else:
            hatter = self.szinek["aktiv"] if aktiv else self.szinek["alap"]
            szoveg = self.szinek["szoveg"]
            keret = "#7484a0" if aktiv else self.szinek["keret"]
        # Finom felső fénycsík: ettől kap üvegszerű, rétegzett érzetet.
        self.lekerekitett_teglalap(1, 1, w-1, h-1, 13, fill=hatter, outline=keret, width=1)
        self.create_line(14, 4, w-14, 4, fill="#ffffff" if self.accent else "#66758f")
        self.create_text(w / 2, h / 2 + 1, text=self.felirat, fill=szoveg, font=self.betutipus)


class ForgatokonyvIro(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("FVG Story Editor — Íróstúdió")
        self.geometry("1120x720")
        self.minsize(860, 550)
        self.fajl_utvonal = None
        self.projekt = self.uj_projekt_adat()
        self.aktualis_jelenet = None
        self.letrehoz_felulet()
        self.uj_projekt()
        self.after(350, self.indulasi_ellenorzes)
        self.after(180000, self.auto_mentes)
        if len(sys.argv) > 1 and sys.argv[1]:
            self.after(120, lambda: self.megnyit_utvonal(sys.argv[1]))

    @staticmethod
    def uj_projekt_adat():
        return {"cim": "Új forgatókönyv", "szerzo": "", "jelenetek": [], "karakterek": [], "karakter_adatok": {}, "verziok": []}

    def letrehoz_felulet(self):
        self.szinek = {
            "hatterszin": "#10131a", "panel": "#1a1f2b", "panel_vilagos": "#242b3a",
            "szoveg": "#f2f4f8", "halvany": "#aeb8c9", "kiemeles": "#f5a623",
            "kiemeles_sotet": "#d88713", "vonal": "#333c4e", "szerkeszto": "#171c26",
        }
        self.configure(bg=self.szinek["hatterszin"])
        self.option_add("*Font", "Sans 10")
        self.beallit_stilusok()
        menu = tk.Menu(self)
        fajl = tk.Menu(menu, tearoff=False)
        fajl.add_command(label="Új projekt", command=self.uj_projekt, accelerator="Ctrl+N")
        fajl.add_command(label="Megnyitás…", command=self.megnyit, accelerator="Ctrl+O")
        fajl.add_command(label="Mentés", command=self.ment, accelerator="Ctrl+S")
        fajl.add_command(label="Mentés másként…", command=self.ment_maskent)
        fajl.add_separator()
        fajl.add_command(label="Verzióelőzmények…", command=self.verzio_elzmenyek, accelerator="Ctrl+H")
        fajl.add_command(label="Exportálás PDF-be…", command=self.pdf_export)
        fajl.add_separator()
        fajl.add_command(label="Kilépés", command=self.destroy)
        menu.add_cascade(label="Fájl", menu=fajl)
        eszkozok = tk.Menu(menu, tearoff=False)
        eszkozok.add_command(label="Keresés és csere…", command=self.keres_es_csere, accelerator="Ctrl+F")
        eszkozok.add_command(label="Statisztikák…", command=self.statisztikak)
        eszkozok.add_separator()
        eszkozok.add_command(label="Karakterlap szerkesztése…", command=self.karakterlap)
        eszkozok.add_command(label="Aktuális jelenet kártyája…", command=self.jelenetkartya)
        eszkozok.add_separator()
        eszkozok.add_command(label="Komponensek ellenőrzése", command=lambda: self.indulasi_ellenorzes(reszletes=True))
        menu.add_cascade(label="Eszközök", menu=eszkozok)
        self.config(menu=menu)
        self.bind_all("<Control-n>", lambda e: self.uj_projekt())
        self.bind_all("<Control-o>", lambda e: self.megnyit())
        self.bind_all("<Control-s>", lambda e: self.ment())
        self.bind_all("<Control-h>", lambda e: self.verzio_elzmenyek())
        self.bind_all("<Control-f>", lambda e: self.keres_es_csere())

        fejlec = ttk.Frame(self, style="Header.TFrame", padding=(22, 18, 22, 14))
        fejlec.pack(fill="x")
        jelveny = ttk.Label(fejlec, text="✦", style="Brand.TLabel")
        jelveny.pack(side="left", padx=(0, 10))
        cimkeret = ttk.Frame(fejlec, style="Header.TFrame")
        cimkeret.pack(side="left")
        ttk.Label(cimkeret, text="FVG STORY EDITOR", style="AppTitle.TLabel").pack(anchor="w")
        ttk.Label(cimkeret, text="A történeted itt kap formát.", style="Tagline.TLabel").pack(anchor="w")
        UvegGomb(fejlec, "Mentés", self.ment, accent=True, width=112, hatter=self.szinek["hatterszin"]).pack(side="right", pady=4)

        info = ttk.Frame(self, style="Header.TFrame", padding=(22, 2, 22, 16))
        info.pack(fill="x")
        ttk.Label(info, text="Cím:").pack(side="left")
        self.cim = ttk.Entry(info, width=38)
        self.cim.pack(side="left", padx=(5, 18))
        ttk.Label(info, text="Szerző:").pack(side="left")
        self.szerzo = ttk.Entry(info, width=30)
        self.szerzo.pack(side="left", padx=5)

        panel = ttk.PanedWindow(self, orient="horizontal", style="Studio.TPanedwindow")
        panel.pack(fill="both", expand=True, padx=22, pady=(0, 18))

        bal = ttk.Labelframe(panel, text="Jelenetek", padding=8)
        # A weight opció nem érhető el minden Ubuntuhoz csomagolt Tk verzióban.
        panel.add(bal)
        self.jelenet_lista = tk.Listbox(bal, exportselection=False, activestyle="none",
            bg=self.szinek["panel"], fg=self.szinek["szoveg"], selectbackground=self.szinek["kiemeles"],
            selectforeground="#15191f", highlightthickness=0, borderwidth=0, font=("Sans", 10))
        self.jelenet_lista.pack(fill="both", expand=True)
        self.jelenet_lista.bind("<<ListboxSelect>>", self.jelenet_kivalaszt)
        gombok = ttk.Frame(bal)
        gombok.pack(fill="x", pady=(8, 0))
        UvegGomb(gombok, "+ Jelenet", self.uj_jelenet, accent=True, width=102).pack(side="left")
        UvegGomb(gombok, "Törlés", self.jelenet_torles, width=80).pack(side="right")
        rendezes = ttk.Frame(bal)
        rendezes.pack(fill="x", pady=(8, 0))
        UvegGomb(rendezes, "↑ Feljebb", lambda: self.jelenet_mozgat(-1), width=92).pack(side="left")
        UvegGomb(rendezes, "↓ Lejjebb", lambda: self.jelenet_mozgat(1), width=92).pack(side="right")

        kozep = ttk.Labelframe(panel, text="Jelenet szerkesztése", padding=10)
        panel.add(kozep)
        sor = ttk.Frame(kozep)
        sor.pack(fill="x", pady=(0, 8))
        ttk.Label(sor, text="Fejléc:").pack(side="left")
        self.jelenet_fejlec = ttk.Entry(sor)
        self.jelenet_fejlec.pack(side="left", fill="x", expand=True, padx=(6, 0))
        eszkoztar = ttk.Frame(kozep)
        eszkoztar.pack(fill="x", pady=(0, 7))
        ttk.Label(eszkoztar, text="Aktuális sor típusa:").pack(side="left")
        self.blokk_tipus = tk.StringVar(value="Akció")
        ttk.Combobox(eszkoztar, textvariable=self.blokk_tipus, state="readonly", width=19,
            values=("Akció", "Karakter", "Párbeszéd", "Zárójeles utasítás")).pack(side="left", padx=7)
        UvegGomb(eszkoztar, "Formázás alkalmazása", self.blokk_formazas, width=174).pack(side="left")
        ttk.Label(kozep, text="A jelenet szövege:").pack(anchor="w")
        self.szoveg = tk.Text(kozep, wrap="word", undo=True, padx=18, pady=16,
            bg=self.szinek["szerkeszto"], fg=self.szinek["szoveg"], insertbackground=self.szinek["kiemeles"],
            selectbackground="#46516a", relief="flat", highlightthickness=1,
            highlightbackground=self.szinek["vonal"], highlightcolor=self.szinek["kiemeles"],
            font=("Sans", 12), spacing1=3, spacing3=5)
        self.szoveg.pack(fill="both", expand=True, pady=(4, 8))
        self.szoveg.tag_configure("Akció", justify="left", lmargin1=0, lmargin2=0, spacing1=7)
        self.szoveg.tag_configure("Karakter", justify="center", font=("Sans", 11, "bold"), foreground=self.szinek["kiemeles"], spacing1=12)
        self.szoveg.tag_configure("Párbeszéd", justify="left", lmargin1=70, lmargin2=70, rmargin=70, spacing3=7)
        self.szoveg.tag_configure("Zárójeles utasítás", justify="left", lmargin1=88, lmargin2=88, rmargin=88, foreground=self.szinek["halvany"])
        UvegGomb(kozep, "Jelenet módosításainak rögzítése", self.jelenet_rogzit, accent=True, width=264).pack(anchor="e")

        jobb = ttk.Labelframe(panel, text="Karakterek", padding=8)
        panel.add(jobb)
        self.karakter_lista = tk.Listbox(jobb, height=8, activestyle="none",
            bg=self.szinek["panel"], fg=self.szinek["szoveg"], selectbackground=self.szinek["kiemeles"],
            selectforeground="#15191f", highlightthickness=0, borderwidth=0, font=("Sans", 10))
        self.karakter_lista.pack(fill="both", expand=True)
        kg = ttk.Frame(jobb)
        kg.pack(fill="x", pady=(8, 0))
        ttk.Button(kg, text="+", width=3, command=self.karakter_hozzaad).pack(side="left")
        ttk.Button(kg, text="−", width=3, command=self.karakter_torol).pack(side="right")
        ttk.Label(jobb, text="Tipp: a neveket szabadon beírhatod a jelenet szövegébe.", wraplength=170).pack(anchor="w", pady=(12, 0))

        self.statusz = ttk.Label(self, text="●  Készen áll az írásra", style="Status.TLabel", anchor="w", padding=(22, 7))
        self.statusz.pack(fill="x", side="bottom")

    def beallit_stilusok(self):
        """Egységes, nyugodt sötét írói felület."""
        s = self.szinek
        stilus = ttk.Style(self)
        stilus.theme_use("clam")
        stilus.configure(".", background=s["hatterszin"], foreground=s["szoveg"], font=("Sans", 10))
        stilus.configure("Header.TFrame", background=s["hatterszin"])
        stilus.configure("TFrame", background=s["panel"])
        stilus.configure("TLabelframe", background=s["panel"], bordercolor=s["vonal"], relief="solid")
        stilus.configure("TLabelframe.Label", background=s["panel"], foreground=s["halvany"], font=("Sans", 9, "bold"))
        stilus.configure("TLabel", background=s["panel"], foreground=s["szoveg"])
        stilus.configure("Brand.TLabel", background=s["hatterszin"], foreground=s["kiemeles"], font=("Sans", 26, "bold"))
        stilus.configure("AppTitle.TLabel", background=s["hatterszin"], foreground=s["szoveg"], font=("Sans", 16, "bold"))
        stilus.configure("Tagline.TLabel", background=s["hatterszin"], foreground=s["halvany"], font=("Sans", 9))
        stilus.configure("TEntry", fieldbackground="#0e1118", foreground=s["szoveg"], bordercolor=s["vonal"], lightcolor=s["vonal"], insertcolor=s["kiemeles"], padding=7)
        stilus.map("TEntry", bordercolor=[("focus", s["kiemeles"])])
        stilus.configure("TButton", background=s["panel_vilagos"], foreground=s["szoveg"], borderwidth=0, padding=(10, 7))
        stilus.map("TButton", background=[("active", "#303a4d")])
        stilus.configure("Accent.TButton", background=s["kiemeles"], foreground="#17191e", font=("Sans", 10, "bold"), padding=(12, 8))
        stilus.map("Accent.TButton", background=[("active", s["kiemeles_sotet"])])
        stilus.configure("Studio.TPanedwindow", background=s["hatterszin"], sashwidth=8)
        stilus.configure("Status.TLabel", background="#0b0e14", foreground=s["halvany"], font=("Sans", 9))

    def uj_projekt(self):
        if self.projekt["jelenetek"] and not messagebox.askyesno("Új projekt", "A nem mentett változások elveszhetnek. Folytatod?"):
            return
        self.projekt, self.fajl_utvonal, self.aktualis_jelenet = self.uj_projekt_adat(), None, None
        self.cim.delete(0, "end"); self.cim.insert(0, self.projekt["cim"])
        self.szerzo.delete(0, "end")
        self.frissit_listak(); self.jelenet_mezo_tisztit()
        self.statusz.config(text="Új projekt létrehozva.")

    def uj_jelenet(self):
        self.jelenet_rogzit()
        self.projekt["jelenetek"].append({"fejlec": "INT. HELYSZÍN – NAPPAL", "szoveg": "", "blokkok": {}, "kartya": {}})
        self.frissit_jelenetek()
        i = len(self.projekt["jelenetek"]) - 1
        self.jelenet_lista.selection_set(i); self.jelenet_kivalaszt()

    def jelenet_kivalaszt(self, _esemeny=None):
        k = self.jelenet_lista.curselection()
        if not k: return
        self.jelenet_rogzit()
        self.aktualis_jelenet = k[0]
        jelenet = self.projekt["jelenetek"][self.aktualis_jelenet]
        self.jelenet_fejlec.delete(0, "end"); self.jelenet_fejlec.insert(0, jelenet["fejlec"])
        self.szoveg.delete("1.0", "end"); self.szoveg.insert("1.0", jelenet["szoveg"])
        self.blokkok_rajzol(jelenet.get("blokkok", {}))

    def jelenet_rogzit(self):
        if self.aktualis_jelenet is None: return
        jelenet = self.projekt["jelenetek"][self.aktualis_jelenet]
        jelenet["fejlec"] = self.jelenet_fejlec.get().strip() or "CÍM NÉLKÜLI JELENET"
        jelenet["szoveg"] = self.szoveg.get("1.0", "end-1c")
        jelenet.setdefault("blokkok", {})
        self.frissit_jelenetek(kijelolt=self.aktualis_jelenet)

    def jelenet_mozgat(self, irany):
        if self.aktualis_jelenet is None:
            return
        uj_index = self.aktualis_jelenet + irany
        if not 0 <= uj_index < len(self.projekt["jelenetek"]):
            return
        self.jelenet_rogzit()
        jelenetek = self.projekt["jelenetek"]
        jelenetek[self.aktualis_jelenet], jelenetek[uj_index] = jelenetek[uj_index], jelenetek[self.aktualis_jelenet]
        self.aktualis_jelenet = uj_index
        self.frissit_jelenetek(kijelolt=uj_index)
        self.statusz.config(text="●  Jelenet átrendezve")

    def blokk_formazas(self):
        """A kurzor sorát forgatókönyvblokkká alakítja; a típus mentéskor is megmarad."""
        if self.aktualis_jelenet is None:
            return
        sor = self.szoveg.index("insert").split(".")[0]
        jelenet = self.projekt["jelenetek"][self.aktualis_jelenet]
        jelenet.setdefault("blokkok", {})[sor] = self.blokk_tipus.get()
        self.blokkok_rajzol(jelenet["blokkok"])
        self.statusz.config(text=f"●  Sor formázva: {self.blokk_tipus.get()}")

    def blokkok_rajzol(self, blokkok):
        for tipus in ("Akció", "Karakter", "Párbeszéd", "Zárójeles utasítás"):
            self.szoveg.tag_remove(tipus, "1.0", "end")
        for sor, tipus in blokkok.items():
            if tipus in ("Akció", "Karakter", "Párbeszéd", "Zárójeles utasítás"):
                self.szoveg.tag_add(tipus, f"{sor}.0", f"{sor}.end")

    def jelenet_torles(self):
        if self.aktualis_jelenet is None: return
        if not messagebox.askyesno("Jelenet törlése", "Biztosan törlöd ezt a jelenetet?"): return
        del self.projekt["jelenetek"][self.aktualis_jelenet]
        self.aktualis_jelenet = None; self.frissit_jelenetek(); self.jelenet_mezo_tisztit()

    def karakter_hozzaad(self):
        nev = simpledialog.askstring("Új karakter", "A karakter neve:", parent=self)
        if nev and nev.strip():
            nev = nev.strip()
            self.projekt["karakterek"].append(nev)
            self.projekt.setdefault("karakter_adatok", {})[nev] = {"leiras": "", "cel": "", "konfliktus": "", "hattersztori": ""}
            self.frissit_karakterek()

    def karakter_torol(self):
        k = self.karakter_lista.curselection()
        if k:
            nev = self.projekt["karakterek"].pop(k[0])
            self.projekt.setdefault("karakter_adatok", {}).pop(nev, None)
            self.frissit_karakterek()

    def frissit_jelenetek(self, kijelolt=None):
        self.jelenet_lista.delete(0, "end")
        for i, j in enumerate(self.projekt["jelenetek"], 1): self.jelenet_lista.insert("end", f"{i:02d}. {j['fejlec']}")
        if kijelolt is not None: self.jelenet_lista.selection_set(kijelolt)

    def frissit_karakterek(self):
        self.karakter_lista.delete(0, "end")
        for nev in self.projekt["karakterek"]: self.karakter_lista.insert("end", nev)

    def frissit_listak(self): self.frissit_jelenetek(); self.frissit_karakterek()
    def jelenet_mezo_tisztit(self): self.jelenet_fejlec.delete(0, "end"); self.szoveg.delete("1.0", "end")
    def adatokat_osszegyujt(self):
        self.jelenet_rogzit(); self.projekt["cim"] = self.cim.get().strip() or "Új forgatókönyv"; self.projekt["szerzo"] = self.szerzo.get().strip()

    def verzio_pillanatkep(self):
        """Elmenti a projekt aktuális állapotát egy visszaállítható változatként."""
        adat = {
            "cim": self.projekt["cim"], "szerzo": self.projekt["szerzo"],
            "jelenetek": self.projekt["jelenetek"], "karakterek": self.projekt["karakterek"], "karakter_adatok": self.projekt.get("karakter_adatok", {}),
        }
        # JSON-körrel mély másolat készül, így a régi változat nem módosul később.
        masolat = json.loads(json.dumps(adat, ensure_ascii=False))
        idobelyeg = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        self.projekt.setdefault("verziok", []).append({"ido": idobelyeg, "adat": masolat})
        # Az utolsó 30 állapotot tartjuk meg, hogy a fájl kezelhető méretű maradjon.
        self.projekt["verziok"] = self.projekt["verziok"][-30:]

    def ment(self):
        if not self.fajl_utvonal: return self.ment_maskent()
        self.adatokat_osszegyujt()
        try:
            self.verzio_pillanatkep()
            Path(self.fajl_utvonal).write_text(json.dumps(self.projekt, ensure_ascii=False, indent=2), encoding="utf-8")
            self.statusz.config(text=f"●  Mentve — {len(self.projekt['verziok'])} változat az előzményekben")
        except OSError as hiba: messagebox.showerror("Mentési hiba", str(hiba))

    def ment_maskent(self):
        utvonal = filedialog.asksaveasfilename(defaultextension=".fvgscript", filetypes=[("FVG Story Editor projekt", "*.fvgscript"), ("Korábbi forgatókönyv projekt", "*.forgatokonyv.json"), ("JSON", "*.json")])
        if utvonal: self.fajl_utvonal = utvonal; self.ment()

    def megnyit(self):
        utvonal = filedialog.askopenfilename(filetypes=[("FVG Story Editor projekt", "*.fvgscript"), ("Korábbi forgatókönyv projekt", "*.forgatokonyv.json *.json"), ("Minden fájl", "*.*")])
        if not utvonal: return
        self.megnyit_utvonal(utvonal)

    def megnyit_utvonal(self, utvonal):
        try:
            adat = json.loads(Path(utvonal).read_text(encoding="utf-8"))
            if not all(k in adat for k in ("cim", "szerzo", "jelenetek", "karakterek")): raise ValueError("Ez nem érvényes FVG Story Editor projekt.")
            adat.setdefault("verziok", [])
            adat.setdefault("karakter_adatok", {})
            for jelenet in adat["jelenetek"]:
                jelenet.setdefault("blokkok", {})
                jelenet.setdefault("kartya", {})
            self.projekt, self.fajl_utvonal, self.aktualis_jelenet = adat, utvonal, None
            self.cim.delete(0, "end"); self.cim.insert(0, adat["cim"])
            self.szerzo.delete(0, "end"); self.szerzo.insert(0, adat["szerzo"])
            self.frissit_listak(); self.jelenet_mezo_tisztit(); self.statusz.config(text=f"Megnyitva: {utvonal}")
        except (OSError, ValueError, json.JSONDecodeError) as hiba: messagebox.showerror("Megnyitási hiba", str(hiba))

    def pdf_export(self):
        """A jeleneteket nyomtatható, szabványos közelségű PDF-forgatókönyvvé alakítja."""
        self.adatokat_osszegyujt()
        utvonal = filedialog.asksaveasfilename(defaultextension=".pdf",
            initialfile=f"{self.projekt['cim']}.pdf", filetypes=[("PDF dokumentum", "*.pdf")])
        if not utvonal:
            return
        try:
            from reportlab.lib.enums import TA_CENTER, TA_LEFT
            from reportlab.lib.pagesizes import A4
            from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
            from reportlab.lib.units import cm
            from reportlab.platypus import PageBreak, Paragraph, SimpleDocTemplate, Spacer
        except ImportError:
            messagebox.showerror("PDF export", "A PDF-exporthoz hiányzik a ReportLab.\n\nUbuntu: sudo apt install python3-reportlab")
            return
        try:
            dokumentum = SimpleDocTemplate(utvonal, pagesize=A4, leftMargin=2.5 * cm, rightMargin=2.5 * cm,
                topMargin=2.3 * cm, bottomMargin=2.2 * cm, title=self.projekt["cim"], author=self.projekt["szerzo"])
            alap = getSampleStyleSheet()["Normal"]
            stilusok = {
                "cim": ParagraphStyle("Cim", parent=alap, fontName="Helvetica-Bold", fontSize=20, leading=25, alignment=TA_CENTER, spaceAfter=12),
                "szerzo": ParagraphStyle("Szerzo", parent=alap, fontSize=11, leading=15, alignment=TA_CENTER, textColor="#555555"),
                "fejlec": ParagraphStyle("Fejlec", parent=alap, fontName="Helvetica-Bold", fontSize=10, leading=14, spaceBefore=12, spaceAfter=6),
                "Akció": ParagraphStyle("Akcio", parent=alap, fontName="Courier", fontSize=10, leading=14, spaceAfter=5),
                "Karakter": ParagraphStyle("Karakter", parent=alap, fontName="Courier-Bold", fontSize=10, leading=14, alignment=TA_CENTER, spaceBefore=8),
                "Párbeszéd": ParagraphStyle("Parbeszed", parent=alap, fontName="Courier", fontSize=10, leading=14, leftIndent=1.8 * cm, rightIndent=1.8 * cm, spaceAfter=5),
                "Zárójeles utasítás": ParagraphStyle("Zarojel", parent=alap, fontName="Courier-Oblique", fontSize=9, leading=12, leftIndent=2.2 * cm, rightIndent=2.2 * cm),
            }
            elemek = [Spacer(1, 5.2 * cm), Paragraph(escape(self.projekt["cim"]), stilusok["cim"]),
                Paragraph(escape(self.projekt["szerzo"] or ""), stilusok["szerzo"]), PageBreak()]
            for jelenet in self.projekt["jelenetek"]:
                elemek.append(Paragraph(escape(jelenet["fejlec"]), stilusok["fejlec"]))
                blokkok = jelenet.get("blokkok", {})
                for sorszam, sor in enumerate(jelenet["szoveg"].splitlines(), 1):
                    tipus = blokkok.get(str(sorszam), "Akció")
                    elemek.append(Paragraph(escape(sor) or " ", stilusok.get(tipus, stilusok["Akció"])))
                elemek.append(Spacer(1, 8))
            def labléc(canvas, doc):
                canvas.saveState(); canvas.setFont("Helvetica", 8); canvas.setFillColor("#666666")
                canvas.drawCentredString(A4[0] / 2, 1.25 * cm, f"FVG Story Editor  •  {doc.page}"); canvas.restoreState()
            dokumentum.build(elemek, onFirstPage=labléc, onLaterPages=labléc)
            self.statusz.config(text=f"●  PDF export elkészült: {Path(utvonal).name}")
            messagebox.showinfo("PDF export", f"Elkészült a PDF:\n{utvonal}")
        except OSError as hiba:
            messagebox.showerror("PDF export", str(hiba))

    def keres_es_csere(self):
        self.adatokat_osszegyujt()
        ablak = tk.Toplevel(self); ablak.title("Keresés és csere"); ablak.configure(bg=self.szinek["panel"]); ablak.transient(self)
        kereses, csere = ttk.Entry(ablak, width=42), ttk.Entry(ablak, width=42)
        ttk.Label(ablak, text="Keresett szöveg:").pack(anchor="w", padx=18, pady=(18, 3)); kereses.pack(padx=18)
        ttk.Label(ablak, text="Csere erre:").pack(anchor="w", padx=18, pady=(12, 3)); csere.pack(padx=18)
        def ker():
            s = kereses.get()
            if not s: return
            kezdet = self.szoveg.search(s, "insert", stopindex="end", nocase=True) or self.szoveg.search(s, "1.0", stopindex="insert", nocase=True)
            if kezdet:
                vege = f"{kezdet}+{len(s)}c"; self.szoveg.tag_remove("keresat", "1.0", "end"); self.szoveg.tag_add("keresat", kezdet, vege); self.szoveg.mark_set("insert", vege); self.szoveg.see(kezdet)
            else: messagebox.showinfo("Keresés", "Nincs találat.", parent=ablak)
        def csere_minden():
            s, u = kereses.get(), csere.get()
            if not s: return
            darab = 0
            for jelenet in self.projekt["jelenetek"]:
                darab += jelenet["szoveg"].lower().count(s.lower()); jelenet["szoveg"] = jelenet["szoveg"].replace(s, u)
            if self.aktualis_jelenet is not None:
                aktualis = self.projekt["jelenetek"][self.aktualis_jelenet]
                self.szoveg.delete("1.0", "end"); self.szoveg.insert("1.0", aktualis["szoveg"])
                self.blokkok_rajzol(aktualis.get("blokkok", {}))
            self.statusz.config(text=f"●  {darab} csere elvégezve")
        g = ttk.Frame(ablak, padding=18); g.pack(fill="x")
        UvegGomb(g, "Keresés", ker, width=90).pack(side="left")
        UvegGomb(g, "Összes cseréje", csere_minden, accent=True, width=130).pack(side="right")
        self.szoveg.tag_configure("keresat", background=self.szinek["kiemeles"], foreground="#15191f")

    def statisztikak(self):
        self.adatokat_osszegyujt()
        szoveg = "\n".join(j["szoveg"] for j in self.projekt["jelenetek"])
        szavak = len(szoveg.split()); karakterek = len(self.projekt["karakterek"])
        parbeszed = sum(1 for j in self.projekt["jelenetek"] for t in j.get("blokkok", {}).values() if t == "Párbeszéd")
        messagebox.showinfo("Forgatókönyv-statisztikák", f"Jelenetek: {len(self.projekt['jelenetek'])}\nKarakterek: {karakterek}\nSzavak: {szavak}\nBecsült oldalszám: {max(1, round(szavak / 250, 1))}\nPárbeszédblokkok: {parbeszed}")

    def karakterlap(self):
        k = self.karakter_lista.curselection()
        if not k:
            messagebox.showinfo("Karakterlap", "Válassz egy karaktert a listából."); return
        nev = self.projekt["karakterek"][k[0]]; adatok = self.projekt.setdefault("karakter_adatok", {}).setdefault(nev, {})
        ablak = tk.Toplevel(self); ablak.title(f"Karakterlap — {nev}"); ablak.configure(bg=self.szinek["panel"]); ablak.transient(self)
        ttk.Label(ablak, text=nev.upper(), style="AppTitle.TLabel").pack(anchor="w", padx=18, pady=(18, 10))
        mezok = {}
        for kulcs, cim in (("leiras", "Leírás"), ("cel", "Cél"), ("konfliktus", "Konfliktus"), ("hattersztori", "Háttértörténet")):
            ttk.Label(ablak, text=cim).pack(anchor="w", padx=18); mezo = tk.Text(ablak, height=3, width=54, bg=self.szinek["szerkeszto"], fg=self.szinek["szoveg"], insertbackground=self.szinek["kiemeles"], relief="flat")
            mezo.insert("1.0", adatok.get(kulcs, "")); mezo.pack(padx=18, pady=(2, 8)); mezok[kulcs] = mezo
        def mentes():
            self.projekt["karakter_adatok"][nev] = {kulcs: mezo.get("1.0", "end-1c") for kulcs, mezo in mezok.items()}; ablak.destroy(); self.statusz.config(text=f"●  Karakterlap rögzítve: {nev}")
        UvegGomb(ablak, "Karakterlap mentése", mentes, accent=True, width=175).pack(anchor="e", padx=18, pady=(2, 18))

    def jelenetkartya(self):
        if self.aktualis_jelenet is None:
            messagebox.showinfo("Jelenetkártya", "Válassz vagy hozz létre egy jelenetet."); return
        jelenet = self.projekt["jelenetek"][self.aktualis_jelenet]; kartya = jelenet.setdefault("kartya", {})
        ablak = tk.Toplevel(self); ablak.title("Jelenetkártya"); ablak.configure(bg=self.szinek["panel"]); ablak.transient(self)
        ttk.Label(ablak, text="JELENETKÁRTYA", style="AppTitle.TLabel").pack(anchor="w", padx=18, pady=(18, 10))
        mezok = {}
        for kulcs, cim in (("osszefoglalo", "Rövid összefoglaló"), ("helyszin", "Helyszín"), ("ido", "Idő"), ("szereplok", "Szereplők"), ("dramaturgia", "Dramaturgiai szerep")):
            ttk.Label(ablak, text=cim).pack(anchor="w", padx=18); mezo = ttk.Entry(ablak, width=56); mezo.insert(0, kartya.get(kulcs, "")); mezo.pack(padx=18, pady=(2, 8)); mezok[kulcs] = mezo
        def mentes():
            jelenet["kartya"] = {kulcs: mezo.get().strip() for kulcs, mezo in mezok.items()}; ablak.destroy(); self.statusz.config(text="●  Jelenetkártya rögzítve")
        UvegGomb(ablak, "Jelenetkártya mentése", mentes, accent=True, width=190).pack(anchor="e", padx=18, pady=(2, 18))

    def auto_mentes(self):
        try:
            self.adatokat_osszegyujt()
            cel = Path(self.fajl_utvonal).with_suffix(".autosave.json") if self.fajl_utvonal else Path.cwd() / "fvg-storyeditor.autosave.json"
            cel.write_text(json.dumps(self.projekt, ensure_ascii=False, indent=2), encoding="utf-8")
            self.statusz.config(text="●  Automatikus mentés elkészült")
        except OSError:
            self.statusz.config(text="●  Automatikus mentés sikertelen")
        finally:
            self.after(180000, self.auto_mentes)

    def indulasi_ellenorzes(self, reszletes=False):
        hibak = []
        if importlib.util.find_spec("reportlab") is None: hibak.append("PDF-export: ReportLab nincs telepítve")
        try:
            with tempfile.TemporaryFile(mode="w+", encoding="utf-8") as fajl: fajl.write("ok")
        except OSError: hibak.append("Írási jogosultság: ideiglenes fájl nem hozható létre")
        if hibak:
            uzenet = "Komponensek: " + " • ".join(hibak)
            self.statusz.config(text="●  " + uzenet)
            if reszletes: messagebox.showwarning("Komponensellenőrzés", uzenet + "\n\nA PDF-exporthoz futtasd: python3 -m pip install -r requirements.txt")
        else:
            uzenet = "Minden komponens rendben: Tkinter, fájlkezelés, PDF-export"
            self.statusz.config(text="●  " + uzenet)
            if reszletes: messagebox.showinfo("Komponensellenőrzés", uzenet)

    def verzio_elzmenyek(self):
        self.adatokat_osszegyujt()
        ablak = tk.Toplevel(self)
        ablak.title("Verzióelőzmények — FVG Story Editor")
        ablak.geometry("540x390")
        ablak.configure(bg=self.szinek["panel"])
        ablak.transient(self)
        ttk.Label(ablak, text="VERZIÓELŐZMÉNYEK", style="AppTitle.TLabel").pack(anchor="w", padx=18, pady=(18, 2))
        ttk.Label(ablak, text="A mentések pillanatképei. Visszaállítás előtt az aktuális állapot is megmarad.").pack(anchor="w", padx=18, pady=(0, 12))
        lista = tk.Listbox(ablak, activestyle="none", bg=self.szinek["szerkeszto"], fg=self.szinek["szoveg"],
            selectbackground=self.szinek["kiemeles"], selectforeground="#15191f", borderwidth=0, highlightthickness=0, font=("Sans", 10))
        lista.pack(fill="both", expand=True, padx=18, pady=(0, 14))
        verziok = self.projekt.get("verziok", [])
        for i, verzio in enumerate(reversed(verziok), 1):
            adat = verzio["adat"]
            lista.insert("end", f"{i:02d}. {verzio['ido']}  ·  {len(adat['jelenetek'])} jelenet · {adat['cim']}")
        also = ttk.Frame(ablak, padding=(18, 0, 18, 18))
        also.pack(fill="x")
        ttk.Button(also, text="Bezárás", command=ablak.destroy).pack(side="right")
        def visszaallit():
            k = lista.curselection()
            if not k:
                messagebox.showinfo("Verzióelőzmények", "Előbb válassz egy változatot.", parent=ablak)
                return
            if not messagebox.askyesno("Változat visszaállítása", "Visszaállítod a kijelölt változatot?", parent=ablak):
                return
            valasztott = json.loads(json.dumps(verziok[len(verziok) - 1 - k[0]]["adat"]))
            self.verzio_pillanatkep()
            self.projekt["cim"] = valasztott["cim"]
            self.projekt["szerzo"] = valasztott["szerzo"]
            self.projekt["jelenetek"] = json.loads(json.dumps(valasztott["jelenetek"]))
            self.projekt["karakterek"] = json.loads(json.dumps(valasztott["karakterek"]))
            self.projekt["karakter_adatok"] = json.loads(json.dumps(valasztott.get("karakter_adatok", {})))
            self.aktualis_jelenet = None
            self.cim.delete(0, "end"); self.cim.insert(0, self.projekt["cim"])
            self.szerzo.delete(0, "end"); self.szerzo.insert(0, self.projekt["szerzo"])
            self.frissit_listak(); self.jelenet_mezo_tisztit()
            self.statusz.config(text="●  Egy korábbi változat visszaállítva — mentsd el a projektet.")
            ablak.destroy()
        ttk.Button(also, text="Kijelölt változat visszaállítása", command=visszaallit, style="Accent.TButton").pack(side="left")


if __name__ == "__main__":
    try:
        ForgatokonyvIro().mainloop()
    except Exception as hiba:
        # A .desktop indítás nem mutat terminált; a napló segít, ha a hiba
        # a grafikus párbeszédablak előtt következne be.
        Path(__file__).with_name("inditasi_hiba.log").write_text(
            traceback.format_exc(), encoding="utf-8"
        )
        try:
            messagebox.showerror(
                "FVG Story Editor – indítási hiba",
                f"Az alkalmazás nem tudott elindulni.\n\n{hiba}\n\n"
                "A részletek az inditasi_hiba.log fájlban vannak.",
            )
        except tk.TclError:
            pass
