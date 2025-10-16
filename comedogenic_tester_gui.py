#!/usr/bin/env python3
"""Comedogenic Tester GUI (text input window)
Reads comedogenic_db.xlsx from the same folder and presents a simple text input window.
Paste comma-separated INCI ingredients, choose leave-on checkbox, choose formulation type, then click Analyze.
Results are shown on-screen (no saving required).

To run: double-click with Python installed, or run in terminal:
    python comedogenic_tester_gui.py
"""
import tkinter as tk
from tkinter import ttk, scrolledtext, messagebox
import pandas as pd
import math, os, re

DB_FILE = os.path.join(os.path.dirname(__file__), 'comedogenic_db.xlsx')

# Load DB
try:
    ING_DB = pd.read_excel(DB_FILE)
except Exception as e:
    ING_DB = pd.DataFrame(columns=['name','score','synonyms','category','notes'])

# simple lookup map
LOOKUP = {row['name'].strip().lower(): row for _, row in ING_DB.iterrows()}

# helper functions
def normalize_ingredient(name):
    s = re.sub(r"\([^)]*\)", '', name)
    s = re.sub(r"[^a-zA-Z0-9 ]+", ' ', s).strip().lower()
    return s

def parse_ingredients(text):
    parts = re.split(r"[,;\n]", text)
    parsed = [p.strip() for p in parts if p.strip()]
    return parsed

def rank_weight(index, total):
    if total <= 1:
        return 1.0
    frac = index / float(total - 1)
    weight = 1.0 * (0.08 ** frac)
    return weight

def concentration_weights(n):
    raw = [rank_weight(i, n) for i in range(n)]
    s = sum(raw)
    return [r / s for r in raw]

def lookup_info(name):
    key = normalize_ingredient(name)
    if key in LOOKUP:
        row = LOOKUP[key]
        return {'name': row['name'], 'score': float(row['score']), 'notes': row.get('notes',''), 'category': row.get('category','')}
    # try partial match
    for k in LOOKUP:
        if k in key:
            row = LOOKUP[k]
            return {'name': row['name'], 'score': float(row['score']), 'notes': row.get('notes',''), 'category': row.get('category','')}
    return {'name': name, 'score': 0.0, 'notes': 'Unknown (assumed low)', 'category':'unknown'}

def analyze(ing_text, leave_on, formulation):
    ingredients = parse_ingredients(ing_text)
    if not ingredients:
        return None
    n = len(ingredients)
    weights = concentration_weights(n)
    breakdown = []
    weighted_sum = 0.0
    occlusive_count = 0
    high_risk = []
    for i, ingr in enumerate(ingredients):
        info = lookup_info(ingr)
        base = info['score']
        w = weights[i]
        contrib = base * w
        breakdown.append((info['name'], base, round(w,4), round(contrib,4), info['notes']))
        weighted_sum += contrib
        if info['category'] in ('occlusive','butter','wax') or base >= 4:
            occlusive_count += 1
        if base >= 4:
            high_risk.append(info['name'])
    baseline = weighted_sum
    modifier = 1.0
    notes = []
    if leave_on:
        modifier *= 1.15
        notes.append('Leave-on -> +15%')
    if formulation.lower() in ('anhydrous','oil only'):
        modifier *= 1.10
        notes.append('Anhydrous -> +10%')
    if formulation.lower() in ('w/o','water-in-oil'):
        modifier *= 1.08
        notes.append('W/O emulsion -> +8%')
    if occlusive_count >= 2:
        modifier *= 1.12
        notes.append('Multiple occlusives -> +12%')
    score = baseline * modifier
    score = max(0.0, min(5.0, score))
    if score < 0.5:
        cat = 'Very Low'
    elif score < 1.5:
        cat = 'Low'
    elif score < 2.5:
        cat = 'Moderate'
    elif score < 3.5:
        cat = 'High'
    else:
        cat = 'Very High'
    return {'score': round(score,2), 'category': cat, 'baseline': round(baseline,3), 'modifier': round(modifier,3), 'notes': notes, 'breakdown': breakdown, 'high_risk': high_risk}

# GUI
root = tk.Tk()
root.title('Comedogenic Tester — Text Input (offline)')
root.geometry('800x600')

frame = ttk.Frame(root, padding=10)
frame.pack(fill='both', expand=True)

lbl = ttk.Label(frame, text='Paste INCI-style ingredient list (comma, semicolon, or newline separated):')
lbl.pack(anchor='w')

text_in = scrolledtext.ScrolledText(frame, height=8)
text_in.pack(fill='x')

controls = ttk.Frame(frame)
controls.pack(fill='x', pady=8)

leave_var = tk.BooleanVar()
chk = ttk.Checkbutton(controls, text='Leave-on product', variable=leave_var)
chk.pack(side='left')

form_label = ttk.Label(controls, text='Formulation:')
form_label.pack(side='left', padx=(10,2))
form_var = tk.StringVar(value='o/w')
form_combo = ttk.Combobox(controls, textvariable=form_var, values=['o/w','w/o','anhydrous','oil only'], width=12)
form_combo.pack(side='left')

output = scrolledtext.ScrolledText(frame, height=15)
output.pack(fill='both', expand=True)


def on_analyze():
    text = text_in.get('1.0', 'end').strip()
    leave = leave_var.get()
    form = form_var.get()
    res = analyze(text, leave, form)
    output.delete('1.0', 'end')
    if not res:
        output.insert('end', 'No ingredients provided.\n')
        return
    output.insert('end', f"Overall score (0-5): {res['score']}  — Category: {res['category']}\n")
    output.insert('end', f"Baseline: {res['baseline']}  Modifier: {res['modifier']}\n")
    if res['notes']:
        output.insert('end', 'Modifiers applied:\n')
        for n in res['notes']:
            output.insert('end', f" - {n}\n")
    output.insert('end', '\nIngredient breakdown (top -> bottom):\n')
    for b in res['breakdown']:
        output.insert('end', f" - {b[0]}: base {b[1]} * weight {b[2]} => contrib {b[3]}   ({b[4]})\n")
    if res['high_risk']:
        output.insert('end', '\nHigh-risk ingredients found:\n')
        for h in res['high_risk']:
            output.insert('end', f" - {h}\n")

btn = ttk.Button(frame, text='Analyze', command=on_analyze)
btn.pack(pady=6)

root.mainloop()
