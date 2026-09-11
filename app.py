"""FVG Story Editor – magyar nyelvű asztali forgatókönyvíró."""

import json
import traceback
import importlib.util
import tempfile
import sys
import csv
import difflib
import subprocess
import os
import platform
import threading
import urllib.request
import webbrowser
import xml.etree.ElementTree as ET
from datetime import datetime
from html import escape
from pathlib import Path
import tkinter as tk
from tkinter import filedialog, messagebox, simpledialog, ttk


APP_VERZIO = "0.2.0"
GITHUB_TARHELY = "atombenceprivate/fvg-storyeditor-v1"
GITHUB_KIADAS_API = f"https://api.github.com/repos/{GITHUB_TARHELY}/releases/latest"

SZOVEGEK = {
    "hu": {
        "file": "Fájl", "tools": "Eszközök", "settings": "Beállítások", "new": "Új projekt",
        "open": "Megnyitás…", "save": "Mentés", "save_as": "Mentés másként…", "exit": "Kilépés",
        "scenes": "Jelenetek", "scene_editor": "Jelenet szerkesztése", "characters": "Karakterek",
        "title": "Cím:", "author": "Szerző:", "save_scene": "Jelenet módosításainak rögzítése",
        "language": "Alkalmazás nyelve", "hungarian": "Magyar", "english": "English",
        "beat_sheet": "Beat Sheet…", "shot_list": "Kamera-beállítási lista…",
        "check_update": "Frissítések ellenőrzése…", "update_available": "Új verzió elérhető",
    },
    "en": {
        "file": "File", "tools": "Tools", "settings": "Settings", "new": "New project",
        "open": "Open…", "save": "Save", "save_as": "Save as…", "exit": "Exit",
        "scenes": "Scenes", "scene_editor": "Scene editor", "characters": "Characters",
        "title": "Title:", "author": "Author:", "save_scene": "Save scene changes",
        "language": "Application language", "hungarian": "Magyar", "english": "English",
        "beat_sheet": "Beat sheet…", "shot_list": "Camera shot list…",
        "check_update": "Check for updates…", "update_available": "Update available",
    },
}


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
        self.beallitasok = self.beallitasok_betoltese()
        self.nyelv = self.beallitasok.get("nyelv", "hu")
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
        self.after(600, self.autosave_helyreallitas_felajanlasa)
        self.after(1800, self.frissites_ellenorzese_hatterben)
        if len(sys.argv) > 1 and sys.argv[1]:
            self.after(120, lambda: self.megnyit_utvonal(sys.argv[1]))

    @staticmethod
    def uj_projekt_adat():
        return {"cim": "Új forgatókönyv", "szerzo": "", "jelenetek": [], "karakterek": [], "karakter_adatok": {}, "verziok": [], "dramaturgia": [], "beatsheet": [], "kamera_beallitasok": [], "jegyzetek": "", "napi_cel": 500, "referenciak": []}

    def t(self, kulcs):
        return SZOVEGEK.get(self.nyelv, SZOVEGEK["hu"]).get(kulcs, SZOVEGEK["hu"].get(kulcs, kulcs))

    @staticmethod
    def beallitasok_utvonala():
        alap = Path(os.environ.get("APPDATA", Path.home() / ".config")) / "FVG Story Editor"
        return alap / "settings.json"

    def beallitasok_betoltese(self):
        try:
            return json.loads(self.beallitasok_utvonala().read_text(encoding="utf-8"))
        except (OSError, ValueError, json.JSONDecodeError):
            return {"nyelv": "hu", "automatikus_frissites_ellenorzes": True}

    def beallitasok_mentese(self):
        try:
            cel = self.beallitasok_utvonala(); cel.parent.mkdir(parents=True, exist_ok=True)
            cel.write_text(json.dumps(self.beallitasok, ensure_ascii=False, indent=2), encoding="utf-8")
        except OSError:
            pass

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
        fajl.add_command(label=self.t("new"), command=self.uj_projekt, accelerator="Ctrl+N")
        fajl.add_command(label="Új projekt varázsló…", command=self.projekt_varazslo)
        fajl.add_command(label=self.t("open"), command=self.megnyit, accelerator="Ctrl+O")
        fajl.add_command(label=self.t("save"), command=self.ment, accelerator="Ctrl+S")
        fajl.add_command(label=self.t("save_as"), command=self.ment_maskent)
        fajl.add_separator()
        fajl.add_command(label="Verzióelőzmények…", command=self.verzio_elzmenyek, accelerator="Ctrl+H")
        fajl.add_command(label="Exportálás PDF-be…", command=self.pdf_export)
        fajl.add_command(label="Exportálás Fountainbe…", command=self.fountain_export)
        fajl.add_command(label="Exportcsomag készítése…", command=self.exportcsomag)
        fajl.add_separator()
        fajl.add_command(label="Fountain importálása…", command=self.fountain_import)
        fajl.add_command(label="Final Draft (.fdx) importálása…", command=self.fdx_import)
        fajl.add_separator()
        fajl.add_command(label=self.t("exit"), command=self.destroy)
        menu.add_cascade(label=self.t("file"), menu=fajl)
        eszkozok = tk.Menu(menu, tearoff=False)
        eszkozok.add_command(label="Keresés és csere…", command=self.keres_es_csere, accelerator="Ctrl+F")
        eszkozok.add_command(label="Statisztikák…", command=self.statisztikak)
        eszkozok.add_separator()
        eszkozok.add_command(label="Karakterlap szerkesztése…", command=self.karakterlap)
        eszkozok.add_command(label="Aktuális jelenet kártyája…", command=self.jelenetkartya)
        eszkozok.add_command(label="Jelenetkártya-tábla…", command=self.kartyatabla)
        eszkozok.add_command(label="Dramaturgiai ív…", command=self.dramaturgiai_iv)
        eszkozok.add_command(label="Projekt-navigátor…", command=self.navigator)
        eszkozok.add_command(label="Dialóguselemzés…", command=self.dialogus_elemzes)
        eszkozok.add_command(label="Jelenetjegyzetek…", command=self.jelenet_jegyzetek)
        eszkozok.add_command(label="Produkciós bontás…", command=self.produkcios_bontas)
        eszkozok.add_command(label=self.t("beat_sheet"), command=self.beatsheet)
        eszkozok.add_command(label=self.t("shot_list"), command=self.kamera_beallitas_lista)
        eszkozok.add_command(label="Verziók összehasonlítása…", command=self.verzio_osszehasonlitas)
        eszkozok.add_command(label="Idővonal nézet…", command=self.idovonal)
        eszkozok.add_command(label="Produkciós összesítő…", command=self.produkcios_osszesito)
        eszkozok.add_command(label="Referenciaképek / moodboard…", command=self.moodboard)
        eszkozok.add_command(label="Magyar helyesírás ellenőrzése…", command=self.helyesiras)
        eszkozok.add_separator()
        eszkozok.add_command(label="Írási cél és fókuszmód…", command=self.cel_es_fokusz)
        eszkozok.add_command(label="Aktuális jelenet duplikálása", command=self.jelenet_duplikalasa, accelerator="Ctrl+D")
        eszkozok.add_separator()
        eszkozok.add_command(label="Komponensek ellenőrzése", command=lambda: self.indulasi_ellenorzes(reszletes=True))
        menu.add_cascade(label=self.t("tools"), menu=eszkozok)
        beallitasok = tk.Menu(menu, tearoff=False)
        nyelv = tk.Menu(beallitasok, tearoff=False)
        nyelv.add_command(label=self.t("hungarian"), command=lambda: self.nyelv_valtas("hu"))
        nyelv.add_command(label=self.t("english"), command=lambda: self.nyelv_valtas("en"))
        beallitasok.add_cascade(label=self.t("language"), menu=nyelv)
        beallitasok.add_command(label=self.t("check_update"), command=lambda: self.frissites_ellenorzese_hatterben(kezzel=True))
        menu.add_cascade(label=self.t("settings"), menu=beallitasok)
        self.config(menu=menu)
        self.bind_all("<Control-n>", lambda e: self.uj_projekt())
        self.bind_all("<Control-o>", lambda e: self.megnyit())
        self.bind_all("<Control-s>", lambda e: self.ment())
        self.bind_all("<Control-h>", lambda e: self.verzio_elzmenyek())
        self.bind_all("<Control-f>", lambda e: self.keres_es_csere())
        self.bind_all("<Control-d>", lambda e: self.jelenet_duplikalasa())

        fejlec = ttk.Frame(self, style="Header.TFrame", padding=(22, 18, 22, 14))
        fejlec.pack(fill="x")
        jelveny = ttk.Label(fejlec, text="✦", style="Brand.TLabel")
        jelveny.pack(side="left", padx=(0, 10))
        cimkeret = ttk.Frame(fejlec, style="Header.TFrame")
        cimkeret.pack(side="left")
        ttk.Label(cimkeret, text="FVG STORY EDITOR", style="AppTitle.TLabel").pack(anchor="w")
        ttk.Label(cimkeret, text="A történeted itt kap formát.", style="Tagline.TLabel").pack(anchor="w")
        UvegGomb(fejlec, self.t("save"), self.ment, accent=True, width=112, hatter=self.szinek["hatterszin"]).pack(side="right", pady=4)

        info = ttk.Frame(self, style="Header.TFrame", padding=(22, 2, 22, 16))
        info.pack(fill="x")
        ttk.Label(info, text=self.t("title")).pack(side="left")
        self.cim = ttk.Entry(info, width=38)
        self.cim.pack(side="left", padx=(5, 18))
        ttk.Label(info, text=self.t("author")).pack(side="left")
        self.szerzo = ttk.Entry(info, width=30)
        self.szerzo.pack(side="left", padx=5)

        panel = ttk.PanedWindow(self, orient="horizontal", style="Studio.TPanedwindow")
        panel.pack(fill="both", expand=True, padx=22, pady=(0, 18))

        bal = ttk.Labelframe(panel, text=self.t("scenes"), padding=8)
        # A weight opció nem érhető el minden Ubuntuhoz csomagolt Tk verzióban.
        panel.add(bal)
        self.jelenet_lista = tk.Listbox(bal, exportselection=False, activestyle="none",
            bg=self.szinek["panel"], fg=self.szinek["szoveg"], selectbackground=self.szinek["kiemeles"],
            selectforeground="#15191f", highlightthickness=0, borderwidth=0, font=("Sans", 10))
        self.jelenet_lista.pack(fill="both", expand=True)
        self.jelenet_lista.bind("<<ListboxSelect>>", self.jelenet_kivalaszt)
        self.jelenet_lista.bind("<ButtonPress-1>", self.jelenet_huzas_kezdete)
        self.jelenet_lista.bind("<B1-Motion>", self.jelenet_huzas_mozgatasa)
        self.jelenet_lista.bind("<ButtonRelease-1>", self.jelenet_huzas_vege)
        gombok = ttk.Frame(bal)
        gombok.pack(fill="x", pady=(8, 0))
        UvegGomb(gombok, "+ Jelenet", self.uj_jelenet, accent=True, width=102).pack(side="left")
        UvegGomb(gombok, "Törlés", self.jelenet_torles, width=80).pack(side="right")
        rendezes = ttk.Frame(bal)
        rendezes.pack(fill="x", pady=(8, 0))
        UvegGomb(rendezes, "↑ Feljebb", lambda: self.jelenet_mozgat(-1), width=92).pack(side="left")
        UvegGomb(rendezes, "↓ Lejjebb", lambda: self.jelenet_mozgat(1), width=92).pack(side="right")

        kozep = ttk.Labelframe(panel, text=self.t("scene_editor"), padding=10)
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
        self.szoveg.bind("<KeyRelease>", lambda _e: self.frissit_szamlalo())
        self.szoveg.tag_configure("Akció", justify="left", lmargin1=0, lmargin2=0, spacing1=7)
        self.szoveg.tag_configure("Karakter", justify="center", font=("Sans", 11, "bold"), foreground=self.szinek["kiemeles"], spacing1=12)
        self.szoveg.tag_configure("Párbeszéd", justify="left", lmargin1=70, lmargin2=70, rmargin=70, spacing3=7)
        self.szoveg.tag_configure("Zárójeles utasítás", justify="left", lmargin1=88, lmargin2=88, rmargin=88, foreground=self.szinek["halvany"])
        szerkeszto_also = ttk.Frame(kozep)
        szerkeszto_also.pack(fill="x")
        self.szamlalo = ttk.Label(szerkeszto_also, text="0 szó · 0 karakter", foreground=self.szinek["halvany"])
        self.szamlalo.pack(side="left", pady=2)
        UvegGomb(szerkeszto_also, self.t("save_scene"), self.jelenet_rogzit, accent=True, width=264).pack(side="right")

        jobb = ttk.Labelframe(panel, text=self.t("characters"), padding=8)
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
        self.projekt["jelenetek"].append({"fejlec": "INT. HELYSZÍN – NAPPAL", "szoveg": "", "blokkok": {}, "kartya": {}, "bontas": {}, "megjegyzesek": "", "kepek": []})
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
        self.frissit_szamlalo()

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

    def jelenet_huzas_kezdete(self, esemeny):
        """A jelenetlista fogd-és-ejtsd átrendezésének kezdőpontja."""
        if not self.projekt["jelenetek"]:
            return
        index = self.jelenet_lista.nearest(esemeny.y)
        if not 0 <= index < len(self.projekt["jelenetek"]):
            return
        self.jelenet_rogzit()
        self.huzott_jelenet = index
        self.aktualis_jelenet = None

    def jelenet_huzas_mozgatasa(self, esemeny):
        if not hasattr(self, "huzott_jelenet"):
            return
        cel = self.jelenet_lista.nearest(esemeny.y)
        if cel == self.huzott_jelenet or not 0 <= cel < len(self.projekt["jelenetek"]):
            return
        jelenet = self.projekt["jelenetek"].pop(self.huzott_jelenet)
        self.projekt["jelenetek"].insert(cel, jelenet)
        self.huzott_jelenet = cel
        self.frissit_jelenetek(kijelolt=cel)
        self.jelenet_lista.activate(cel)

    def jelenet_huzas_vege(self, _esemeny):
        if not hasattr(self, "huzott_jelenet"):
            return
        index = self.huzott_jelenet
        del self.huzott_jelenet
        self.aktualis_jelenet = index
        jelenet = self.projekt["jelenetek"][index]
        self.jelenet_fejlec.delete(0, "end"); self.jelenet_fejlec.insert(0, jelenet["fejlec"])
        self.szoveg.delete("1.0", "end"); self.szoveg.insert("1.0", jelenet["szoveg"])
        self.blokkok_rajzol(jelenet.get("blokkok", {})); self.frissit_szamlalo()
        self.statusz.config(text="●  Jelenet átrendezve fogd-és-ejtsd módszerrel")

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

    def jelenet_duplikalasa(self):
        if self.aktualis_jelenet is None:
            messagebox.showinfo("Jelenet duplikálása", "Válassz ki egy jelenetet.")
            return
        self.jelenet_rogzit()
        eredeti = self.projekt["jelenetek"][self.aktualis_jelenet]
        masolat = json.loads(json.dumps(eredeti, ensure_ascii=False))
        masolat["fejlec"] = f"{eredeti['fejlec']} (MÁSOLAT)"
        uj_index = self.aktualis_jelenet + 1
        self.projekt["jelenetek"].insert(uj_index, masolat)
        self.aktualis_jelenet = None
        self.frissit_jelenetek(kijelolt=uj_index)
        self.jelenet_kivalaszt()
        self.statusz.config(text="●  Jelenet duplikálva")

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
    def jelenet_mezo_tisztit(self): self.jelenet_fejlec.delete(0, "end"); self.szoveg.delete("1.0", "end"); self.frissit_szamlalo()
    def frissit_szamlalo(self):
        szoveg = self.szoveg.get("1.0", "end-1c")
        self.szamlalo.config(text=f"{len(szoveg.split())} szó · {len(szoveg)} karakter")
    def adatokat_osszegyujt(self):
        self.jelenet_rogzit(); self.projekt["cim"] = self.cim.get().strip() or "Új forgatókönyv"; self.projekt["szerzo"] = self.szerzo.get().strip()

    def verzio_pillanatkep(self):
        """Elmenti a projekt aktuális állapotát egy visszaállítható változatként."""
        adat = {
            "cim": self.projekt["cim"], "szerzo": self.projekt["szerzo"],
            "jelenetek": self.projekt["jelenetek"], "karakterek": self.projekt["karakterek"], "karakter_adatok": self.projekt.get("karakter_adatok", {}), "dramaturgia": self.projekt.get("dramaturgia", []), "beatsheet": self.projekt.get("beatsheet", []), "kamera_beallitasok": self.projekt.get("kamera_beallitasok", []), "jegyzetek": self.projekt.get("jegyzetek", ""), "napi_cel": self.projekt.get("napi_cel", 500),
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
            adat.setdefault("dramaturgia", [])
            adat.setdefault("beatsheet", [])
            adat.setdefault("kamera_beallitasok", [])
            adat.setdefault("jegyzetek", "")
            adat.setdefault("napi_cel", 500)
            adat.setdefault("referenciak", [])
            for jelenet in adat["jelenetek"]:
                jelenet.setdefault("blokkok", {})
                jelenet.setdefault("kartya", {})
                jelenet.setdefault("bontas", {})
                jelenet.setdefault("megjegyzesek", "")
                jelenet.setdefault("kepek", [])
            self.projekt, self.fajl_utvonal, self.aktualis_jelenet = adat, utvonal, None
            self.cim.delete(0, "end"); self.cim.insert(0, adat["cim"])
            self.szerzo.delete(0, "end"); self.szerzo.insert(0, adat["szerzo"])
            self.frissit_listak(); self.jelenet_mezo_tisztit(); self.statusz.config(text=f"Megnyitva: {utvonal}")
            autosave = Path(utvonal).with_suffix(".autosave.json")
            if autosave.exists() and autosave.stat().st_mtime > Path(utvonal).stat().st_mtime:
                if messagebox.askyesno("Újabb automatikus mentés", "Találtam a projektfájlnál újabb automatikus mentést. Visszaállítod?"):
                    auto_adat = json.loads(autosave.read_text(encoding="utf-8"))
                    self.projekt = auto_adat
                    for j in self.projekt["jelenetek"]: j.setdefault("blokkok", {}); j.setdefault("kartya", {}); j.setdefault("bontas", {}); j.setdefault("megjegyzesek", ""); j.setdefault("kepek", [])
                    self.projekt.setdefault("referenciak", [])
                    self.projekt.setdefault("beatsheet", [])
                    self.projekt.setdefault("kamera_beallitasok", [])
                    self.cim.delete(0, "end"); self.cim.insert(0, self.projekt["cim"])
                    self.szerzo.delete(0, "end"); self.szerzo.insert(0, self.projekt.get("szerzo", ""))
                    self.frissit_listak(); self.jelenet_mezo_tisztit(); self.statusz.config(text="●  Projekt-specifikus automatikus mentés visszaállítva")
        except (OSError, ValueError, json.JSONDecodeError) as hiba: messagebox.showerror("Megnyitási hiba", str(hiba))

    def beatsheet(self):
        """A történet beatjeinek (történetfordulóinak) szerkeszthető listája."""
        self.adatokat_osszegyujt()
        alapok = ["Nyitókép", "Téma felvetése", "Kiváltó esemény", "Első fordulópont", "Középpont", "Mélypont", "Finálé", "Zárókép"]
        beatek = self.projekt.setdefault("beatsheet", [])
        if not beatek:
            beatek.extend({"nev": nev, "leiras": "", "jelenet": ""} for nev in alapok)
        ablak = tk.Toplevel(self); ablak.title("Beat Sheet — FVG Story Editor"); ablak.geometry("820x520"); ablak.configure(bg=self.szinek["panel"]); ablak.transient(self)
        ttk.Label(ablak, text="BEAT SHEET", style="AppTitle.TLabel").pack(anchor="w", padx=18, pady=(18, 3))
        ttk.Label(ablak, text="A történet fontos fordulópontjai. A sorrend fogd-és-ejtsd helyett a nyilakkal is módosítható.").pack(anchor="w", padx=18, pady=(0, 10))
        tabla = ttk.Treeview(ablak, columns=("nev", "jelenet", "leiras"), show="headings", selectmode="browse")
        for azonosito, cim, szelesseg in (("nev", "Beat", 180), ("jelenet", "Kapcsolt jelenet", 230), ("leiras", "Jegyzet", 350)):
            tabla.heading(azonosito, text=cim); tabla.column(azonosito, width=szelesseg, anchor="w")
        tabla.pack(fill="both", expand=True, padx=18, pady=(0, 10))
        def frissit(kijelolt=None):
            tabla.delete(*tabla.get_children())
            for i, beat in enumerate(beatek): tabla.insert("", "end", iid=str(i), values=(beat.get("nev", ""), beat.get("jelenet", ""), beat.get("leiras", "")))
            if kijelolt is not None and 0 <= kijelolt < len(beatek): tabla.selection_set(str(kijelolt))
        def szerkeszt(index=None):
            adat = beatek[index] if index is not None else {"nev": "Új beat", "jelenet": "", "leiras": ""}
            szerk = tk.Toplevel(ablak); szerk.title("Beat szerkesztése"); szerk.configure(bg=self.szinek["panel"]); szerk.transient(ablak)
            ttk.Label(szerk, text="Beat neve:").pack(anchor="w", padx=16, pady=(16, 3)); nev = ttk.Entry(szerk, width=55); nev.insert(0, adat.get("nev", "")); nev.pack(padx=16)
            ttk.Label(szerk, text="Kapcsolt jelenet:").pack(anchor="w", padx=16, pady=(10, 3)); jelenet = ttk.Combobox(szerk, values=[j["fejlec"] for j in self.projekt["jelenetek"]], width=52); jelenet.set(adat.get("jelenet", "")); jelenet.pack(padx=16)
            ttk.Label(szerk, text="Jegyzet:").pack(anchor="w", padx=16, pady=(10, 3)); leiras = tk.Text(szerk, width=55, height=5, bg=self.szinek["szerkeszto"], fg=self.szinek["szoveg"], insertbackground=self.szinek["kiemeles"], relief="flat"); leiras.insert("1.0", adat.get("leiras", "")); leiras.pack(padx=16)
            def mentes():
                uj = {"nev": nev.get().strip() or "Névtelen beat", "jelenet": jelenet.get().strip(), "leiras": leiras.get("1.0", "end-1c").strip()}
                if index is None: beatek.append(uj); cel = len(beatek) - 1
                else: beatek[index] = uj; cel = index
                frissit(cel); szerk.destroy(); self.statusz.config(text="●  Beat Sheet mentve")
            UvegGomb(szerk, "Mentés", mentes, accent=True, width=100).pack(anchor="e", padx=16, pady=16)
        def kivalasztott():
            k = tabla.selection(); return int(k[0]) if k else None
        def torol():
            i = kivalasztott()
            if i is not None and messagebox.askyesno("Beat törlése", "Törlöd a kijelölt beatet?", parent=ablak): beatek.pop(i); frissit()
        def mozgat(irany):
            i = kivalasztott(); uj = None if i is None else i + irany
            if uj is not None and 0 <= uj < len(beatek): beatek[i], beatek[uj] = beatek[uj], beatek[i]; frissit(uj)
        also = ttk.Frame(ablak, padding=(18, 0, 18, 18)); also.pack(fill="x")
        UvegGomb(also, "+ Beat", lambda: szerkeszt(), accent=True, width=90).pack(side="left")
        UvegGomb(also, "Szerkesztés", lambda: (szerkeszt(kivalasztott()) if kivalasztott() is not None else None), width=110).pack(side="left", padx=7)
        UvegGomb(also, "↑", lambda: mozgat(-1), width=45).pack(side="left"); UvegGomb(also, "↓", lambda: mozgat(1), width=45).pack(side="left", padx=4)
        UvegGomb(also, "Törlés", torol, width=80).pack(side="right")
        frissit()

    def kamera_beallitas_lista(self):
        """Produkciós kamera shot lista jelenethez kötött beállításokkal."""
        self.adatokat_osszegyujt(); lista = self.projekt.setdefault("kamera_beallitasok", [])
        ablak = tk.Toplevel(self); ablak.title("Kamera-beállítási lista — FVG Story Editor"); ablak.geometry("900x520"); ablak.configure(bg=self.szinek["panel"]); ablak.transient(self)
        ttk.Label(ablak, text="KAMERA-BEÁLLÍTÁSI LISTA", style="AppTitle.TLabel").pack(anchor="w", padx=18, pady=(18, 3))
        ttk.Label(ablak, text="Tervezd meg jelenetenként a képkivágást, kameramozgást és technikai megjegyzéseket.").pack(anchor="w", padx=18, pady=(0, 10))
        tabla = ttk.Treeview(ablak, columns=("jelenet", "tipus", "mozgas", "leiras"), show="headings", selectmode="browse")
        for azonosito, cim, szelesseg in (("jelenet", "Jelenet", 230), ("tipus", "Beállítás", 130), ("mozgas", "Mozgás", 130), ("leiras", "Leírás / megjegyzés", 350)):
            tabla.heading(azonosito, text=cim); tabla.column(azonosito, width=szelesseg, anchor="w")
        tabla.pack(fill="both", expand=True, padx=18, pady=(0, 10))
        def frissit(kijelolt=None):
            tabla.delete(*tabla.get_children())
            for i, shot in enumerate(lista): tabla.insert("", "end", iid=str(i), values=(shot.get("jelenet", ""), shot.get("tipus", ""), shot.get("mozgas", ""), shot.get("leiras", "")))
            if kijelolt is not None and 0 <= kijelolt < len(lista): tabla.selection_set(str(kijelolt))
        def szerkeszt(index=None):
            adat = lista[index] if index is not None else {}
            szerk = tk.Toplevel(ablak); szerk.title("Kamera-beállítás"); szerk.configure(bg=self.szinek["panel"]); szerk.transient(ablak)
            mezok = {}
            definiciok = (("jelenet", "Jelenet", [j["fejlec"] for j in self.projekt["jelenetek"]]), ("tipus", "Beállítás", ["Nagytotál", "Totál", "Kistotál", "Féltotál", "Közelkép", "Nagyközel", "Részlet"]), ("mozgas", "Kameramozgás", ["Statikus", "Svenk", "Kocsizás", "Daru", "Kézikamera", "Steadicam", "Zoom"]))
            for kulcs, cim, ertekek in definiciok:
                ttk.Label(szerk, text=cim + ":").pack(anchor="w", padx=16, pady=(12 if mezok else 16, 3)); mezo = ttk.Combobox(szerk, values=ertekek, width=52); mezo.set(adat.get(kulcs, "")); mezo.pack(padx=16); mezok[kulcs] = mezo
            ttk.Label(szerk, text="Leírás / technikai megjegyzés:").pack(anchor="w", padx=16, pady=(12, 3)); leiras = tk.Text(szerk, width=55, height=5, bg=self.szinek["szerkeszto"], fg=self.szinek["szoveg"], insertbackground=self.szinek["kiemeles"], relief="flat"); leiras.insert("1.0", adat.get("leiras", "")); leiras.pack(padx=16)
            def mentes():
                uj = {kulcs: mezo.get().strip() for kulcs, mezo in mezok.items()}; uj["leiras"] = leiras.get("1.0", "end-1c").strip()
                if index is None: lista.append(uj); cel = len(lista) - 1
                else: lista[index] = uj; cel = index
                frissit(cel); szerk.destroy(); self.statusz.config(text="●  Kamera-beállítás mentve")
            UvegGomb(szerk, "Mentés", mentes, accent=True, width=100).pack(anchor="e", padx=16, pady=16)
        def kivalasztott():
            k = tabla.selection(); return int(k[0]) if k else None
        def torol():
            i = kivalasztott()
            if i is not None and messagebox.askyesno("Beállítás törlése", "Törlöd a kijelölt kamera-beállítást?", parent=ablak): lista.pop(i); frissit()
        also = ttk.Frame(ablak, padding=(18, 0, 18, 18)); also.pack(fill="x")
        UvegGomb(also, "+ Beállítás", lambda: szerkeszt(), accent=True, width=115).pack(side="left")
        UvegGomb(also, "Szerkesztés", lambda: (szerkeszt(kivalasztott()) if kivalasztott() is not None else None), width=110).pack(side="left", padx=7)
        UvegGomb(also, "Törlés", torol, width=80).pack(side="right")
        frissit()

    def nyelv_valtas(self, nyelv):
        if nyelv == self.nyelv: return
        self.beallitasok["nyelv"] = nyelv; self.beallitasok_mentese()
        if messagebox.askyesno("Language / Nyelv", "A nyelvváltás az alkalmazás újraindításával lép életbe. Újraindítod most?"):
            self.destroy(); os.execv(sys.executable, [sys.executable, *sys.argv])

    @staticmethod
    def verzio_kulcs(verzio):
        return tuple(int(resz) for resz in verzio.lstrip("vV").split("-")[0].split(".") if resz.isdigit())

    def frissites_ellenorzese_hatterben(self, kezzel=False):
        if not kezzel and not self.beallitasok.get("automatikus_frissites_ellenorzes", True): return
        def ellenoriz():
            try:
                keres = urllib.request.Request(GITHUB_KIADAS_API, headers={"Accept": "application/vnd.github+json", "User-Agent": "FVG-Story-Editor"})
                with urllib.request.urlopen(keres, timeout=8) as valasz: kiadas = json.loads(valasz.read().decode("utf-8"))
                uj = kiadas.get("tag_name", "")
                self.after(0, lambda: self.frissitesi_eredmeny(uj, kiadas.get("html_url", ""), kezzel))
            except (OSError, ValueError, json.JSONDecodeError):
                if kezzel: self.after(0, lambda: messagebox.showwarning("Frissítés", "A GitHub kiadásait most nem sikerült elérni."))
        threading.Thread(target=ellenoriz, daemon=True).start()

    def frissitesi_eredmeny(self, uj_verzio, kiadas_url, kezzel):
        if self.verzio_kulcs(uj_verzio) > self.verzio_kulcs(APP_VERZIO):
            uzenet = f"{self.t('update_available')}: {uj_verzio}\nJelenlegi verzió: {APP_VERZIO}\n\nMegnyitom a GitHub Release oldalát a rendszeredhez való telepítő letöltéséhez?"
            if messagebox.askyesno(self.t("update_available"), uzenet): webbrowser.open(kiadas_url)
        elif kezzel:
            messagebox.showinfo("Frissítés", f"Az alkalmazás naprakész. Jelenlegi verzió: {APP_VERZIO}")

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

    def fountain_export(self):
        """Egyszerű Fountain-szöveg export, kompatibilis számos forgatókönyvíróval."""
        self.adatokat_osszegyujt()
        utvonal = filedialog.asksaveasfilename(defaultextension=".fountain", initialfile=f"{self.projekt['cim']}.fountain", filetypes=[("Fountain forgatókönyv", "*.fountain"), ("Szövegfájl", "*.txt")])
        if not utvonal:
            return
        try:
            Path(utvonal).write_text(self.fountain_tartalom(), encoding="utf-8")
            self.statusz.config(text=f"●  Fountain export elkészült: {Path(utvonal).name}")
            messagebox.showinfo("Fountain export", f"Elkészült:\n{utvonal}")
        except OSError as hiba:
            messagebox.showerror("Fountain export", str(hiba))

    def fountain_tartalom(self):
        sorok = [f"Title: {self.projekt['cim']}", f"Author: {self.projekt['szerzo']}", ""]
        for jelenet in self.projekt["jelenetek"]:
            sorok.extend([jelenet["fejlec"], ""])
            blokkok = jelenet.get("blokkok", {})
            for sorszam, sor in enumerate(jelenet["szoveg"].splitlines(), 1):
                tipus = blokkok.get(str(sorszam), "Akció")
                if tipus == "Karakter": sor = sor.upper()
                elif tipus == "Zárójeles utasítás" and sor and not sor.startswith("("): sor = f"({sor})"
                sorok.append(sor)
            sorok.append("")
        return "\n".join(sorok)

    @staticmethod
    def fountain_jelenetek(tartalom):
        jelenetek, aktualis, elozo_karakter = [], None, None
        for sor in tartalom.splitlines():
            csupasz = sor.strip()
            if not csupasz or csupasz.startswith(("Title:", "Author:")): continue
            if csupasz.startswith(("INT.", "EXT.", "INT/EXT.", "I/E.")):
                aktualis = {"fejlec": csupasz, "szoveg": "", "blokkok": {}, "kartya": {}, "bontas": {}, "megjegyzesek": "", "kepek": []}; jelenetek.append(aktualis); elozo_karakter = None; continue
            if aktualis is None: continue
            sorszam = len(aktualis["szoveg"].splitlines()) + 1
            if csupasz.isupper() and len(csupasz) < 45:
                aktualis["blokkok"][str(sorszam)] = "Karakter"; elozo_karakter = csupasz
            elif csupasz.startswith("(") and csupasz.endswith(")"):
                aktualis["blokkok"][str(sorszam)] = "Zárójeles utasítás"
            elif elozo_karakter:
                aktualis["blokkok"][str(sorszam)] = "Párbeszéd"; elozo_karakter = None
            aktualis["szoveg"] += ("\n" if aktualis["szoveg"] else "") + sor
        return jelenetek

    def fountain_import(self):
        utvonal = filedialog.askopenfilename(filetypes=[("Fountain forgatókönyv", "*.fountain"), ("Szövegfájl", "*.txt")])
        if not utvonal: return
        try:
            tartalom = Path(utvonal).read_text(encoding="utf-8"); jelenetek = self.fountain_jelenetek(tartalom)
            if not jelenetek: raise ValueError("Nem találtam jelenetfejléceket a fájlban.")
            self.projekt["jelenetek"] = jelenetek; self.aktualis_jelenet = None; self.frissit_listak(); self.jelenet_mezo_tisztit(); self.statusz.config(text=f"●  {len(jelenetek)} jelenet importálva Fountainből")
        except (OSError, UnicodeDecodeError, ValueError) as hiba: messagebox.showerror("Fountain import", str(hiba))

    def fdx_import(self):
        utvonal = filedialog.askopenfilename(filetypes=[("Final Draft", "*.fdx")])
        if not utvonal: return
        try:
            gyoker = ET.parse(utvonal).getroot(); jelenetek, aktualis = [], None
            tipusok = {"Character": "Karakter", "Dialogue": "Párbeszéd", "Parenthetical": "Zárójeles utasítás", "Action": "Akció"}
            for bekezdes in gyoker.findall(".//Paragraph"):
                tipus = bekezdes.attrib.get("Type", "Action"); szoveg = "".join(bekezdes.itertext()).strip()
                if not szoveg: continue
                if tipus == "Scene Heading":
                    aktualis = {"fejlec": szoveg, "szoveg": "", "blokkok": {}, "kartya": {}, "bontas": {}, "megjegyzesek": "", "kepek": []}; jelenetek.append(aktualis); continue
                if aktualis is None: continue
                sor = len(aktualis["szoveg"].splitlines()) + 1; aktualis["szoveg"] += ("\n" if aktualis["szoveg"] else "") + szoveg; aktualis["blokkok"][str(sor)] = tipusok.get(tipus, "Akció")
            if not jelenetek: raise ValueError("Nem találtam importálható Final Draft jeleneteket.")
            self.projekt["jelenetek"] = jelenetek; self.aktualis_jelenet = None; self.frissit_listak(); self.jelenet_mezo_tisztit(); self.statusz.config(text=f"●  {len(jelenetek)} jelenet importálva FDX-ből")
        except (OSError, ET.ParseError, ValueError) as hiba: messagebox.showerror("Final Draft import", str(hiba))

    def idovonal(self):
        ablak = tk.Toplevel(self); ablak.title("Idővonal — FVG Story Editor"); ablak.geometry("960x390"); ablak.configure(bg=self.szinek["hatterszin"]); ablak.transient(self)
        ttk.Label(ablak, text="TÖRTÉNETI IDŐVONAL", style="AppTitle.TLabel").pack(anchor="w", padx=18, pady=(18, 8))
        vaszon = tk.Canvas(ablak, bg=self.szinek["hatterszin"], highlightthickness=0); vaszon.pack(fill="both", expand=True, padx=18, pady=(0, 18))
        szelesseg = max(760, len(self.projekt["jelenetek"]) * 145); vaszon.configure(scrollregion=(0, 0, szelesseg, 280)); gorgeto = ttk.Scrollbar(ablak, orient="horizontal", command=vaszon.xview); vaszon.configure(xscrollcommand=gorgeto.set); gorgeto.pack(fill="x", padx=18, pady=(0, 12))
        vaszon.create_line(55, 150, szelesseg - 30, 150, fill=self.szinek["vonal"], width=3)
        for i, jelenet in enumerate(self.projekt["jelenetek"]):
            x = 75 + i * 145; kartya = jelenet.get("kartya", {}); szin = self.szinek["kiemeles"] if kartya.get("dramaturgia") else "#52617a"
            vaszon.create_oval(x - 7, 143, x + 7, 157, fill=szin, outline="")
            cim = f"{i + 1}. {kartya.get('dramaturgia') or jelenet['fejlec']}"; cim_id = vaszon.create_text(x, 112 if i % 2 == 0 else 195, text=cim, width=126, fill=self.szinek["szoveg"], font=("Sans", 9, "bold" if kartya.get("dramaturgia") else "normal"))
            vaszon.tag_bind(cim_id, "<Button-1>", lambda _e, index=i: self.idovonal_jelenet_megnyit(ablak, index))

    def idovonal_jelenet_megnyit(self, ablak, index):
        self.jelenet_rogzit(); self.aktualis_jelenet = None; self.frissit_jelenetek(kijelolt=index); self.jelenet_kivalaszt(); ablak.destroy()

    def produkcios_osszesito(self):
        osszes = {"szereplok": set(), "kellekek": set(), "jelmezek": set(), "helyszin": set()}
        for jelenet in self.projekt["jelenetek"]:
            bontas = jelenet.get("bontas", {})
            for kulcs in osszes:
                osszes[kulcs].update(x.strip() for x in bontas.get(kulcs, "").split(",") if x.strip())
        sorok = [f"{cim}: {', '.join(sorted(osszes[kulcs])) or '—'}" for kulcs, cim in (("helyszin", "Helyszínek"), ("szereplok", "Szereplők"), ("kellekek", "Kellékek"), ("jelmezek", "Jelmezek"))]
        messagebox.showinfo("Produkciós összesítő", "\n\n".join(sorok))

    def moodboard(self):
        ablak = tk.Toplevel(self); ablak.title("Referenciaképek / moodboard"); ablak.geometry("620x410"); ablak.configure(bg=self.szinek["panel"]); ablak.transient(self)
        ttk.Label(ablak, text="REFERENCIÁK ÉS MOODBOARD", style="AppTitle.TLabel").pack(anchor="w", padx=18, pady=(18, 8))
        lista = tk.Listbox(ablak, bg=self.szinek["szerkeszto"], fg=self.szinek["szoveg"], selectbackground=self.szinek["kiemeles"], selectforeground="#15191f", borderwidth=0, highlightthickness=0); lista.pack(fill="both", expand=True, padx=18, pady=(0, 10))
        def frissit():
            lista.delete(0, "end")
            for ut in self.projekt.setdefault("referenciak", []): lista.insert("end", Path(ut).name)
        def hozzaad():
            utak = filedialog.askopenfilenames(title="Referenciaképek", filetypes=[("Képfájlok", "*.png *.jpg *.jpeg *.webp *.gif"), ("Minden fájl", "*.*")]); self.projekt["referenciak"].extend(ut for ut in utak if ut not in self.projekt["referenciak"]); frissit()
        def torol():
            k = lista.curselection()
            if k: del self.projekt["referenciak"][k[0]]; frissit()
        g = ttk.Frame(ablak, padding=(18, 0, 18, 18)); g.pack(fill="x"); UvegGomb(g, "+ Képek", hozzaad, accent=True, width=90).pack(side="left"); UvegGomb(g, "Törlés", torol, width=80).pack(side="right"); frissit()

    def helyesiras(self):
        self.adatokat_osszegyujt(); szoveg = "\n".join(j["szoveg"] for j in self.projekt["jelenetek"])
        try:
            futas = subprocess.run(["hunspell", "-d", "hu_HU", "-l"], input=szoveg, text=True, capture_output=True, check=False, timeout=15)
        except (FileNotFoundError, subprocess.TimeoutExpired):
            messagebox.showwarning("Helyesírás", "A magyar helyesírás-ellenőrzéshez telepítsd a Hunspellt és a magyar szótárat.\n\nUbuntu: sudo apt install hunspell hunspell-hu")
            return
        hibak = sorted(set(x for x in futas.stdout.splitlines() if x.strip()))
        messagebox.showinfo("Magyar helyesírás", "Nem találtam ismeretlen szót." if not hibak else "Lehetséges ismeretlen szavak:\n\n" + "\n".join(hibak[:200]))

    def projekt_varazslo(self):
        ablak = tk.Toplevel(self); ablak.title("Új projekt varázsló"); ablak.configure(bg=self.szinek["panel"]); ablak.transient(self)
        ttk.Label(ablak, text="ÚJ PROJEKT", style="AppTitle.TLabel").pack(anchor="w", padx=20, pady=(20, 4))
        ttk.Label(ablak, text="Válassz kiinduló sablont, majd nevezd el a történetet.").pack(anchor="w", padx=20, pady=(0, 14))
        ttk.Label(ablak, text="Projektcím").pack(anchor="w", padx=20); cim = ttk.Entry(ablak, width=45); cim.pack(padx=20, pady=(2, 10)); cim.focus_set()
        ttk.Label(ablak, text="Szerző").pack(anchor="w", padx=20); szerzo = ttk.Entry(ablak, width=45); szerzo.pack(padx=20, pady=(2, 10))
        ttk.Label(ablak, text="Sablon").pack(anchor="w", padx=20); sablon = tk.StringVar(value="Játékfilm"); ttk.Combobox(ablak, textvariable=sablon, state="readonly", values=("Játékfilm", "Rövidfilm", "Sorozatepizód", "Üres projekt"), width=42).pack(padx=20, pady=(2, 16))
        def letrehoz():
            if self.projekt["jelenetek"] and not messagebox.askyesno("Új projekt", "A jelenlegi projekt nem mentett részei elveszhetnek. Folytatod?", parent=ablak): return
            self.projekt = self.uj_projekt_adat(); self.projekt["cim"] = cim.get().strip() or "Új forgatókönyv"; self.projekt["szerzo"] = szerzo.get().strip(); self.fajl_utvonal = None; self.aktualis_jelenet = None
            if sablon.get() != "Üres projekt":
                kezd = "INT. HELYSZÍN – NAPPAL" if sablon.get() != "Sorozatepizód" else "TEASER"
                self.projekt["jelenetek"].append({"fejlec": kezd, "szoveg": "", "blokkok": {}, "kartya": {}, "bontas": {}, "megjegyzesek": "", "kepek": []})
            self.cim.delete(0, "end"); self.cim.insert(0, self.projekt["cim"]); self.szerzo.delete(0, "end"); self.szerzo.insert(0, self.projekt["szerzo"]); self.frissit_listak(); self.jelenet_mezo_tisztit(); ablak.destroy(); self.statusz.config(text=f"●  Új projekt: {sablon.get()} sablon")
        UvegGomb(ablak, "Projekt létrehozása", letrehoz, accent=True, width=170).pack(anchor="e", padx=20, pady=(0, 20))

    def navigator(self):
        ablak = tk.Toplevel(self); ablak.title("Projekt-navigátor"); ablak.geometry("530x500"); ablak.configure(bg=self.szinek["panel"]); ablak.transient(self)
        fa = ttk.Treeview(ablak, show="tree", selectmode="browse"); fa.pack(fill="both", expand=True, padx=16, pady=16)
        jelenetek = fa.insert("", "end", text="Jelenetek", open=True)
        for i, jelenet in enumerate(self.projekt["jelenetek"]): fa.insert(jelenetek, "end", iid=f"j:{i}", text=f"{i + 1:02d}. {jelenet['fejlec']}")
        karakterek = fa.insert("", "end", text="Karakterek", open=True)
        for nev in self.projekt["karakterek"]: fa.insert(karakterek, "end", text=nev)
        dramaturgia = fa.insert("", "end", text="Dramaturgiai ív", open=True)
        for pont in self.projekt.get("dramaturgia", []): fa.insert(dramaturgia, "end", text=f"{pont['nev']}: {pont.get('jelenet') or '—'}")
        def ugrik(_e):
            azonosito = fa.selection()
            if azonosito and azonosito[0].startswith("j:"):
                index = int(azonosito[0][2:]); self.jelenet_rogzit(); self.aktualis_jelenet = None; self.frissit_jelenetek(kijelolt=index); self.jelenet_kivalaszt(); ablak.destroy()
        fa.bind("<Double-1>", ugrik)

    def dialogus_elemzes(self):
        self.adatokat_osszegyujt(); adatok = {}
        for jelenet in self.projekt["jelenetek"]:
            aktualis = "NÉVTELEN"
            for sorszam, sor in enumerate(jelenet["szoveg"].splitlines(), 1):
                tipus = jelenet.get("blokkok", {}).get(str(sorszam), "Akció")
                if tipus == "Karakter": aktualis = sor.strip().upper() or "NÉVTELEN"
                elif tipus == "Párbeszéd":
                    adatok[aktualis] = adatok.get(aktualis, 0) + len(sor.split())
        rendezett = sorted(adatok.items(), key=lambda x: x[1], reverse=True)
        szoveg = "\n".join(f"{nev}: {szavak} szó" for nev, szavak in rendezett) or "Még nincs formázott párbeszédblokk."
        messagebox.showinfo("Dialóguselemzés", f"KARAKTERENKÉNTI DIALÓGUS\n\n{szoveg}")

    def jelenet_jegyzetek(self):
        if self.aktualis_jelenet is None: messagebox.showinfo("Jelenetjegyzetek", "Válassz ki egy jelenetet."); return
        jelenet = self.projekt["jelenetek"][self.aktualis_jelenet]; ablak = tk.Toplevel(self); ablak.title("Jelenetjegyzetek"); ablak.configure(bg=self.szinek["panel"]); ablak.transient(self)
        ttk.Label(ablak, text="JELENETJEGYZETEK", style="AppTitle.TLabel").pack(anchor="w", padx=18, pady=(18, 8))
        mezo = tk.Text(ablak, width=62, height=17, bg=self.szinek["szerkeszto"], fg=self.szinek["szoveg"], insertbackground=self.szinek["kiemeles"], relief="flat"); mezo.insert("1.0", jelenet.get("megjegyzesek", "")); mezo.pack(padx=18, pady=(0, 12))
        def mentes(): jelenet["megjegyzesek"] = mezo.get("1.0", "end-1c"); ablak.destroy(); self.statusz.config(text="●  Jelenetjegyzetek mentve")
        UvegGomb(ablak, "Jegyzetek mentése", mentes, accent=True, width=150).pack(anchor="e", padx=18, pady=(0, 18))

    def produkcios_bontas(self):
        if self.aktualis_jelenet is None: messagebox.showinfo("Produkciós bontás", "Válassz ki egy jelenetet."); return
        jelenet = self.projekt["jelenetek"][self.aktualis_jelenet]; bontas = jelenet.setdefault("bontas", {})
        ablak = tk.Toplevel(self); ablak.title("Produkciós bontás"); ablak.configure(bg=self.szinek["panel"]); ablak.transient(self)
        ttk.Label(ablak, text="PRODUKCIÓS BONTÁS", style="AppTitle.TLabel").pack(anchor="w", padx=18, pady=(18, 4))
        ttk.Label(ablak, text="Vesszővel elválasztott lista is megadható.").pack(anchor="w", padx=18, pady=(0, 10))
        mezok = {}
        for kulcs, cim in (("helyszin", "Helyszín"), ("szereplok", "Szereplők"), ("kellekek", "Kellékek"), ("jelmezek", "Jelmezek"), ("hang", "Hang / zene"), ("megjegyzes", "Produkciós megjegyzés")):
            ttk.Label(ablak, text=cim).pack(anchor="w", padx=18); mezo = ttk.Entry(ablak, width=60); mezo.insert(0, bontas.get(kulcs, "")); mezo.pack(padx=18, pady=(2, 7)); mezok[kulcs] = mezo
        def mentes(): jelenet["bontas"] = {k: m.get().strip() for k, m in mezok.items()}; ablak.destroy(); self.statusz.config(text="●  Produkciós bontás mentve")
        UvegGomb(ablak, "Bontás mentése", mentes, accent=True, width=140).pack(anchor="e", padx=18, pady=(3, 18))

    def verzio_osszehasonlitas(self):
        self.adatokat_osszegyujt(); verziok = self.projekt.get("verziok", [])
        if not verziok: messagebox.showinfo("Verziók összehasonlítása", "Mentsd el a projektet legalább egyszer."); return
        ablak = tk.Toplevel(self); ablak.title("Verziók összehasonlítása"); ablak.geometry("820x570"); ablak.configure(bg=self.szinek["panel"]); ablak.transient(self)
        ttk.Label(ablak, text="VERZIÓ-ÖSSZEHASONLÍTÁS", style="AppTitle.TLabel").pack(anchor="w", padx=18, pady=(18, 8))
        valasztas = tk.StringVar(); cimkek = [f"{v['ido']} · {v['adat']['cim']}" for v in reversed(verziok)]
        ttk.Combobox(ablak, textvariable=valasztas, values=cimkek, state="readonly", width=76).pack(padx=18, fill="x")
        nezet = tk.Text(ablak, wrap="none", bg=self.szinek["szerkeszto"], fg=self.szinek["szoveg"], insertbackground=self.szinek["kiemeles"], relief="flat", font=("Courier", 10)); nezet.pack(fill="both", expand=True, padx=18, pady=12)
        def osszevet():
            if not valasztas.get(): return
            index = cimkek.index(valasztas.get()); regi = verziok[len(verziok) - 1 - index]["adat"]
            most = {"cim": self.projekt["cim"], "szerzo": self.projekt["szerzo"], "jelenetek": self.projekt["jelenetek"], "karakterek": self.projekt["karakterek"], "karakter_adatok": self.projekt.get("karakter_adatok", {}), "dramaturgia": self.projekt.get("dramaturgia", [])}
            diff = difflib.unified_diff(json.dumps(regi, ensure_ascii=False, indent=2).splitlines(), json.dumps(most, ensure_ascii=False, indent=2).splitlines(), fromfile="kiválasztott változat", tofile="jelenlegi állapot", lineterm="")
            nezet.delete("1.0", "end"); nezet.insert("1.0", "\n".join(diff) or "Nincs különbség.")
        UvegGomb(ablak, "Összehasonlítás", osszevet, accent=True, width=145).pack(anchor="e", padx=18, pady=(0, 18))

    def cel_es_fokusz(self):
        ablak = tk.Toplevel(self); ablak.title("Írási cél és fókuszmód"); ablak.configure(bg=self.szinek["panel"]); ablak.transient(self)
        ttk.Label(ablak, text="ÍRÁSI CÉL", style="AppTitle.TLabel").pack(anchor="w", padx=18, pady=(18, 8))
        ttk.Label(ablak, text="Napi szócél:").pack(anchor="w", padx=18); cel = tk.IntVar(value=self.projekt.get("napi_cel", 500)); ttk.Spinbox(ablak, from_=50, to=10000, increment=50, textvariable=cel, width=12).pack(anchor="w", padx=18, pady=(3, 10))
        fokusz = tk.BooleanVar(value=False); ttk.Checkbutton(ablak, text="Fókuszmód bekapcsolása (teljes képernyő)", variable=fokusz).pack(anchor="w", padx=18, pady=(0, 14))
        def alkalmaz():
            self.projekt["napi_cel"] = cel.get(); self.attributes("-fullscreen", fokusz.get()); self.bind("<Escape>", lambda _e: self.attributes("-fullscreen", False)); ablak.destroy()
            osszes = sum(len(j["szoveg"].split()) for j in self.projekt["jelenetek"]); self.statusz.config(text=f"●  Írási cél: {osszes}/{cel.get()} szó")
        UvegGomb(ablak, "Alkalmazás", alkalmaz, accent=True, width=110).pack(anchor="e", padx=18, pady=(0, 18))

    def exportcsomag(self):
        self.adatokat_osszegyujt(); cel = filedialog.askdirectory(title="Exportcsomag mappája")
        if not cel: return
        try:
            mappa = Path(cel); alap = "fvg-storyeditor-export"
            (mappa / f"{alap}.fountain").write_text(self.fountain_tartalom(), encoding="utf-8")
            (mappa / f"{alap}.fvgscript").write_text(json.dumps(self.projekt, ensure_ascii=False, indent=2), encoding="utf-8")
            with (mappa / f"{alap}-jelenetek.csv").open("w", newline="", encoding="utf-8") as fajl:
                iro = csv.writer(fajl); iro.writerow(["Sorszám", "Fejléc", "Helyszín", "Idő", "Dramaturgia", "Szereplők", "Kellékek", "Jelmezek", "Hang / zene"])
                for i, j in enumerate(self.projekt["jelenetek"], 1):
                    k, b = j.get("kartya", {}), j.get("bontas", {})
                    iro.writerow([i, j["fejlec"], b.get("helyszin", k.get("helyszin", "")), k.get("ido", ""), k.get("dramaturgia", ""), b.get("szereplok", ""), b.get("kellekek", ""), b.get("jelmezek", ""), b.get("hang", "")])
            with (mappa / f"{alap}-karakterek.csv").open("w", newline="", encoding="utf-8") as fajl:
                iro = csv.writer(fajl); iro.writerow(["Név", "Leírás", "Cél", "Konfliktus"])
                for nev in self.projekt["karakterek"]: k = self.projekt.get("karakter_adatok", {}).get(nev, {}); iro.writerow([nev, k.get("leiras", ""), k.get("cel", ""), k.get("konfliktus", "")])
            self.statusz.config(text=f"●  Exportcsomag elkészült: {mappa}"); messagebox.showinfo("Exportcsomag", f"Elkészült 4 fájl:\n{mappa}")
        except OSError as hiba: messagebox.showerror("Exportcsomag", str(hiba))

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

    def autosave_helyreallitas_felajanlasa(self):
        """Egy korábbi, névtelen projekt automatikus mentését felajánlja induláskor."""
        cel = Path.cwd() / "fvg-storyeditor.autosave.json"
        if not cel.exists():
            return
        try:
            adat = json.loads(cel.read_text(encoding="utf-8"))
            if not all(k in adat for k in ("cim", "jelenetek", "karakterek")):
                return
            if messagebox.askyesno("Automatikus mentés", f"Találtam egy automatikus mentést:\n{adat['cim']}\n\nVisszaállítod?"):
                self.projekt = adat
                self.projekt.setdefault("verziok", []); self.projekt.setdefault("karakter_adatok", {}); self.projekt.setdefault("dramaturgia", []); self.projekt.setdefault("beatsheet", []); self.projekt.setdefault("kamera_beallitasok", [])
                for jelenet in self.projekt["jelenetek"]: jelenet.setdefault("blokkok", {}); jelenet.setdefault("kartya", {}); jelenet.setdefault("bontas", {}); jelenet.setdefault("megjegyzesek", ""); jelenet.setdefault("kepek", [])
                self.fajl_utvonal, self.aktualis_jelenet = None, None
                self.cim.delete(0, "end"); self.cim.insert(0, adat["cim"])
                self.szerzo.delete(0, "end"); self.szerzo.insert(0, adat.get("szerzo", ""))
                self.frissit_listak(); self.jelenet_mezo_tisztit()
                self.statusz.config(text="●  Automatikus mentés visszaállítva — mentsd el projektként.")
        except (OSError, ValueError, json.JSONDecodeError):
            return

    def kartyatabla(self):
        self.adatokat_osszegyujt()
        ablak = tk.Toplevel(self); ablak.title("Jelenetkártya-tábla — FVG Story Editor"); ablak.geometry("900x620"); ablak.configure(bg=self.szinek["hatterszin"]); ablak.transient(self)
        ttk.Label(ablak, text="JELENETKÁRTYA-TÁBLA", style="AppTitle.TLabel").pack(anchor="w", padx=20, pady=(18, 3))
        ttk.Label(ablak, text="Kattints egy kártyára a jelenet megnyitásához.", style="Tagline.TLabel").pack(anchor="w", padx=20, pady=(0, 12))
        vaszon = tk.Canvas(ablak, bg=self.szinek["hatterszin"], highlightthickness=0)
        gorgeto = ttk.Scrollbar(ablak, orient="vertical", command=vaszon.yview); vaszon.configure(yscrollcommand=gorgeto.set)
        gorgeto.pack(side="right", fill="y"); vaszon.pack(fill="both", expand=True, padx=(20, 5), pady=(0, 20))
        belso = tk.Frame(vaszon, bg=self.szinek["hatterszin"]); vaszon.create_window((0, 0), window=belso, anchor="nw")
        belso.bind("<Configure>", lambda _e: vaszon.configure(scrollregion=vaszon.bbox("all")))
        def megnyit(index):
            self.jelenet_rogzit(); self.aktualis_jelenet = None; self.frissit_jelenetek(kijelolt=index); self.jelenet_kivalaszt(); ablak.destroy()
        for i, jelenet in enumerate(self.projekt["jelenetek"]):
            kartya = jelenet.get("kartya", {}); panel = tk.Frame(belso, bg=self.szinek["panel_vilagos"], highlightbackground=self.szinek["vonal"], highlightthickness=1, padx=14, pady=12, cursor="hand2")
            panel.grid(row=i // 3, column=i % 3, padx=7, pady=7, sticky="nsew")
            ttk.Label(panel, text=f"{i + 1:02d}  {jelenet['fejlec']}", foreground=self.szinek["kiemeles"], wraplength=230, font=("Sans", 9, "bold")).pack(anchor="w")
            ttk.Label(panel, text=kartya.get("osszefoglalo") or "Nincs összefoglaló.", wraplength=230, justify="left").pack(anchor="w", pady=(8, 5))
            ttk.Label(panel, text=" · ".join(x for x in (kartya.get("helyszin"), kartya.get("dramaturgia")) if x) or "Jelenetkártya szerkesztése", foreground=self.szinek["halvany"], wraplength=230).pack(anchor="w")
            for elem in (panel, *panel.winfo_children()): elem.bind("<Button-1>", lambda _e, index=i: megnyit(index))
        for oszlop in range(3): belso.grid_columnconfigure(oszlop, weight=1)

    def dramaturgiai_iv(self):
        self.adatokat_osszegyujt()
        alap = ["Nyitókép", "Kiváltó esemény", "Első fordulópont", "Középpont", "Mélypont", "Finálé"]
        iv = self.projekt.setdefault("dramaturgia", [])
        while len(iv) < len(alap): iv.append({"nev": alap[len(iv)], "jelenet": "", "jegyzet": ""})
        ablak = tk.Toplevel(self); ablak.title("Dramaturgiai ív — FVG Story Editor"); ablak.geometry("650x560"); ablak.configure(bg=self.szinek["panel"]); ablak.transient(self)
        ttk.Label(ablak, text="DRAMATURGIAI ÍV", style="AppTitle.TLabel").pack(anchor="w", padx=18, pady=(18, 3))
        ttk.Label(ablak, text="A történet fő fordulópontjai és a hozzájuk tartozó jelenetek.").pack(anchor="w", padx=18, pady=(0, 12))
        tartalom = ttk.Frame(ablak); tartalom.pack(fill="both", expand=True, padx=18)
        jelenet_nevek = [j["fejlec"] for j in self.projekt["jelenetek"]]
        mezok = []
        for i, pont in enumerate(iv):
            sor = ttk.Labelframe(tartalom, text=pont["nev"], padding=8); sor.pack(fill="x", pady=4)
            valasztas = tk.StringVar(value=pont.get("jelenet", "")); ttk.Combobox(sor, textvariable=valasztas, values=jelenet_nevek, state="readonly", width=42).pack(fill="x")
            jegyzet = ttk.Entry(sor); jegyzet.insert(0, pont.get("jegyzet", "")); jegyzet.pack(fill="x", pady=(5, 0)); mezok.append((valasztas, jegyzet))
        def mentes():
            self.projekt["dramaturgia"] = [{"nev": alap[i], "jelenet": v.get(), "jegyzet": j.get().strip()} for i, (v, j) in enumerate(mezok)]
            ablak.destroy(); self.statusz.config(text="●  Dramaturgiai ív rögzítve")
        UvegGomb(ablak, "Dramaturgiai ív mentése", mentes, accent=True, width=190).pack(anchor="e", padx=18, pady=18)

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
            self.projekt["dramaturgia"] = json.loads(json.dumps(valasztott.get("dramaturgia", [])))
            self.projekt["beatsheet"] = json.loads(json.dumps(valasztott.get("beatsheet", [])))
            self.projekt["kamera_beallitasok"] = json.loads(json.dumps(valasztott.get("kamera_beallitasok", [])))
            self.projekt["jegyzetek"] = valasztott.get("jegyzetek", "")
            self.projekt["napi_cel"] = valasztott.get("napi_cel", 500)
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
        naplo = Path(__file__).with_name("inditasi_hiba.log")
        try:
            naplo.write_text(traceback.format_exc(), encoding="utf-8")
        except OSError:
            naplo = Path(tempfile.gettempdir()) / "fvg-story-editor-inditasi-hiba.log"
            naplo.write_text(traceback.format_exc(), encoding="utf-8")
        try:
            messagebox.showerror(
                "FVG Story Editor – indítási hiba",
                f"Az alkalmazás nem tudott elindulni.\n\n{hiba}\n\n"
                f"A részletek itt vannak: {naplo}",
            )
        except tk.TclError:
            pass
