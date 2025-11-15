"""
Éditeur de sorts pour WakSOS - Interface graphique pour remplir iop_combos.json
"""
import tkinter as tk
from tkinter import filedialog, messagebox, ttk
import json
import os
import shutil
from pathlib import Path


class SortEditor:
    """Interface graphique pour éditer les sorts dans iop_combos.json"""
    
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("WakSOS - Éditeur de sorts Iop")
        self.root.geometry("700x600")
        
        self.combos_file = "iop_combos.json"
        self.assets_dir = "assets/iop"
        self.data = self.load_data()
        
        self.create_ui()
        self.refresh_sort_list()
    
    def load_data(self):
        """Charge les données depuis iop_combos.json"""
        if os.path.exists(self.combos_file):
            try:
                with open(self.combos_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception as e:
                messagebox.showerror("Erreur", f"Erreur lors du chargement de {self.combos_file}:\n{e}")
                return {"sorts": {}, "combos": {}}
        else:
            # Créer la structure par défaut
            default_data = {
                "sorts": {},
                "combos": {
                    "combo_1": {"nom": "Vol de Vie", "sequence": [{"PM": 1}, {"PA": 3}, {"PA": 3}]},
                    "combo_2": {"nom": "Poussée", "sequence": [{"PA": 1}, {"PA": 1}, {"PA": 2}]},
                    "combo_3": {"nom": "Préparation", "sequence": [{"PM": 1}, {"PM": 1}, {"PW": 1}]},
                    "combo_4": {"nom": "Dommages +", "sequence": [{"PA": 2}, {"PA": 1}, {"PM": 1}]},
                    "combo_5": {"nom": "Combo PA", "sequence": [{"PW": 1}, {"PA": 3}, {"PW": 1}, {"PA": 1}]}
                }
            }
            self.save_data(default_data)
            return default_data
    
    def save_data(self, data=None):
        """Sauvegarde les données dans iop_combos.json"""
        if data is None:
            data = self.data
        
        try:
            with open(self.combos_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            return True
        except Exception as e:
            messagebox.showerror("Erreur", f"Erreur lors de la sauvegarde:\n{e}")
            return False
    
    def create_ui(self):
        """Crée l'interface utilisateur"""
        # Frame principal
        main_frame = tk.Frame(self.root, padx=10, pady=10)
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # Titre
        title_label = tk.Label(
            main_frame,
            text="Éditeur de sorts Iop",
            font=('Arial', 16, 'bold')
        )
        title_label.pack(pady=10)
        
        # Frame pour l'ajout/édition de sort
        edit_frame = tk.LabelFrame(main_frame, text="Ajouter/Modifier un sort", padx=10, pady=10)
        edit_frame.pack(fill=tk.X, pady=10)
        
        # Nom du sort
        tk.Label(edit_frame, text="Nom du sort:").grid(row=0, column=0, sticky='w', pady=5)
        self.sort_name_entry = tk.Entry(edit_frame, width=30)
        self.sort_name_entry.grid(row=0, column=1, columnspan=2, sticky='ew', pady=5, padx=5)
        
        # Icône du sort
        tk.Label(edit_frame, text="Icône:").grid(row=1, column=0, sticky='w', pady=5)
        self.icon_path_var = tk.StringVar()
        icon_frame = tk.Frame(edit_frame)
        icon_frame.grid(row=1, column=1, columnspan=2, sticky='ew', pady=5, padx=5)
        
        self.icon_path_entry = tk.Entry(icon_frame, textvariable=self.icon_path_var, width=25)
        self.icon_path_entry.pack(side=tk.LEFT, fill=tk.X, expand=True)
        
        browse_btn = tk.Button(
            icon_frame,
            text="Parcourir...",
            command=self.browse_icon
        )
        browse_btn.pack(side=tk.LEFT, padx=5)
        
        # Coûts
        costs_frame = tk.LabelFrame(edit_frame, text="Coûts", padx=10, pady=10)
        costs_frame.grid(row=2, column=0, columnspan=3, sticky='ew', pady=10)
        
        # PA
        tk.Label(costs_frame, text="PA:").grid(row=0, column=0, padx=5)
        self.pa_var = tk.StringVar(value="0")
        pa_spinbox = tk.Spinbox(costs_frame, from_=0, to=10, textvariable=self.pa_var, width=5)
        pa_spinbox.grid(row=0, column=1, padx=5)
        
        # PM
        tk.Label(costs_frame, text="PM:").grid(row=0, column=2, padx=5)
        self.pm_var = tk.StringVar(value="0")
        pm_spinbox = tk.Spinbox(costs_frame, from_=0, to=10, textvariable=self.pm_var, width=5)
        pm_spinbox.grid(row=0, column=3, padx=5)
        
        # PW
        tk.Label(costs_frame, text="PW:").grid(row=0, column=4, padx=5)
        self.pw_var = tk.StringVar(value="0")
        pw_spinbox = tk.Spinbox(costs_frame, from_=0, to=10, textvariable=self.pw_var, width=5)
        pw_spinbox.grid(row=0, column=5, padx=5)
        
        # Boutons
        buttons_frame = tk.Frame(edit_frame)
        buttons_frame.grid(row=3, column=0, columnspan=3, pady=10)
        
        add_btn = tk.Button(
            buttons_frame,
            text="Ajouter/Modifier",
            command=self.add_sort,
            bg='#4CAF50',
            fg='white',
            width=15
        )
        add_btn.pack(side=tk.LEFT, padx=5)
        
        clear_btn = tk.Button(
            buttons_frame,
            text="Effacer",
            command=self.clear_form,
            width=15
        )
        clear_btn.pack(side=tk.LEFT, padx=5)
        
        # Liste des sorts existants
        list_frame = tk.LabelFrame(main_frame, text="Sorts existants", padx=10, pady=10)
        list_frame.pack(fill=tk.BOTH, expand=True, pady=10)
        
        # Treeview pour afficher les sorts
        columns = ("Nom", "Icône", "PA", "PM", "PW")
        self.sort_tree = ttk.Treeview(list_frame, columns=columns, show="headings", height=10)
        
        for col in columns:
            self.sort_tree.heading(col, text=col)
            self.sort_tree.column(col, width=120)
        
        # Scrollbar
        scrollbar = ttk.Scrollbar(list_frame, orient=tk.VERTICAL, command=self.sort_tree.yview)
        self.sort_tree.configure(yscrollcommand=scrollbar.set)
        
        self.sort_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        # Boutons pour la liste
        list_buttons_frame = tk.Frame(list_frame)
        list_buttons_frame.pack(fill=tk.X, pady=5)
        
        edit_btn = tk.Button(
            list_buttons_frame,
            text="Modifier",
            command=self.edit_selected_sort,
            width=15
        )
        edit_btn.pack(side=tk.LEFT, padx=5)
        
        delete_btn = tk.Button(
            list_buttons_frame,
            text="Supprimer",
            command=self.delete_selected_sort,
            bg='#f44336',
            fg='white',
            width=15
        )
        delete_btn.pack(side=tk.LEFT, padx=5)
        
        # Bind double-click pour modifier
        self.sort_tree.bind('<Double-1>', lambda e: self.edit_selected_sort())
    
    def browse_icon(self):
        """Ouvre un dialogue pour sélectionner une image"""
        file_path = filedialog.askopenfilename(
            title="Sélectionner l'icône du sort",
            filetypes=[
                ("Images", "*.png *.jpg *.jpeg *.gif *.bmp"),
                ("PNG", "*.png"),
                ("Tous les fichiers", "*.*")
            ]
        )
        
        if file_path:
            self.icon_path_var.set(file_path)
    
    def clear_form(self):
        """Efface le formulaire"""
        self.sort_name_entry.delete(0, tk.END)
        self.icon_path_var.set("")
        self.pa_var.set("0")
        self.pm_var.set("0")
        self.pw_var.set("0")
    
    def add_sort(self):
        """Ajoute ou modifie un sort"""
        sort_name = self.sort_name_entry.get().strip()
        icon_path = self.icon_path_var.get().strip()
        
        if not sort_name:
            messagebox.showwarning("Attention", "Veuillez entrer un nom de sort")
            return
        
        # Lire les coûts
        try:
            pa = int(self.pa_var.get())
            pm = int(self.pm_var.get())
            pw = int(self.pw_var.get())
        except ValueError:
            messagebox.showerror("Erreur", "Les coûts doivent être des nombres entiers")
            return
        
        if pa == 0 and pm == 0 and pw == 0:
            messagebox.showwarning("Attention", "Au moins un coût doit être supérieur à 0")
            return
        
        # Construire le dictionnaire de coûts
        cout = {}
        if pa > 0:
            cout["PA"] = pa
        if pm > 0:
            cout["PM"] = pm
        if pw > 0:
            cout["PW"] = pw
        
        # Gérer l'icône
        icon_filename = None
        if icon_path:
            if os.path.exists(icon_path):
                # Copier l'icône dans assets/iop/
                if not os.path.exists(self.assets_dir):
                    os.makedirs(self.assets_dir)
                
                # Nom du fichier basé sur le nom du sort
                icon_filename = f"{sort_name}.png"
                dest_path = os.path.join(self.assets_dir, icon_filename)
                
                try:
                    # Copier le fichier
                    shutil.copy2(icon_path, dest_path)
                    print(f"✓ Icône copiée: {icon_path} → {dest_path}")
                except Exception as e:
                    messagebox.showerror("Erreur", f"Erreur lors de la copie de l'icône:\n{e}")
                    return
            else:
                # Si le chemin n'existe pas, utiliser juste le nom du fichier
                icon_filename = os.path.basename(icon_path)
        
        # Ajouter/modifier le sort
        if "sorts" not in self.data:
            self.data["sorts"] = {}
        
        self.data["sorts"][sort_name] = {
            "cout": cout,
            "icone": icon_filename or f"{sort_name}.png"
        }
        
        # Sauvegarder
        if self.save_data():
            messagebox.showinfo("Succès", f"Sort '{sort_name}' ajouté/modifié avec succès!")
            self.clear_form()
            self.refresh_sort_list()
    
    def refresh_sort_list(self):
        """Rafraîchit la liste des sorts"""
        # Effacer la liste actuelle
        for item in self.sort_tree.get_children():
            self.sort_tree.delete(item)
        
        # Ajouter les sorts
        if "sorts" in self.data:
            for sort_name, sort_data in self.data["sorts"].items():
                cout = sort_data.get("cout", {})
                icon = sort_data.get("icone", "")
                
                self.sort_tree.insert(
                    "",
                    tk.END,
                    values=(
                        sort_name,
                        icon,
                        cout.get("PA", 0),
                        cout.get("PM", 0),
                        cout.get("PW", 0)
                    )
                )
    
    def edit_selected_sort(self):
        """Modifie le sort sélectionné"""
        selection = self.sort_tree.selection()
        if not selection:
            messagebox.showwarning("Attention", "Veuillez sélectionner un sort à modifier")
            return
        
        item = self.sort_tree.item(selection[0])
        values = item['values']
        sort_name = values[0]
        
        # Charger les données du sort
        if sort_name in self.data.get("sorts", {}):
            sort_data = self.data["sorts"][sort_name]
            cout = sort_data.get("cout", {})
            icon = sort_data.get("icone", "")
            
            # Remplir le formulaire
            self.clear_form()
            self.sort_name_entry.insert(0, sort_name)
            
            # Chercher l'icône dans assets/iop/
            icon_path = os.path.join(self.assets_dir, icon)
            if os.path.exists(icon_path):
                self.icon_path_var.set(icon_path)
            else:
                self.icon_path_var.set(icon)
            
            self.pa_var.set(str(cout.get("PA", 0)))
            self.pm_var.set(str(cout.get("PM", 0)))
            self.pw_var.set(str(cout.get("PW", 0)))
    
    def delete_selected_sort(self):
        """Supprime le sort sélectionné"""
        selection = self.sort_tree.selection()
        if not selection:
            messagebox.showwarning("Attention", "Veuillez sélectionner un sort à supprimer")
            return
        
        item = self.sort_tree.item(selection[0])
        sort_name = item['values'][0]
        
        # Confirmer la suppression
        if messagebox.askyesno("Confirmation", f"Êtes-vous sûr de vouloir supprimer le sort '{sort_name}' ?"):
            if sort_name in self.data.get("sorts", {}):
                del self.data["sorts"][sort_name]
                if self.save_data():
                    messagebox.showinfo("Succès", f"Sort '{sort_name}' supprimé avec succès!")
                    self.refresh_sort_list()
    
    def run(self):
        """Lance l'interface"""
        self.root.mainloop()


if __name__ == "__main__":
    app = SortEditor()
    app.run()





