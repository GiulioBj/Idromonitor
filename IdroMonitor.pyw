# Copyright (C) 2026 Giulio Bojan
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <https://www.gnu.org/licenses/>.

import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import os
import json
import glob
from datetime import datetime
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg, NavigationToolbar2Tk
from matplotlib.figure import Figure
from matplotlib.backends.backend_pdf import PdfPages
from matplotlib.dates import DateFormatter
import subprocess
import threading
import warnings
import sys
import requests
import configparser
import numpy as np

# Nascondi console su Windows
if sys.platform.startswith('win'):
    import ctypes
    ctypes.windll.user32.ShowWindow(ctypes.windll.kernel32.GetConsoleWindow(), 0)

warnings.filterwarnings("ignore", category=UserWarning, module="matplotlib")


# ==================== CLASSE AGGIUNGI STAZIONE ====================
class AggiungiStazione:
    def __init__(self, parent_app=None):
        self.parent_app = parent_app
        self.root = tk.Toplevel() if parent_app else tk.Tk()
        self.root.title("Aggiungi Stazione")
        self.root.geometry("550x680")
        self.root.resizable(False, False)
        if os.path.exists('IMLogo.ico'):
            self.root.iconbitmap('IMLogo.ico')
        self.crea_form()

    def crea_form(self):
        # Header
        header = tk.Frame(self.root, bg="#2c5aa0", height=80)
        header.pack(fill=tk.X)
        header.pack_propagate(False)
        tk.Label(header, text="➕ Aggiungi Nuova Stazione",
                font=("Arial", 18, "bold"), fg="white", bg="#2c5aa0").pack(pady=20)

        # Container principale
        container = tk.Frame(self.root, bg="#f8f9fa")
        container.pack(fill=tk.BOTH, expand=True, padx=30, pady=20)

        # API URL
        tk.Label(container, text="API URL dati idrometrici:",
                font=("Arial", 11, "bold"), bg="#f8f9fa").pack(anchor='w', pady=(10, 2))
        self.api_entry = tk.Entry(container, font=("Arial", 11), width=60)
        self.api_entry.pack(fill='x', pady=(0, 15))

        # Hint per API
        hint = tk.Label(container,
                       text="💡 Inserisci l'URL completo dell'API (es: https://api.arpa.veneto.it/REST/v1/meteo_meteogrammi_tabella)",
                       font=("Arial", 9), fg="#6c757d", bg="#f8f9fa", wraplength=450, justify='left')
        hint.pack(anchor='w', pady=(0, 10))

        # Separatore
        tk.Frame(container, height=2, bg="#dee2e6").pack(fill='x', pady=15)
        tk.Label(container, text="Configurazione Livelli Allerta",
                font=("Arial", 12, "bold"), bg="#f8f9fa").pack(anchor='w', pady=(5, 10))

        # Livello ORDINARIA
        tk.Label(container, text="Livello ORDINARIA (m) - 🟡 Giallo:",
                font=("Arial", 11, "bold"), bg="#f8f9fa").pack(anchor='w', pady=(5, 2))
        self.ordinaria_entry = tk.Entry(container, font=("Arial", 11), width=60)
        self.ordinaria_entry.pack(fill='x', pady=(0, 10))

        # Livello MODERATA
        tk.Label(container, text="Livello MODERATA (m) - 🟠 Arancione:",
                font=("Arial", 11, "bold"), bg="#f8f9fa").pack(anchor='w', pady=(5, 2))
        self.moderata_entry = tk.Entry(container, font=("Arial", 11), width=60)
        self.moderata_entry.pack(fill='x', pady=(0, 10))

        # Livello ELEVATA
        tk.Label(container, text="Livello ELEVATA (m) - 🔴 Rosso:",
                font=("Arial", 11, "bold"), bg="#f8f9fa").pack(anchor='w', pady=(5, 2))
        self.elevata_entry = tk.Entry(container, font=("Arial", 11), width=60)
        self.elevata_entry.pack(fill='x', pady=(0, 15))

        # Info livelli
        info = tk.Label(container,
                       text="ℹ️ I livelli devono essere crescenti: Ordinaria < Moderata < Elevata",
                       font=("Arial", 9), fg="#6c757d", bg="#f8f9fa", wraplength=450, justify='left')
        info.pack(anchor='w', pady=(0, 15))

        # Pulsanti
        btn_frame = tk.Frame(container, bg="#f8f9fa")
        btn_frame.pack(pady=15)
        self.btn_salva = ttk.Button(btn_frame, text="💾 Salva Stazione",
                                    command=self.salva_stazione)
        self.btn_salva.pack(side=tk.LEFT, padx=10, pady=10)
        ttk.Button(btn_frame, text="❌ Annulla",
                  command=self.root.destroy).pack(side=tk.LEFT, padx=10, pady=10)

    def salva_stazione(self):
        api_url = self.api_entry.get().strip()
        if not api_url:
            messagebox.showerror("Errore", "Inserisci API URL!")
            return

        try:
            # Valida livelli prima della chiamata API
            ordinaria_txt = self.ordinaria_entry.get().strip()
            moderata_txt = self.moderata_entry.get().strip()
            elevata_txt = self.elevata_entry.get().strip()

            if not ordinaria_txt or not moderata_txt or not elevata_txt:
                messagebox.showerror("Errore", "Compila tutti i livelli di allerta!")
                return

            ordinaria = float(ordinaria_txt)
            moderata = float(moderata_txt)
            elevata = float(elevata_txt)

            # Valida logica dei livelli
            if not (ordinaria < moderata < elevata):
                if not messagebox.askyesno("⚠️ Attenzione",
                                          f"I livelli non sono in ordine crescente!\n\n"
                                          f"Ordinaria: {ordinaria} m\n"
                                          f"Moderata: {moderata} m\n"
                                          f"Elevata: {elevata} m\n\n"
                                          f"Vuoi salvare comunque?"):
                    return

            # Mostra stato caricamento
            self.btn_salva.config(text="⏳ Caricamento...", state='disabled')
            self.root.update()

            # Chiama API
            response = requests.get(api_url, timeout=10)
            response.raise_for_status()
            dati = response.json()

            # Nuovo formato: {"success":true,"data":[...]}
            if dati.get('success') and 'data' in dati and dati['data']:
                primo_dato = dati['data'][0]  # Primo elemento lista
                nome_stazione = primo_dato.get('nome_stazione')
            else:
                self.btn_salva.config(text="💾 SALVA STAZIONE", state='normal')
                messagebox.showerror("Errore", "Formato JSON non valido!\nAspettato: {'success':true,'data':[...]}")
                return

            if not nome_stazione:
                self.btn_salva.config(text="💾 SALVA STAZIONE", state='normal')
                messagebox.showerror("Errore", "'nome_stazione' non trovato!")
                return

            # Salva
            os.makedirs("Stazioni", exist_ok=True)
            nome_file = "".join(c for c in nome_stazione if c.isalnum() or c in (' ', '-', '_')).rstrip()
            nome_file = nome_file.replace(' ', '_')[:50] + ".json"
            file_path = os.path.join("Stazioni", nome_file)

            # Controlla se esiste già
            if os.path.exists(file_path):
                if not messagebox.askyesno("⚠️ Stazione Esistente",
                                          f"La stazione '{nome_stazione}' esiste già!\n\n"
                                          f"Vuoi sovrascriverla?"):
                    self.btn_salva.config(text="💾 SALVA STAZIONE", state='normal')
                    return

            stazione = {
                "nome_stazione": nome_stazione,
                "api_url": api_url,
                "livello_ordinaria": ordinaria,
                "livello_moderata": moderata,
                "livello_elevata": elevata,
                "dati_api": dati  # Salva JSON completo
            }

            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(stazione, f, indent=4, ensure_ascii=False)

            messagebox.showinfo("✅ Salvato!",
                              f"Stazione aggiunta con successo!\n\n"
                              f"📍 Nome: {nome_stazione}\n"
                              f"📁 File: Stazioni/{nome_file}\n\n"
                              f"🟡 Ordinaria: {ordinaria} m\n"
                              f"🟠 Moderata: {moderata} m\n"
                              f"🔴 Elevata: {elevata} m")
            
            # Aggiorna app principale se presente
            if self.parent_app:
                self.parent_app.carica_stazioni_da_cartella()
            
            self.root.destroy()

        except ValueError:
            self.btn_salva.config(text="💾 SALVA STAZIONE", state='normal')
            messagebox.showerror("Errore", "I livelli devono essere numeri validi!\nUsa il punto (.) per i decimali.")
        except requests.RequestException:
            self.btn_salva.config(text="💾 SALVA STAZIONE", state='normal')
            messagebox.showerror("API Error", "Connessione fallita!")
        except (KeyError, IndexError):
            self.btn_salva.config(text="💾 SALVA STAZIONE", state='normal')
            messagebox.showerror("Dati Error", "Controlla URL e formato dati API!")
        except Exception:
            self.btn_salva.config(text="💾 SALVA STAZIONE", state='normal')
            messagebox.showerror("Errore", "Errore imprevisto durante il salvataggio!")

    def run(self):
        self.root.mainloop()


# ==================== CLASSE MODIFICA LIVELLI ====================
class ModificaLivelli:
    def __init__(self, nome_stazione=None, parent_app=None):
        self.parent_app = parent_app
        self.root = tk.Toplevel() if parent_app else tk.Tk()
        self.root.title("Modifica Livelli Allerta")
        self.root.geometry("550x620")
        self.root.resizable(False, False)
        if os.path.exists('IMLogo.ico'):
            self.root.iconbitmap('IMLogo.ico')

        self.stazioni = {}
        self.stazione_corrente = None
        self.file_path_corrente = None

        self.carica_stazioni()
        self.crea_form()

        # Se riceve nome stazione, preseleziona
        if nome_stazione and nome_stazione in self.stazioni:
            self.combo_stazioni.set(nome_stazione)
            self.carica_livelli_stazione()

    def carica_stazioni(self):
        """📂 Carica tutte le stazioni dalla cartella"""
        cartella_stazioni = "Stazioni"
        if not os.path.exists(cartella_stazioni):
            return

        for file_path in glob.glob(os.path.join(cartella_stazioni, "*.json")):
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    dati = json.load(f)
                    nome = dati.get('nome_stazione', os.path.basename(file_path)[:-5])
                    self.stazioni[nome] = file_path
            except Exception:
                pass

    def crea_form(self):
        # Header
        header = tk.Frame(self.root, bg="#2c5aa0", height=80)
        header.pack(fill=tk.X)
        header.pack_propagate(False)
        tk.Label(header, text="Modifica Livelli Allerta",
                font=("Arial", 18, "bold"), fg="white", bg="#2c5aa0").pack(pady=20)

        # Container principale
        container = tk.Frame(self.root, bg="#f8f9fa")
        container.pack(fill=tk.BOTH, expand=True, padx=30, pady=20)

        # Selezione stazione
        tk.Label(container, text="Seleziona Stazione:",
                font=("Arial", 12, "bold"), bg="#f8f9fa").pack(anchor='w', pady=(0, 5))

        if not self.stazioni:
            tk.Label(container, text="❌ Nessuna stazione trovata",
                    fg="#dc3545", bg="#f8f9fa", font=("Arial", 11)).pack(pady=20)
            ttk.Button(container, text="Chiudi", command=self.root.destroy).pack(side=tk.TOP, padx=10, pady=10)
            return

        self.combo_stazioni = ttk.Combobox(container,
                                          values=sorted(self.stazioni.keys()),
                                          font=("Arial", 11),
                                          state='readonly',
                                          width=57)
        self.combo_stazioni.pack(fill='x', pady=(0, 20))
        self.combo_stazioni.bind('<<ComboboxSelected>>', lambda e: self.carica_livelli_stazione())

        # Separatore
        tk.Frame(container, height=2, bg="#dee2e6").pack(fill='x', pady=10)

        # Campo Nome Stazione (readonly)
        tk.Label(container, text="Nome Stazione:",
                font=("Arial", 11, "bold"), bg="#f8f9fa").pack(anchor='w', pady=(10, 2))
        self.nome_label = tk.Label(container, text="-- Seleziona una stazione --",
                                   font=("Arial", 11), bg="white",
                                   anchor='w', relief='solid', bd=1, padx=10, pady=8)
        self.nome_label.pack(fill='x', pady=(0, 15))

        # Livello ORDINARIA
        tk.Label(container, text="Livello ORDINARIA (m) - 🟡 Giallo:",
                font=("Arial", 11, "bold"), bg="#f8f9fa").pack(anchor='w', pady=(5, 2))
        self.ordinaria_entry = tk.Entry(container, font=("Arial", 11), width=60)
        self.ordinaria_entry.pack(fill='x', pady=(0, 10))

        # Livello MODERATA
        tk.Label(container, text="Livello MODERATA (m) - 🟠 Arancione:",
                font=("Arial", 11, "bold"), bg="#f8f9fa").pack(anchor='w', pady=(5, 2))
        self.moderata_entry = tk.Entry(container, font=("Arial", 11), width=60)
        self.moderata_entry.pack(fill='x', pady=(0, 10))

        # Livello ELEVATA
        tk.Label(container, text="Livello ELEVATA (m) - 🔴 Rosso:",
                font=("Arial", 11, "bold"), bg="#f8f9fa").pack(anchor='w', pady=(5, 2))
        self.elevata_entry = tk.Entry(container, font=("Arial", 11), width=60)
        self.elevata_entry.pack(fill='x', pady=(0, 15))

        # Pulsanti
        btn_frame = tk.Frame(container, bg="#f8f9fa")
        btn_frame.pack(pady=15)
        self.btn_salva = ttk.Button(btn_frame, text="💾 Salva Modifiche",
                                    command=self.salva_modifiche,
                                    state='disabled')
        self.btn_salva.pack(side=tk.LEFT, padx=10, pady=10)
        ttk.Button(btn_frame, text="❌ Annulla",
                  command=self.root.destroy).pack(side=tk.LEFT, padx=10, pady=10)

    def carica_livelli_stazione(self):
        """📥 Carica i livelli della stazione selezionata"""
        nome_stazione = self.combo_stazioni.get()
        if not nome_stazione:
            return

        try:
            self.stazione_corrente = nome_stazione
            self.file_path_corrente = self.stazioni[nome_stazione]

            with open(self.file_path_corrente, 'r', encoding='utf-8') as f:
                dati = json.load(f)

            # Aggiorna UI
            self.nome_label.config(text=nome_stazione, fg="#2c5aa0", font=("Arial", 11, "bold"))

            # Carica livelli esistenti
            ordinaria = dati.get('livello_ordinaria', '')
            moderata = dati.get('livello_moderata', '')
            elevata = dati.get('livello_elevata', '')

            self.ordinaria_entry.delete(0, tk.END)
            self.ordinaria_entry.insert(0, str(ordinaria) if ordinaria is not None else "")

            self.moderata_entry.delete(0, tk.END)
            self.moderata_entry.insert(0, str(moderata) if moderata is not None else "")

            self.elevata_entry.delete(0, tk.END)
            self.elevata_entry.insert(0, str(elevata) if elevata is not None else "")

            # Abilita pulsante salva
            self.btn_salva.config(state='normal')

        except Exception:
            messagebox.showerror("Errore", "Impossibile caricare i dati della stazione!")

    def salva_modifiche(self):
        """💾 Salva le modifiche ai livelli"""
        if not self.stazione_corrente or not self.file_path_corrente:
            messagebox.showerror("Errore", "Seleziona prima una stazione!")
            return

        try:
            # Valida input numerici
            ordinaria_txt = self.ordinaria_entry.get().strip()
            moderata_txt = self.moderata_entry.get().strip()
            elevata_txt = self.elevata_entry.get().strip()

            # Converti in float (permetti campi vuoti)
            ordinaria = float(ordinaria_txt) if ordinaria_txt else None
            moderata = float(moderata_txt) if moderata_txt else None
            elevata = float(elevata_txt) if elevata_txt else None

            # Valida logica dei livelli
            livelli = [l for l in [ordinaria, moderata, elevata] if l is not None]
            if len(livelli) > 1:
                if not all(livelli[i] < livelli[i+1] for i in range(len(livelli)-1)):
                    if not messagebox.askyesno("⚠️ Attenzione",
                                              "I livelli non sono in ordine crescente!\n"
                                              "Ordinaria < Moderata < Elevata\n\n"
                                              "Vuoi salvare comunque?"):
                        return

            # Carica JSON esistente
            with open(self.file_path_corrente, 'r', encoding='utf-8') as f:
                dati = json.load(f)

            # Aggiorna solo i livelli
            dati['livello_ordinaria'] = ordinaria
            dati['livello_moderata'] = moderata
            dati['livello_elevata'] = elevata

            # Salva file
            with open(self.file_path_corrente, 'w', encoding='utf-8') as f:
                json.dump(dati, f, indent=4, ensure_ascii=False)

            messagebox.showinfo("✅ Salvato!",
                              f"Livelli aggiornati per:\n{self.stazione_corrente}\n\n"
                              f"🟡 Ordinaria: {ordinaria if ordinaria is not None else 'Non impostato'} m\n"
                              f"🟠 Moderata: {moderata if moderata is not None else 'Non impostato'} m\n"
                              f"🔴 Elevata: {elevata if elevata is not None else 'Non impostato'} m")
            
            # Aggiorna app principale se presente
            if self.parent_app:
                self.parent_app.carica_stazioni_da_cartella()
            
            self.root.destroy()

        except ValueError:
            messagebox.showerror("Errore", "I livelli devono essere numeri validi!\nUsa il punto (.) per i decimali.")
        except Exception:
            messagebox.showerror("Errore", "Impossibile salvare le modifiche!")

    def run(self):
        self.root.mainloop()


# ==================== CLASSE SALVA REPORT ====================
class SalvaReportApp:
    def __init__(self, parent_app=None):
        self.parent_app = parent_app
        self.root = tk.Toplevel() if parent_app else tk.Tk()
        self.root.title("Salva Report IdroMonitor")
        self.root.geometry("600x800")
        self.root.resizable(False, False)
        if os.path.exists('IMLogo.ico'):
            self.root.iconbitmap('IMLogo.ico')

        self.stazioni = {}
        self.stazioni_selezionate = []
        self.config_file = "report_config.ini"
        self.ultima_cartella = self.carica_ultima_cartella()

        self.carica_stazioni()
        self.crea_interfaccia()

    def carica_stazioni(self):
        """📂 Carica tutte le stazioni disponibili"""
        cartella_stazioni = "Stazioni"
        if not os.path.exists(cartella_stazioni):
            return

        for file_path in glob.glob(os.path.join(cartella_stazioni, "*.json")):
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    dati = json.load(f)
                    nome = dati.get('nome_stazione', os.path.basename(file_path)[:-5])
                    self.stazioni[nome] = file_path
            except Exception:
                pass

    def carica_ultima_cartella(self):
        """💾 Carica ultima cartella di salvataggio"""
        if os.path.exists(self.config_file):
            try:
                config = configparser.ConfigParser()
                config.read(self.config_file)
                return config.get('DEFAULT', 'ultima_cartella', fallback=os.path.expanduser("~"))
            except:
                return os.path.expanduser("~")
        return os.path.expanduser("~")

    def salva_ultima_cartella(self, cartella):
        """💾 Salva ultima cartella utilizzata"""
        config = configparser.ConfigParser()
        config['DEFAULT'] = {'ultima_cartella': cartella}
        with open(self.config_file, 'w') as f:
            config.write(f)

    def crea_interfaccia(self):
        # Header
        header = tk.Frame(self.root, bg="#2c5aa0", height=80)
        header.pack(fill=tk.X)
        header.pack_propagate(False)
        tk.Label(header, text="💾 Genera Report PDF",
                font=("Arial", 18, "bold"), fg="white", bg="#2c5aa0").pack(pady=20)

        # Container principale
        container = tk.Frame(self.root, bg="#f8f9fa")
        container.pack(fill=tk.BOTH, expand=True, padx=30, pady=20)

        if not self.stazioni:
            tk.Label(container, text="❌ Nessuna stazione trovata",
                    fg="#dc3545", bg="#f8f9fa", font=("Arial", 12, "bold")).pack(pady=20)
            ttk.Button(container, text="Chiudi", command=self.root.destroy).pack(side=tk.TOP, padx=10, pady=10)
            return

        # Selezione stazioni
        tk.Label(container, text="Seleziona stazioni per il report:",
                font=("Arial", 12, "bold"), bg="#f8f9fa").pack(anchor='w', pady=(10, 5))

        # Checkbox "Tutte le stazioni"
        self.var_tutte = tk.BooleanVar(value=False)
        checkbox_tutte = tk.Checkbutton(container, text="✅ Seleziona TUTTE le stazioni",
                                       variable=self.var_tutte,
                                       command=self.toggle_tutte_stazioni,
                                       font=("Arial", 11, "bold"),
                                       bg="#f8f9fa", fg="#2c5aa0",
                                       activebackground="#f8f9fa",
                                       selectcolor="white")
        checkbox_tutte.pack(anchor='w', pady=(5, 10))

        # Frame con scrollbar per lista stazioni
        lista_frame = tk.Frame(container, bg="white", relief='solid', bd=1)
        lista_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 15))

        scrollbar = tk.Scrollbar(lista_frame)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        self.canvas_lista = tk.Canvas(lista_frame, bg="white",
                                      yscrollcommand=scrollbar.set,
                                      highlightthickness=0)
        self.canvas_lista.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.config(command=self.canvas_lista.yview)

        # Frame interno per checkbox
        self.frame_checkbox = tk.Frame(self.canvas_lista, bg="white")
        self.canvas_lista.create_window((0, 0), window=self.frame_checkbox, anchor='nw')

        # Crea checkbox per ogni stazione
        self.checkbox_vars = {}
        for i, nome in enumerate(sorted(self.stazioni.keys())):
            var = tk.BooleanVar(value=False)
            self.checkbox_vars[nome] = var
            cb = tk.Checkbutton(self.frame_checkbox, text=f"  {nome}",
                               variable=var,
                               font=("Arial", 10),
                               bg="white",
                               activebackground="white",
                               selectcolor="#e3f2fd")
            cb.pack(anchor='w', padx=10, pady=2)

        # Aggiorna scroll region
        self.frame_checkbox.update_idletasks()
        self.canvas_lista.config(scrollregion=self.canvas_lista.bbox("all"))

        # Info cartella destinazione
        tk.Label(container, text="📁 Cartella di salvataggio:",
                font=("Arial", 11, "bold"), bg="#f8f9fa").pack(anchor='w', pady=(10, 5))
        self.label_cartella = tk.Label(container,
                                       text=self.ultima_cartella if self.ultima_cartella else "Nessuna cartella selezionata",
                                       font=("Arial", 9), bg="white", fg="#6c757d",
                                       anchor='w', relief='solid', bd=1, padx=10, pady=8,
                                       wraplength=500, justify='left')
        self.label_cartella.pack(fill='x', pady=(0, 5))
        ttk.Button(container, text="📂 Cambia cartella",
                  command=self.seleziona_cartella).pack(anchor='w', pady=(0, 15))

        # Pulsanti azione
        btn_frame = tk.Frame(container, bg="#f8f9fa")
        btn_frame.pack(pady=15)
        ttk.Button(btn_frame, text="💾 Salva Report",
                  command=self.genera_report).pack(side=tk.LEFT, padx=10, pady=10)
        ttk.Button(btn_frame, text="❌ Annulla",
                  command=self.root.destroy).pack(side=tk.LEFT, padx=10, pady=10)

    def toggle_tutte_stazioni(self):
        """✅ Seleziona/Deseleziona tutte le stazioni"""
        valore = self.var_tutte.get()
        for var in self.checkbox_vars.values():
            var.set(valore)

    def seleziona_cartella(self):
        """📂 Apri dialog selezione cartella"""
        # Porta la finestra in primo piano prima di aprire il dialog
        self.root.lift()
        self.root.focus_force()
        
        cartella = filedialog.askdirectory(
            parent=self.root,  # ← IMPORTANTE: specifica il parent
            title="Seleziona cartella per salvare i report",
            initialdir=self.ultima_cartella
        )
        
        if cartella:
            self.ultima_cartella = cartella
            self.label_cartella.config(text=cartella, fg="#2c5aa0")
            self.salva_ultima_cartella(cartella)
        
        # Riporta il focus alla finestra dopo la selezione
        self.root.lift()
        self.root.focus_force()

    def calcola_colore_livello(self, livello_corrente, dati):
        """🎨 Calcola colore in base al livello di allerta"""
        try:
            if livello_corrente is None:
                return "#6c757d"

            soglia_ordinaria = dati.get('livello_ordinaria')
            soglia_moderata = dati.get('livello_moderata')
            soglia_elevata = dati.get('livello_elevata')

            if soglia_elevata is not None and livello_corrente > float(soglia_elevata):
                return "#dc3545"  # 🔴 ROSSO
            elif soglia_moderata is not None and livello_corrente > float(soglia_moderata):
                return "#fd7e14"  # 🟠 ARANCIONE
            elif soglia_ordinaria is not None and livello_corrente >= float(soglia_ordinaria):
                return "#ffc107"  # 🟡 GIALLO
            else:
                return "#28a745"  # 🟢 VERDE
        except:
            return "#6c757d"

    def get_livello_corrente(self, file_path):
        """🔍 Legge ultimo livello LIDRO"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                dati = json.load(f)
            dati_api = dati.get('dati_api', {})
            data_list = dati_api.get('data', [])
            lidro_data = [item for item in data_list if item.get("tipo") == "LIDRO"]
            if not lidro_data:
                return None
            return float(lidro_data[-1]["valore"])
        except:
            return None

    def prepara_dati_grafico(self, file_path):
        """📊 Prepara dati per grafico e tabella"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                dati = json.load(f)
            dati_api = dati.get('dati_api', {})
            data_list = dati_api.get('data', [])
            lidro_data = [item for item in data_list if item.get("tipo") == "LIDRO"]

            tempi = []
            valori = []
            tabella_dati = []

            for item in lidro_data:
                try:
                    t = datetime.fromisoformat(item["dataora"])
                    v = float(item["valore"])
                    tempi.append(t)
                    valori.append(v)

                    # Calcola colore per ogni riga della tabella
                    colore = self.calcola_colore_livello(v, dati)
                    tabella_dati.append([t.strftime('%d/%m/%Y'), t.strftime('%H:%M'), f"{v:.2f}", colore])
                except:
                    continue

            return dati, tempi, valori, tabella_dati
        except Exception:
            return None, [], [], []

    def crea_header(self, fig, nome_stazione, pagina, totale_pagine):
        """📄 Crea header standard per ogni pagina"""
        fig.text(0.5, 0.97, "Report IdroMonitor",
                ha='center', va='top', fontsize=18, fontweight='bold', color='#2c5aa0')
        fig.text(0.5, 0.945, datetime.now().strftime('%d/%m/%Y %H:%M'),
                ha='center', va='top', fontsize=9, color='#6c757d')
        fig.text(0.5, 0.92, f"Stazione: {nome_stazione}",
                ha='center', va='top', fontsize=13, fontweight='bold', color='#2c3e50')

        # Footer
        fig.text(0.5, 0.02, f"Protezione Civile di Pernumia - Pagina {pagina}/{totale_pagine}",
                ha='center', va='bottom', fontsize=8, color='#6c757d')

    def crea_pagina_grafico(self, pdf, nome_stazione, dati, tempi, valori, num_pagina, totale_pagine):
        """📊 Crea pagina con grafico ORIZZONTALE (landscape)"""
        # Figura A4 ORIZZONTALE (landscape)
        fig = plt.figure(figsize=(11.69, 8.27))
        fig.subplots_adjust(left=0.08, right=0.92, top=0.90, bottom=0.12)

        # Header
        fig.text(0.5, 0.97, "Report IdroMonitor",
                ha='center', va='top', fontsize=18, fontweight='bold', color='#2c5aa0')
        fig.text(0.5, 0.945, datetime.now().strftime('%d/%m/%Y %H:%M'),
                ha='center', va='top', fontsize=9, color='#6c757d')
        fig.text(0.5, 0.92, f"Stazione: {nome_stazione}",
                ha='center', va='top', fontsize=13, fontweight='bold', color='#2c3e50')

        # Info livelli
        livello_attuale = self.get_livello_corrente(self.stazioni[nome_stazione])
        livelli_ord = dati.get('livello_ordinaria', 'N/D')
        livelli_mod = dati.get('livello_moderata', 'N/D')
        livelli_ele = dati.get('livello_elevata', 'N/D')

        # Colore livello attuale
        colore_livello = self.calcola_colore_livello(livello_attuale, dati)
        fig.text(0.5, 0.885, f"Livello Attuale: {livello_attuale:.2f} m",
                ha='center', va='top', fontsize=11, fontweight='bold', color=colore_livello)

        info_text = f"Soglie Allerta | Ordinaria: {livelli_ord} m | Moderata: {livelli_mod} m | Elevata: {livelli_ele} m"
        fig.text(0.5, 0.86, info_text,
                ha='center', va='top', fontsize=9, color='#495057')

        # Grafico principale (occupa maggior parte della pagina orizzontale)
        ax = fig.add_axes([0.10, 0.18, 0.85, 0.62])
        ax.plot(tempi, valori, '-', linewidth=2.5, color='#2980b9', alpha=0.9, marker='o', markersize=3)
        ax.set_xlabel("Tempo", fontsize=12, fontweight='bold')
        ax.set_ylabel("Livello (m)", fontsize=12, fontweight='bold')
        ax.set_title("Andamento Livello Idrometrico", fontsize=14, fontweight='bold', pad=15)
        ax.grid(True, alpha=0.3, linestyle='--', linewidth=0.5)
        ax.xaxis.set_major_formatter(DateFormatter('%d/%m\n%H:%M'))
        plt.setp(ax.xaxis.get_majorticklabels(), rotation=45, ha='right', fontsize=9)
        plt.setp(ax.yaxis.get_majorticklabels(), fontsize=10)

        # Footer
        fig.text(0.5, 0.02, f"Protezione Civile di Pernumia - Pagina {num_pagina}/{totale_pagine}",
                ha='center', va='bottom', fontsize=8, color='#6c757d')

        pdf.savefig(fig, orientation='landscape')
        plt.close(fig)

    def crea_pagine_tabella(self, pdf, nome_stazione, tabella_dati, num_pagina_inizio, totale_pagine):
        """📄 Crea pagine tabella con 2 tabelle affiancate per pagina (portrait)"""
        # 45 righe per tabella, 2 tabelle per pagina = 90 righe totali per pagina
        righe_per_tabella = 45
        righe_per_pagina = righe_per_tabella * 2

        # Inverti ordine: più recenti in alto
        tabella_dati_reversed = tabella_dati[::-1]
        num_pagine = (len(tabella_dati_reversed) + righe_per_pagina - 1) // righe_per_pagina

        for pagina_idx in range(num_pagine):
            inizio = pagina_idx * righe_per_pagina
            fine = min((pagina_idx + 1) * righe_per_pagina, len(tabella_dati_reversed))
            chunk = tabella_dati_reversed[inizio:fine]

            # Crea figura A4 VERTICALE (portrait)
            fig = plt.figure(figsize=(8.27, 11.69))
            fig.subplots_adjust(left=0.05, right=0.95, top=0.88, bottom=0.08)

            # Header
            self.crea_header(fig, nome_stazione, num_pagina_inizio + pagina_idx, totale_pagine)

            # Titolo sezione dati
            fig.text(0.5, 0.87, "Dati Completi Rilevazioni",
                    ha='center', va='top', fontsize=12, fontweight='bold', color='#2c3e50')

            # Dividi chunk in 2 tabelle
            tabella_sx = chunk[0:righe_per_tabella]
            tabella_dx = chunk[righe_per_tabella:righe_per_tabella*2]

            # TABELLA SINISTRA
            if tabella_sx:
                ax_sx = fig.add_axes([0.05, 0.10, 0.44, 0.74])
                ax_sx.axis('tight')
                ax_sx.axis('off')

                # Separa dati e colori
                dati_sx = [[riga[0], riga[1], riga[2]] for riga in tabella_sx]
                colori_sx = [riga[3] for riga in tabella_sx]

                table_sx = ax_sx.table(cellText=dati_sx,
                                      colLabels=['Data', 'Ora', 'Livello\n(m)'],
                                      cellLoc='center',
                                      loc='upper center',
                                      colWidths=[0.40, 0.30, 0.30])
                table_sx.auto_set_font_size(False)
                table_sx.set_fontsize(7.5)
                table_sx.scale(1, 1.5)

                # Stile tabella sinistra
                for (row, col), cell in table_sx.get_celld().items():
                    if row == 0:  # Header
                        cell.set_facecolor('#2c5aa0')
                        cell.set_text_props(weight='bold', color='white', fontsize=8)
                        cell.set_height(0.025)
                    else:
                        if row % 2 == 0:
                            cell.set_facecolor('#f8f9fa')
                        else:
                            cell.set_facecolor('white')
                        cell.set_edgecolor('#dee2e6')
                        cell.set_height(0.020)

                        # Colora colonna Livello
                        if col == 2:
                            cell.set_text_props(color=colori_sx[row-1], weight='bold')

            # TABELLA DESTRA
            if tabella_dx:
                ax_dx = fig.add_axes([0.51, 0.10, 0.44, 0.74])
                ax_dx.axis('tight')
                ax_dx.axis('off')

                # Separa dati e colori
                dati_dx = [[riga[0], riga[1], riga[2]] for riga in tabella_dx]
                colori_dx = [riga[3] for riga in tabella_dx]

                table_dx = ax_dx.table(cellText=dati_dx,
                                      colLabels=['Data', 'Ora', 'Livello\n(m)'],
                                      cellLoc='center',
                                      loc='upper center',
                                      colWidths=[0.40, 0.30, 0.30])
                table_dx.auto_set_font_size(False)
                table_dx.set_fontsize(7.5)
                table_dx.scale(1, 1.5)

                # Stile tabella destra
                for (row, col), cell in table_dx.get_celld().items():
                    if row == 0:  # Header
                        cell.set_facecolor('#2c5aa0')
                        cell.set_text_props(weight='bold', color='white', fontsize=8)
                        cell.set_height(0.025)
                    else:
                        if row % 2 == 0:
                            cell.set_facecolor('#f8f9fa')
                        else:
                            cell.set_facecolor('white')
                        cell.set_edgecolor('#dee2e6')
                        cell.set_height(0.020)

                        # Colora colonna Livello
                        if col == 2:
                            cell.set_text_props(color=colori_dx[row-1], weight='bold')

            pdf.savefig(fig)
            plt.close(fig)

        return num_pagine

    def genera_report(self):
        """📄 Genera PDF report"""
        # Verifica selezione stazioni
        stazioni_selezionate = [nome for nome, var in self.checkbox_vars.items() if var.get()]

        if not stazioni_selezionate:
            messagebox.showerror("Errore", "Seleziona almeno una stazione!")
            return

        if not self.ultima_cartella:
            messagebox.showerror("Errore", "Seleziona una cartella di destinazione!")
            return

        try:
            # Nome file
            ora_corrente = datetime.now().strftime('%Y%m%d_%H%M%S')
            if len(stazioni_selezionate) == 1:
                nome_stazione_file = stazioni_selezionate[0].replace(' ', '_')[:30]
                nome_file = f"ReportIM_{nome_stazione_file}_{ora_corrente}.pdf"
            else:
                nome_file = f"ReportIM_Stazioni_{ora_corrente}.pdf"

            file_path = os.path.join(self.ultima_cartella, nome_file)

            # Conta totale pagine per ogni stazione
            pagine_per_stazione = {}
            for nome_stazione in stazioni_selezionate:
                file_stazione = self.stazioni[nome_stazione]
                dati, tempi, valori, tabella_dati = self.prepara_dati_grafico(file_stazione)

                if not tempi:
                    pagine_per_stazione[nome_stazione] = 0
                    continue

                # 1 pagina grafico + pagine tabella
                righe_per_pagina = 90  # 45 righe x 2 tabelle
                num_pagine_tabella = (len(tabella_dati) + righe_per_pagina - 1) // righe_per_pagina
                pagine_per_stazione[nome_stazione] = 1 + num_pagine_tabella

            totale_pagine_report = sum(pagine_per_stazione.values())

            # Crea PDF
            with PdfPages(file_path) as pdf:
                pagina_corrente = 1

                for nome_stazione in stazioni_selezionate:
                    file_stazione = self.stazioni[nome_stazione]
                    dati, tempi, valori, tabella_dati = self.prepara_dati_grafico(file_stazione)

                    if not tempi:
                        continue

                    totale_pagine_stazione = pagine_per_stazione[nome_stazione]

                    # PAGINA 1: Grafico ORIZZONTALE (landscape)
                    self.crea_pagina_grafico(pdf, nome_stazione, dati, tempi, valori,
                                            pagina_corrente, totale_pagine_report)
                    pagina_corrente += 1

                    # PAGINE SUCCESSIVE: 2 tabelle affiancate (portrait)
                    num_pagine_tabella = self.crea_pagine_tabella(pdf, nome_stazione, tabella_dati,
                                                                  pagina_corrente, totale_pagine_report)
                    pagina_corrente += num_pagine_tabella

            messagebox.showinfo("✅ Report Generato!",
                              f"Report salvato con successo!\n\n"
                              f"📁 Posizione: {self.ultima_cartella}\n"
                              f"📄 File: {nome_file}\n"
                              f"📊 Stazioni: {len(stazioni_selezionate)}\n"
                              f"📄 Pagine totali: {totale_pagine_report}")
            self.root.destroy()

        except Exception:
            messagebox.showerror("Errore", "Impossibile generare il report!")

    def run(self):
        self.root.mainloop()


# ==================== FUNZIONE REFRESH DATI ====================
def esegui_refresh_dati():
    """🔄 Aggiorna dati da API (equivalente a refresh.pyw)"""
    cartella = "Stazioni"
    if not os.path.exists(cartella):
        return

    for filename in os.listdir(cartella):
        if filename.endswith('.json'):
            file_path = os.path.join(cartella, filename)
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    dati = json.load(f)
                api_url = dati.get('api_url')
            except:
                continue

            if not api_url:
                continue

            try:
                response = requests.get(api_url, timeout=10)
                nuovi_dati = response.json()
                dati['dati_api'] = nuovi_dati
                dati['dati_api']['timestamp_aggiornamento'] = datetime.now().isoformat()

                with open(file_path, 'w', encoding='utf-8') as f:
                    json.dump(dati, f, indent=4, ensure_ascii=False)
            except Exception:
                pass


# ==================== CLASSE PRINCIPALE IDROMONITOR ====================
class ProtezioneCivileApp:
    def __init__(self, root):
        self.root = root
        self.root.title("IdroMonitor")
        self.root.state('zoomed')
        self.root.geometry("1400x700")
        self.root.minsize(1400, 700)
        self.root.resizable(True, True)
        if os.path.exists('IMLogo.ico'):
            self.root.iconbitmap('IMLogo.ico')

        # Dati stazioni
        self.stazioni = []
        self.stazioni_files = {}
        self.stazioni_livelli = {}
        self.stazioni_colori = {}
        self.mappa_lista_stazioni = {}

        # Grafico
        self.canvas = None
        self.current_stazione = None
        self.linea = None
        self.fig = None
        self.ax = None
        self.tempi = []
        self.valori = []

        # Tooltip
        self.annotation = None

        # Refresh e animazioni
        self.pulsante_refresh = None
        self.pulsante_modifica_livelli = None
        self.auto_refresh_id = None
        self.animazione_id = None
        self.clessidra_frame = 0

        plt.style.use('default')

        self.crea_interfaccia()
        self.carica_stazioni_da_cartella()
        self.root.after(100, self.apri_prima_stazione)
        self.root.after(5000, self.avvia_refresh_dati)
        self.avvia_auto_refresh()

    def get_livello_corrente(self, nome_stazione):
        """🔍 Legge PRIMO dato LIDRO da JSON"""
        try:
            file_path = self.stazioni_files.get(nome_stazione)
            if not file_path or not os.path.exists(file_path):
                return None

            with open(file_path, 'r', encoding='utf-8') as f:
                dati_stazione = json.load(f)

            dati_api = dati_stazione.get('dati_api', {})
            data_list = dati_api.get('data', [])
            lidro_data = [item for item in data_list if item.get("tipo") == "LIDRO"]

            if not lidro_data:
                return None

            primo_dato = lidro_data[-1]
            return float(primo_dato["valore"])
        except:
            return None

    def calcola_colore_allerta(self, nome_stazione):
        """🎨 Calcola colore con ULTIMO LIDRO e Soglie SPECIFICHE della stazione"""
        livello_corrente = self.get_livello_corrente(nome_stazione)
        if livello_corrente is None:
            return "#f0f0f0"

        try:
            file_path = self.stazioni_files.get(nome_stazione)
            with open(file_path, 'r', encoding='utf-8') as f:
                dati = json.load(f)

            soglia_ordinaria = dati.get('livello_ordinaria')
            soglia_moderata = dati.get('livello_moderata')
            soglia_elevata = dati.get('livello_elevata')

            if soglia_elevata is not None and livello_corrente > float(soglia_elevata):
                return "#dc3545"  # 🔴 ROSSO
            elif soglia_moderata is not None and livello_corrente > float(soglia_moderata):
                return "#fd7e14"  # 🟠 ARANCIONE
            elif soglia_ordinaria is not None and livello_corrente >= float(soglia_ordinaria):
                return "#ffc107"  # 🟡 GIALLO
            else:
                return "#28a745"  # 🟢 VERDE
        except:
            return "#f0f0f0"

    def carica_stazioni_da_cartella(self):
        """📂 Carica + RIVERIFICA COLORI con ULTIMO LIDRO"""
        self.stazioni = []
        self.stazioni_files = {}
        self.stazioni_livelli = {}
        self.stazioni_colori = {}

        cartella_stazioni = "Stazioni"
        if not os.path.exists(cartella_stazioni):
            self.aggiorna_lista_stazioni()
            return

        temp_stazioni = []
        for file_path in glob.glob(os.path.join(cartella_stazioni, "*.json")):
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    dati = json.load(f)
                nome_stazione = dati.get('nome_stazione', os.path.basename(file_path)[:-5])
                temp_stazioni.append((nome_stazione.lower(), nome_stazione, file_path))

                self.stazioni_livelli[nome_stazione] = self.get_livello_corrente(nome_stazione)
                self.stazioni_colori[nome_stazione] = self.calcola_colore_allerta(nome_stazione)
            except Exception:
                pass

        temp_stazioni.sort(key=lambda x: x[0])
        for _, nome, file_path in temp_stazioni:
            self.stazioni.append(nome)
            self.stazioni_files[nome] = file_path

        self.aggiorna_lista_stazioni()

        # 🔄 Ricarica grafico se c'è una stazione aperta
        if self.current_stazione and self.current_stazione in self.stazioni:
            self.root.after(100, lambda: self.avvia_graph(self.current_stazione))

    def crea_interfaccia(self):
        # Header
        header_frame = tk.Frame(self.root, bg="#2c5aa0", height=80)
        header_frame.pack(side=tk.TOP, fill=tk.X)
        header_frame.pack_propagate(False)
        tk.Label(header_frame, text="Protezione Civile di Pernumia",
                font=("Arial", 24, "bold"), fg="white", bg="#2c5aa0").pack(side=tk.TOP, pady=22)

        # Menu
        menu_frame = tk.Frame(self.root, height=50, bg="#e8f4f8")
        menu_frame.pack(side=tk.TOP, fill=tk.X)
        menu_frame.pack_propagate(False)

        ttk.Button(menu_frame, text="Aggiungi stazione", command=self.apri_aggiungi_stazione).pack(side=tk.LEFT, padx=10, pady=10)
        ttk.Button(menu_frame, text="Rimuovi stazione", command=self.rimuovi_stazione).pack(side=tk.LEFT, padx=10, pady=10)
        ttk.Button(menu_frame, text="Aggiorna stazioni", command=self.carica_stazioni_da_cartella).pack(side=tk.LEFT, padx=10, pady=10)

        # Pulsante Modifica livelli (disabilitato di default)
        self.pulsante_modifica_livelli = ttk.Button(menu_frame, text="Modifica livelli",
                                                    command=self.apri_modifica_livelli,
                                                    state='disabled')
        self.pulsante_modifica_livelli.pack(side=tk.LEFT, padx=10, pady=10)

        self.pulsante_refresh = ttk.Button(menu_frame, text="⏳ Aggiornamento dati", command=self.avvia_refresh_dati)
        self.pulsante_refresh.pack(side=tk.LEFT, padx=10, pady=10)

        ttk.Button(menu_frame, text="ℹ️ Info", command=self.info).pack(side=tk.RIGHT, padx=10, pady=10)
        ttk.Button(menu_frame, text="💾 Salva Report", command=self.salva_report).pack(side=tk.RIGHT, padx=10, pady=10)

        # Main frame
        main_frame = tk.Frame(self.root, bg="#f8f9fa")
        main_frame.pack(fill=tk.BOTH, expand=True)

        # Left frame - Lista stazioni
        left_frame = tk.Frame(main_frame, width=380, bg="#ecf0f1")
        left_frame.pack(side=tk.LEFT, fill=tk.Y, padx=15, pady=15)
        left_frame.pack_propagate(False)

        tk.Label(left_frame, text="Stazioni Idrometriche:",
                font=("Arial", 13, "bold"), bg="#ecf0f1").pack(pady=(15, 5))

        # Ricerca
        ricerca_frame = tk.Frame(left_frame, bg="#ecf0f1")
        ricerca_frame.pack(fill=tk.X, padx=20, pady=(0, 10))

        tk.Label(ricerca_frame, text="🔍 Cerca:", font=("Arial", 10, "bold"),
                bg="#ecf0f1", fg="#2c3e50").pack(side=tk.LEFT, padx=(0, 5))

        self.entry_ricerca = tk.Entry(ricerca_frame, font=("Arial", 10), width=18)
        self.entry_ricerca.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 10))
        self.entry_ricerca.bind('<KeyRelease>', self.filtra_stazioni)

        ttk.Button(ricerca_frame, text="✕", width=2, command=self.pulisci_ricerca).pack(side=tk.RIGHT)

        # Lista con scrollbar
        lista_frame = tk.Frame(left_frame, bg="#ecf0f1")
        lista_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=(0, 15))

        scrollbar = tk.Scrollbar(
            lista_frame,
            bg="white",
            troughcolor="#ecf0f1",
            activebackground="#666666",
            bd=1,
            highlightthickness=0,
            relief='flat'
        )
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        self.lista_stazioni = tk.Listbox(
            lista_frame,
            font=("Arial", 11),
            height=22,
            bg="white",
            fg="black",
            selectbackground="#e3f2fd",
            selectforeground="black",
            yscrollcommand=scrollbar.set,
            selectmode=tk.SINGLE,
            activestyle='none',
            highlightthickness=1,
            bd=0,
            relief='flat',
            highlightbackground="#4a4a4a",
            highlightcolor="#4a4a4a"
        )
        self.lista_stazioni.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.config(command=self.lista_stazioni.yview)
        self.lista_stazioni.bind('<<ListboxSelect>>', self.on_stazione_select)

        # Graph container
        graph_container = tk.Frame(main_frame, bg="white", bd=1, relief='flat', highlightthickness=0)
        graph_container.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True, padx=15, pady=15)
        graph_container.config(highlightbackground="#4a4a4a", highlightcolor="#4a4a4a")

        # Graph header
        graph_header = tk.Frame(graph_container, bg="#f8f9fa", height=100, relief='flat')
        graph_header.pack(fill=tk.X, padx=15, pady=(20, 15))
        graph_header.pack_propagate(False)

        # Titoli
        titoli_frame = tk.Frame(graph_header, bg="#f8f9fa")
        titoli_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(15, 10))

        self.titolo_grafico = tk.Label(titoli_frame, text="Seleziona una stazione",
                                       font=("Arial", 16, "bold"), fg="#2c3e50", bg="#f8f9fa")
        self.titolo_grafico.pack(anchor=tk.W)

        self.ultimo_aggiornamento = tk.Label(titoli_frame, text="Ultimo aggiornamento: --",
                                            font=("Arial", 11), fg="#95a5a6", bg="#f8f9fa")
        self.ultimo_aggiornamento.pack(anchor=tk.W)

        # Livelli (senza pulsante)
        self.livelli_allerta = tk.Label(titoli_frame, text="Livelli allerta: --",
                                       font=("Arial", 11), fg="#95a5a6", bg="#f8f9fa")
        self.livelli_allerta.pack(anchor=tk.W, pady=(0, 5))

        self.graph_frame = tk.Frame(graph_container, bg="white")
        self.graph_frame.pack(fill=tk.BOTH, expand=True, padx=15, pady=(0, 20))

    def aggiorna_lista_stazioni(self):
        """🔄 Aggiorna lista stazioni con colori e selezione"""
        self.lista_stazioni.delete(0, tk.END)
        self.mappa_lista_stazioni = {}  # 🔧 Reset mappa

        if not self.stazioni:
            self.lista_stazioni.insert(tk.END, "Nessuna stazione trovata")
            return

        selezione_corrente = self.lista_stazioni.curselection()
        nome_selezionato = None
        if selezione_corrente:
            idx = selezione_corrente[0]
            nome_selezionato = self.lista_stazioni.get(idx).replace("▶ ", "").replace("  ", "").strip()

        for i, nome in enumerate(self.stazioni):
            self.stazioni_colori[nome] = self.calcola_colore_allerta(nome)
            marker = "▶ " if nome == self.current_stazione else "  "
            colore_sfondo = self.stazioni_colori.get(nome, "#f0f0f0")

            self.lista_stazioni.insert(tk.END, f"{marker}{nome}")
            self.lista_stazioni.itemconfig(i, {
                'bg': colore_sfondo,
                'fg': 'black',
                'selectforeground': 'black'
            })
            self.mappa_lista_stazioni[i] = nome  # 🔧 Salva corrispondenza

        if nome_selezionato and nome_selezionato in self.stazioni:
            try:
                idx = self.stazioni.index(nome_selezionato)
                self.lista_stazioni.selection_set(idx)
                self.lista_stazioni.see(idx)
            except ValueError:
                pass

    def filtra_stazioni(self, event=None):
        query = self.entry_ricerca.get().lower().strip()
        self.lista_stazioni.delete(0, tk.END)

        if not query:
            self.aggiorna_lista_stazioni()
            return

        stazioni_filtrate = [nome for nome in self.stazioni if query in nome.lower()]

        if not stazioni_filtrate:
            self.lista_stazioni.insert(tk.END, "Nessuna stazione trovata")
        else:
            for i, nome in enumerate(stazioni_filtrate):
                colore = self.calcola_colore_allerta(nome)
                marker = "▶ " if nome == self.current_stazione else "  "
                self.lista_stazioni.insert(tk.END, f"{marker}{nome}")
                self.lista_stazioni.itemconfig(i, {'bg': colore, 'fg': 'black', 'selectforeground': 'black'})

    def pulisci_ricerca(self):
        self.entry_ricerca.delete(0, tk.END)
        self.aggiorna_lista_stazioni()
        self.entry_ricerca.focus_set()

    def avvia_auto_refresh(self):
        """🚀 Auto-refresh CON ANIMAZIONE clessidra ogni 10 min"""
        def auto_refresh():
            self.pulsante_refresh.config(state='disabled')
            self.avvia_animazione_clessidra()
            
            # Esegui refresh in thread
            def refresh_thread():
                esegui_refresh_dati()
                self.root.after(3000, self.carica_stazioni_da_cartella)
                self.root.after(0, self.ferma_animazione_auto)
            
            threading.Thread(target=refresh_thread, daemon=True).start()
            self.auto_refresh_id = self.root.after(600000, auto_refresh)  # 10 minuti

        self.auto_refresh_id = self.root.after(600000, auto_refresh)

    def avvia_refresh_dati(self):
        """🔄 Refresh manuale CON animazione"""
        self.pulsante_refresh.config(state='disabled')
        self.avvia_animazione_clessidra()

        def avvia_processo():
            try:
                esegui_refresh_dati()
                self.root.after(3000, self.carica_stazioni_da_cartella)
            except Exception:
                self.root.after(0, lambda: messagebox.showerror("Errore", "Impossibile aggiornare i dati"))
            self.root.after(0, self.ferma_animazione_10s)

        threading.Thread(target=avvia_processo, daemon=True).start()

    def avvia_animazione_clessidra(self):
        """⏳ Avvia animazione clessidra (10 secondi)"""
        self.clessidra_frame = 0
        self.animazione_id = self.root.after(200, self.aggiorna_clessidra)
        # self.root.after(10000, self.ferma_animazione_10s)  # ← Rimosso: il thread chiama già ferma_animazione

    def aggiorna_clessidra(self):
        """🔄 Aggiorna frame animazione"""
        clessidre = ["⏳", "⌛", "⏳", "⌛"]
        testo = f"{clessidre[self.clessidra_frame % 4]} Aggiornamento dati"
        self.pulsante_refresh.config(text=testo)
        self.clessidra_frame += 1
        self.animazione_id = self.root.after(200, self.aggiorna_clessidra)

    def ferma_animazione_10s(self):
        """✅ Ferma animazione dopo 10s (manuale)"""
        if hasattr(self, 'animazione_id'):
            self.root.after_cancel(self.animazione_id)
        self.pulsante_refresh.config(text="✅ Dati aggiornati", state='normal')
        self.root.after(3000, lambda: self.pulsante_refresh.config(text="⏳ Aggiornamento dati"))

    def ferma_animazione_auto(self):
        """✅ Ferma animazione auto-refresh"""
        if hasattr(self, 'animazione_id'):
            self.root.after_cancel(self.animazione_id)
        self.pulsante_refresh.config(text="✅ Auto-update", state='normal')
        self.root.after(2000, lambda: self.pulsante_refresh.config(text="⏳ Aggiornamento dati"))

    def on_stazione_select(self, event):
        sel = self.lista_stazioni.curselection()
        if sel:
            idx = sel[0]
            nome_visualizzato = self.lista_stazioni.get(idx)
            nome = nome_visualizzato.replace("▶ ", "").replace("  ", "").strip()

            # 🔍 Trova corrispondenza esatta
            for nome_reale in self.stazioni:
                if nome_reale.strip() == nome:
                    if nome_reale in self.stazioni:
                        self.avvia_graph(nome_reale)
                        break

    def apri_prima_stazione(self):
        if self.stazioni:
            self.avvia_graph(self.stazioni[0])

    def carica_dati_stazione(self, nome_stazione):
        cartella = "Stazioni"
        nome_file = "".join(c for c in nome_stazione if c.isalnum() or c in (' ', '-', '_')).rstrip()
        nome_file = nome_file.replace(' ', '_')[:50] + ".json"
        file_path = os.path.join(cartella, nome_file)

        if not os.path.exists(file_path):
            raise FileNotFoundError(f"File non trovato: {file_path}")

        with open(file_path, 'r', encoding='utf-8') as f:
            dati_stazione = json.load(f)

        dati_api = dati_stazione.get('dati_api', {})
        data_list = dati_api.get('data', [])

        if not data_list:
            raise ValueError("Nessun dato 'data' nel JSON")

        data_list = [item for item in data_list if item.get("tipo") == "LIDRO"]

        if not data_list:
            raise ValueError("Nessun dato di tipo 'LIDRO' trovato nel JSON")

        return dati_stazione, data_list

    def prepara_serie(self, data_list):
        tempi, valori = [], []
        for item in data_list:
            try:
                t = datetime.fromisoformat(item["dataora"])
                v = float(item["valore"])
                tempi.append(t)
                valori.append(v)
            except:
                continue
        return tempi, valori

    def on_mouse_move(self, event):
        """📍 Mostra tooltip con livello e data al passaggio del mouse"""
        if event.inaxes != self.ax or len(self.tempi) == 0:
            if self.annotation and self.annotation.get_visible():
                self.annotation.set_visible(False)
                self.canvas.draw_idle()
            return

        x_mouse = event.xdata
        if x_mouse is None:
            return

        try:
            from matplotlib.dates import date2num
            x_data_num = date2num(self.tempi)
            idx = min(range(len(x_data_num)), key=lambda i: abs(x_data_num[i] - x_mouse))

            x_point = self.tempi[idx]
            y_point = self.valori[idx]

            data_formattata = x_point.strftime('%d/%m/%Y %H:%M')
            testo = f'{data_formattata}\nLivello: {y_point:.2f} m'

            if self.annotation is None:
                self.annotation = self.ax.annotate(
                    testo,
                    xy=(date2num(x_point), y_point),
                    xytext=(0, 0),
                    textcoords='offset points',
                    bbox=dict(boxstyle='round,pad=0.8', fc='#ffffff', ec='#2c5aa0', lw=2, alpha=0.95),
                    fontsize=10,
                    fontweight='bold',
                    color='#2c3e50',
                    zorder=1000
                )
            else:
                self.annotation.set_text(testo)
                self.annotation.xy = (date2num(x_point), y_point)

            xlim = self.ax.get_xlim()
            ylim = self.ax.get_ylim()
            x_range = xlim[1] - xlim[0]
            y_range = ylim[1] - ylim[0]

            x_rel = (date2num(x_point) - xlim[0]) / x_range
            y_rel = (y_point - ylim[0]) / y_range

            offset_x = -80 if x_rel > 0.7 else 80 if x_rel < 0.3 else 15
            offset_y = -60 if y_rel > 0.7 else 60 if y_rel < 0.3 else 15

            self.annotation.set_position((offset_x, offset_y))
            self.annotation.set_visible(True)
            self.canvas.draw_idle()
        except Exception:
            pass

    def avvia_graph(self, nome_stazione):
        try:
            self.current_stazione = nome_stazione
            dati_stazione, data_list = self.carica_dati_stazione(nome_stazione)

            # Abilita pulsante modifica livelli quando c'è una stazione selezionata
            self.pulsante_modifica_livelli.config(state='normal')

            colore_allerta = self.calcola_colore_allerta(nome_stazione)
            colore_grafico = "#2980b9" if colore_allerta == "#28a745" else colore_allerta

            self.titolo_grafico.config(text=f"{nome_stazione}", fg=colore_grafico)

            timestamp_agg = data_list[0].get('aggiornamento') if data_list else None
            if timestamp_agg:
                try:
                    data_agg = datetime.fromisoformat(timestamp_agg.replace('Z', '+00:00')[:19])
                    self.ultimo_aggiornamento.config(text=f"Ultimo aggiornamento: {data_agg.strftime('%d/%m/%Y %H:%M')}", fg="#27ae60")
                except:
                    self.ultimo_aggiornamento.config(text=f"Aggiornamento: {timestamp_agg[:19]}", fg="#f39c12")
            else:
                self.ultimo_aggiornamento.config(text="Nessun dato aggiornamento", fg="#e74c3c")

            livelli_testo = "Livelli allerta: --"
            colore_livelli = "#95a5a6"

            try:
                livello_attuale = self.get_livello_corrente(nome_stazione)
                livelli_ordinaria = dati_stazione.get('livello_ordinaria')
                livelli_moderata = dati_stazione.get('livello_moderata')
                livelli_elevata = dati_stazione.get('livello_elevata')

                livelli_lista = [f"Attuale: {livello_attuale} m"]
                if livelli_ordinaria is not None: livelli_lista.append(f"Allerta Ordinaria: {livelli_ordinaria} m")
                if livelli_moderata is not None: livelli_lista.append(f"Allerta Moderata: {livelli_moderata} m")
                if livelli_elevata is not None: livelli_lista.append(f"Allerta Elevata: {livelli_elevata} m")

                livelli_testo = f"Livello {' | '.join(livelli_lista)}"
                colore_livelli = "#000000"
            except:
                pass

            self.livelli_allerta.config(text=livelli_testo, fg=colore_livelli)

            for widget in self.graph_frame.winfo_children():
                widget.destroy()

            self.tempi, self.valori = self.prepara_serie(data_list)

            if len(self.tempi) == 0:
                tk.Label(self.graph_frame, text="Nessun dato valido", font=("Arial", 16),
                        fg="#e74c3c", bg="white").pack(expand=True)
                return

            self.fig = Figure(figsize=(12, 6.5), dpi=100, facecolor='white')
            self.ax = self.fig.add_subplot(111)

            self.linea, = self.ax.plot(self.tempi, self.valori, '-', linewidth=3, color=colore_grafico, alpha=0.9)

            self.ax.set_xlabel("Tempo", fontsize=13, color='#34495e')
            self.ax.set_ylabel(f"Livello [{data_list[0].get('unitnm', 'm')}]", fontsize=13, color='#34495e')
            self.ax.tick_params(axis='x', rotation=35)
            self.ax.grid(True, alpha=0.3)
            self.ax.xaxis.set_major_formatter(DateFormatter('%d/%m\n%H:%M'))
            self.fig.autofmt_xdate()

            self.annotation = None

            self.canvas = FigureCanvasTkAgg(self.fig, master=self.graph_frame)
            self.canvas.draw()
            self.canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)
            self.canvas.mpl_connect('motion_notify_event', self.on_mouse_move)

            toolbar = NavigationToolbar2Tk(self.canvas, self.graph_frame)
            toolbar.configure(background='white')
            toolbar.pack(fill=tk.X, pady=(0, 5))

            self.aggiorna_lista_stazioni()
            self.root.update_idletasks()

        except Exception as e:
            messagebox.showerror("Errore", f"Caricamento fallito '{nome_stazione}':\n{str(e)}")

    def apri_aggiungi_stazione(self):
        """➕ Apri finestra aggiungi stazione"""
        AggiungiStazione(parent_app=self)

    def apri_modifica_livelli(self):
        """⚙️ Apri finestra modifica livelli per stazione corrente"""
        if not self.current_stazione:
            messagebox.showwarning("Attenzione", "Seleziona prima una stazione!")
            return
        ModificaLivelli(nome_stazione=self.current_stazione, parent_app=self)

    def salva_report(self):
        """💾 Apri finestra salva report"""
        SalvaReportApp(parent_app=self)

    def rimuovi_stazione(self):
        """🗑️ Rimuovi stazione CORRENTE contrassegnata dalla spunta ▶"""
        if not self.current_stazione:
            messagebox.showwarning("Attenzione", "Seleziona prima una stazione da rimuovere!")
            return

        risposta = messagebox.askyesno("🗑️ Conferma Rimozione",
                                      f"Sei sicuro di voler eliminare la stazione:\n\n"
                                      f"📍 {self.current_stazione}\n\n"
                                      f"⚠️ Questa azione è irreversibile!")
        if not risposta:
            return

        try:
            file_path = self.stazioni_files.get(self.current_stazione)
            if file_path and os.path.exists(file_path):
                os.remove(file_path)
                messagebox.showinfo("✅ Rimosso!",
                                  f"Stazione rimossa con successo:\n{self.current_stazione}")
                self.current_stazione = None
                self.pulsante_modifica_livelli.config(state='disabled')
                
                # Pulisci grafico
                for widget in self.graph_frame.winfo_children():
                    widget.destroy()
                
                self.carica_stazioni_da_cartella()
                self.apri_prima_stazione()
            else:
                messagebox.showerror("Errore", "File della stazione non trovato!")
        except Exception:
            messagebox.showerror("Errore", "Impossibile rimuovere la stazione!")

    def info(self):
        """ℹ️ Mostra informazioni sull'applicazione"""
        messagebox.showinfo("ℹ️ Info IdroMonitor",
                          "IdroMonitor - Sistema di Monitoraggio Idrometrico\n\n"
                          "Versione: 1.0\n"
                          "Protezione Civile di Pernumia\n\n"
                          "Funzionalità:\n"
                          "• Monitoraggio livelli idrometrici in tempo reale\n"
                          "• Sistema di allerta con codici colore\n"
                          "• Grafici interattivi\n"
                          "• Generazione report PDF\n"
                          "• Aggiornamento automatico dati ogni 10 minuti\n\n"
                          "Dati forniti da Meteo Idro Nivo ARPAV\n"
                          "https://www.arpa.veneto.it/dati-ambientali/dati-in-diretta/meteo-idro-nivo\n\n"
                          "IdroMonitor è un programma solo a scopo infromativo di libera diffusione\n"
                          "Non utilizzabile per scopi commerciali\n\n"
                          "Copyright (C) 2026 Giulio Bojan\nGNU General Public License\nhttps://github.com/GiulioBj/Idromonitor.git")


# ==================== MAIN ====================
if __name__ == "__main__":
    root = tk.Tk()
    app = ProtezioneCivileApp(root)
    root.mainloop()
