#!/usr/bin/python3
# -*- coding: utf-8 -*-

"""
Parse Foxwell Tech cbf file into csv + GUI viewer
"""

import sys
import os
import csv
import tkinter as tk
from tkinter import ttk, filedialog, messagebox


# ===================== PARSER (UNCHANGED) ===================== #
def parse_cbf(cbf):
    headings = []
    header = []
    data = []
    errors = []
    flen = len(cbf)
    fp = 0

    def get_null_terminated_string(current_fp):
        res = b''
        while current_fp < flen and cbf[current_fp] != 0:
            res += bytes([cbf[current_fp]])
            current_fp += 1
        return res.decode('latin-1', errors='replace'), current_fp

    if fp < flen:
        ft, fp = get_null_terminated_string(fp)
        headings.append(ft)
        fp += 1
    
    if fp < flen:
        ft, fp = get_null_terminated_string(fp)
        headings.append(ft)
        fp += 1

    fp += 8 
    
    if fp < flen:
        ft, fp = get_null_terminated_string(fp)
        headings.append(ft)
        fp += 1

    if fp + 2 > flen:
        errors.append("Unexpected EOF before field count")
        return headings, header, data, errors

    num_fields = cbf[fp] + 256 * cbf[fp+1]
    fp += 2

    fn = 0
    ft = ''
    nz = 0
    while fn < num_fields:
        if fp >= flen:
            errors.append("end of file during header parse")
            break
        
        byte = cbf[fp]
        if byte == 0 and nz > 0:
            ft = ft.replace("\xb0", "deg ").rstrip(' ')
            if len(ft) > 0:
                header.append(ft)
                fn += 1
            fp += 1
            ft = ''
            nz = 0
        elif byte == 6:
            fp += 10 
        elif byte != 0:
            if byte > 31:
                ft += chr(byte)
            fp += 1
        else:
            nz += 1
            if len(ft) > 0:
                ft += ' '
            fp += 1
    
    if errors:
        return headings, header, data, errors
    
    read_records = 0
    expected_records = -1
    while fp < flen:
        fn = 0
        ft = ''
        dataline = []
        while fn < num_fields:
            if fp >= flen:
                errors.append("end of file during data parse")
                break
            if cbf[fp] == 0:
                dataline.append(ft)
                fp += 1
                fn += 1
                ft = ''
            else:
                ft += chr(cbf[fp])
                fp += 1
        
        if fn == num_fields:
            data.append(dataline)
            read_records += 1
            if fp + 7 < flen:
                if cbf[fp+4:fp+8] == b'\xaa\x55\x33\x11':
                    expected_records = cbf[fp] + 256*cbf[fp+1] + 65536*cbf[fp+2] + 16777216*cbf[fp+3]
                    break
                    
    if expected_records != -1 and read_records != expected_records:
        errors.append(f"read {read_records} records but expected {expected_records}")
    
    return headings, header, data, errors


# ===================== CSV EXPORT ===================== #
def save_to_csv(output_filename, header, data):
    try:
        with open(output_filename, 'w', newline='', encoding='utf-8') as csvfile:
            writer = csv.writer(csvfile)
            writer.writerow(header)
            writer.writerows(data)
        messagebox.showinfo("Success", f"Saved to:\n{output_filename}")
    except Exception as e:
        messagebox.showerror("Error", str(e))


# ===================== GUI ===================== #
class PIDViewer:
    def __init__(self, root, header, data):
        self.root = root
        self.header = header
        self.data = data

        self.root.title("PID Viewer")
        self.root.geometry("900x500")

        # Table
        self.tree = ttk.Treeview(root, columns=header, show="headings")

        for col in header:
            self.tree.heading(col, text=col)
            self.tree.column(col, anchor="center", width=120)

        # Insert data
        for row in data:
            self.tree.insert("", "end", values=row)

        # Scrollbars
        scrollbar_y = ttk.Scrollbar(root, orient="vertical", command=self.tree.yview)
        scrollbar_x = ttk.Scrollbar(root, orient="horizontal", command=self.tree.xview)

        self.tree.configure(yscroll=scrollbar_y.set, xscroll=scrollbar_x.set)

        self.tree.pack(fill=tk.BOTH, expand=True)
        scrollbar_y.pack(side="right", fill="y")
        scrollbar_x.pack(side="bottom", fill="x")

        # Export button
        btn_frame = tk.Frame(root)
        btn_frame.pack(pady=10)

        export_btn = tk.Button(btn_frame, text="Export to CSV", command=self.export_csv)
        export_btn.pack()

    def export_csv(self):
        file_path = filedialog.asksaveasfilename(
            defaultextension=".csv",
            filetypes=[("CSV files", "*.csv")]
        )
        if file_path:
            save_to_csv(file_path, self.header, self.data)


# ===================== MAIN ===================== #
if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python3 script.py <filename.cbf>")
        sys.exit(1)
        
    input_path = sys.argv[1]

    try:
        with open(input_path, "rb") as f_in:
            cbf_data = f_in.read()
    except FileNotFoundError:
        print(f"Error: File {input_path} not found.")
        sys.exit(1)

    headings, header, data, errors = parse_cbf(cbf_data)

    # Terminal output (optional)
    for l in headings:
        print(f"Heading: {l}")

    if errors:
        for l in errors:
            print("Error:", l)

    if not header:
        print("No data found.")
        sys.exit(1)

    # ===================== LAUNCH GUI ===================== #
    root = tk.Tk()
    app = PIDViewer(root, header, data)
    root.mainloop()
