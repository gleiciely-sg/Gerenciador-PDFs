"""
Junta a primeira página de cada PDF em um único arquivo.
Interface gráfica — basta dar duplo clique no .exe para abrir.
"""

import os
import re
import shutil
import threading
import tkinter as tk
from tkinter import filedialog, messagebox, ttk
from pypdf import PdfReader, PdfWriter


def ordenar_numerico(nome):
    numeros = re.findall(r'\d+', nome)
    return int(numeros[0]) if numeros else 0


def juntar_pdfs(pasta_entrada, arquivo_saida, log, progress, btn_iniciar):
    arquivos = [
        f for f in os.listdir(pasta_entrada)
        if f.lower().endswith(".pdf") and f != os.path.basename(arquivo_saida)
    ]

    if not arquivos:
        messagebox.showerror("Erro", f"Nenhum PDF encontrado em:\n{pasta_entrada}")
        btn_iniciar.config(state="normal")
        return

    arquivos = sorted(arquivos, key=ordenar_numerico)
    total = len(arquivos)
    log(f"📂 {total} arquivo(s) encontrado(s)\n")

    pasta_temp = os.path.join(pasta_entrada, "_temp_saida")
    os.makedirs(pasta_temp, exist_ok=True)

    contador = 1
    pdfs_temp = []

    for i, nome in enumerate(arquivos):
        caminho = os.path.join(pasta_entrada, nome)
        try:
            reader = PdfReader(caminho)

            if len(reader.pages) == 0:
                log(f"⚠️  Vazio (ignorado): {nome}")
                continue

            writer = PdfWriter()
            writer.add_page(reader.pages[0])

            temp_nome = os.path.join(pasta_temp, f"{contador}.pdf")
            with open(temp_nome, "wb") as f:
                writer.write(f)

            pdfs_temp.append(temp_nome)
            log(f"✔  {nome}")
            contador += 1

        except Exception as e:
            log(f"❌ Erro em {nome}: {e}")

        progress["value"] = int((i + 1) / total * 90)

    if not pdfs_temp:
        messagebox.showerror("Erro", "Nenhuma página foi extraída.")
        shutil.rmtree(pasta_temp, ignore_errors=True)
        btn_iniciar.config(state="normal")
        return

    writer_final = PdfWriter()
    for pdf in pdfs_temp:
        reader = PdfReader(pdf)
        writer_final.add_page(reader.pages[0])

    with open(arquivo_saida, "wb") as f:
        writer_final.write(f)

    shutil.rmtree(pasta_temp, ignore_errors=True)

    progress["value"] = 100
    log(f"\n✅ Concluído! {len(pdfs_temp)} página(s) unidas.")
    log(f"📄 Salvo em: {arquivo_saida}")
    messagebox.showinfo("Sucesso", f"Arquivo gerado com sucesso!\n\n{arquivo_saida}")
    btn_iniciar.config(state="normal")


def iniciar_thread(entrada_var, saida_var, log, progress, btn_iniciar):
    pasta = entrada_var.get().strip()
    saida = saida_var.get().strip()

    if not pasta:
        messagebox.showwarning("Atenção", "Selecione a pasta com os PDFs.")
        return
    if not os.path.isdir(pasta):
        messagebox.showerror("Erro", "Pasta não encontrada.")
        return
    if not saida:
        messagebox.showwarning("Atenção", "Defina o arquivo de saída.")
        return

    # Limpa o log e reseta a barra
    log_widget.config(state="normal")
    log_widget.delete("1.0", tk.END)
    log_widget.config(state="disabled")
    progress["value"] = 0
    btn_iniciar.config(state="disabled")

    threading.Thread(
        target=juntar_pdfs,
        args=(pasta, saida, log, progress, btn_iniciar),
        daemon=True
    ).start()


# ── Interface ────────────────────────────────────────────────────────────────

root = tk.Tk()
root.title("Juntar PDFs")
root.resizable(False, False)

PADX = 12
PADY = 6
WIDTH = 520

root.configure(padx=PADX, pady=PADX)

# Título
tk.Label(root, text="📄 Juntar PDFs", font=("Segoe UI", 14, "bold")).grid(
    row=0, column=0, columnspan=3, pady=(0, 10), sticky="w"
)

# Pasta de entrada
tk.Label(root, text="Pasta com os PDFs:", font=("Segoe UI", 9)).grid(
    row=1, column=0, columnspan=3, sticky="w"
)
entrada_var = tk.StringVar()
tk.Entry(root, textvariable=entrada_var, width=55, font=("Segoe UI", 9)).grid(
    row=2, column=0, columnspan=2, sticky="ew", pady=(0, PADY)
)
tk.Button(
    root, text="Selecionar", font=("Segoe UI", 9),
    command=lambda: entrada_var.set(filedialog.askdirectory(title="Selecione a pasta com os PDFs"))
).grid(row=2, column=2, padx=(6, 0), pady=(0, PADY))

# Arquivo de saída
tk.Label(root, text="Salvar resultado como:", font=("Segoe UI", 9)).grid(
    row=3, column=0, columnspan=3, sticky="w"
)
saida_var = tk.StringVar(value="Arquivo_Final.pdf")
tk.Entry(root, textvariable=saida_var, width=55, font=("Segoe UI", 9)).grid(
    row=4, column=0, columnspan=2, sticky="ew", pady=(0, PADY)
)
tk.Button(
    root, text="Salvar em…", font=("Segoe UI", 9),
    command=lambda: saida_var.set(
        filedialog.asksaveasfilename(
            title="Salvar resultado como",
            defaultextension=".pdf",
            filetypes=[("PDF", "*.pdf")],
            initialfile="Arquivo_Final.pdf"
        )
    )
).grid(row=4, column=2, padx=(6, 0), pady=(0, PADY))

# Log
tk.Label(root, text="Log:", font=("Segoe UI", 9)).grid(
    row=5, column=0, columnspan=3, sticky="w"
)
log_widget = tk.Text(root, height=10, width=65, font=("Consolas", 9), state="disabled", bg="#f4f4f4")
log_widget.grid(row=6, column=0, columnspan=3, pady=(0, PADY))

def log(msg):
    log_widget.config(state="normal")
    log_widget.insert(tk.END, msg + "\n")
    log_widget.see(tk.END)
    log_widget.config(state="disabled")

# Barra de progresso
progress = ttk.Progressbar(root, length=WIDTH, mode="determinate")
progress.grid(row=7, column=0, columnspan=3, pady=(0, PADY), sticky="ew")

# Botão iniciar
btn_iniciar = tk.Button(
    root, text="▶  Iniciar", font=("Segoe UI", 10, "bold"),
    bg="#0078D4", fg="white", relief="flat", padx=16, pady=6,
    command=lambda: iniciar_thread(entrada_var, saida_var, log, progress, btn_iniciar)
)
btn_iniciar.grid(row=8, column=0, columnspan=3, pady=(4, 0))

root.mainloop()
