"""
Extrai páginas específicas de cada PDF:
  - Salva arquivos individuais (mesmo nome) na pasta de saída
  - Gera um Arquivo_Final.pdf com todas as páginas extraídas unidas
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


def parse_paginas(texto, total_paginas):
    """
    Converte a string de páginas digitada pelo usuário em uma lista de índices (0-based).
    Aceita: "1", "1,3,5", "1-3", "1-3,5,7-9"
    Retorna lista ordenada e sem duplicatas, ou None se inválido.
    """
    indices = set()
    texto = texto.strip()
    if not texto:
        return None

    partes = texto.split(",")
    for parte in partes:
        parte = parte.strip()
        if "-" in parte:
            bounds = parte.split("-")
            if len(bounds) != 2:
                return None
            try:
                inicio = int(bounds[0].strip())
                fim = int(bounds[1].strip())
            except ValueError:
                return None
            if inicio < 1 or fim < inicio or fim > total_paginas:
                return None
            for n in range(inicio, fim + 1):
                indices.add(n - 1)
        else:
            try:
                n = int(parte)
            except ValueError:
                return None
            if n < 1 or n > total_paginas:
                return None
            indices.add(n - 1)

    return sorted(indices)


def processar_pdfs(pasta_entrada, pasta_saida, spec_paginas, log, progress, btn_iniciar):
    os.makedirs(pasta_saida, exist_ok=True)
    arquivo_final = os.path.join(pasta_saida, "Arquivo_Final.pdf")

    arquivos = [
        f for f in os.listdir(pasta_entrada)
        if f.lower().endswith(".pdf") and f != "Arquivo_Final.pdf"
    ]

    if not arquivos:
        messagebox.showerror("Erro", f"Nenhum PDF encontrado em:\n{pasta_entrada}")
        btn_iniciar.config(state="normal")
        return

    arquivos = sorted(arquivos, key=ordenar_numerico)
    total = len(arquivos)
    log(f"📂 {total} arquivo(s) encontrado(s)\n")

    writer_final = PdfWriter()
    arquivos_ok = 0

    for i, nome in enumerate(arquivos):
        caminho = os.path.join(pasta_entrada, nome)
        try:
            reader = PdfReader(caminho)
            total_pags = len(reader.pages)

            if total_pags == 0:
                log(f"⚠️  Vazio (ignorado): {nome}")
                progress["value"] = int((i + 1) / total * 95)
                continue

            indices = parse_paginas(spec_paginas, total_pags)
            if indices is None:
                log(f"⚠️  Páginas fora do intervalo em '{nome}' ({total_pags} pág.) — usando pág. 1")
                indices = [0]

            writer_ind = PdfWriter()
            for idx in indices:
                writer_ind.add_page(reader.pages[idx])

            saida_ind = os.path.join(pasta_saida, nome)
            with open(saida_ind, "wb") as f:
                writer_ind.write(f)

            for idx in indices:
                writer_final.add_page(reader.pages[idx])

            pags_str = spec_paginas if spec_paginas.strip() else "1"
            log(f"✔  {nome}  →  págs. [{pags_str}]  ({total_pags} pág. no original)")
            arquivos_ok += 1

        except Exception as e:
            log(f"❌ Erro em {nome}: {e}")

        progress["value"] = int((i + 1) / total * 95)

    if arquivos_ok == 0:
        messagebox.showerror("Erro", "Nenhuma página foi extraída.")
        btn_iniciar.config(state="normal")
        return

    with open(arquivo_final, "wb") as f:
        writer_final.write(f)

    progress["value"] = 100
    log(f"\n✅ Concluído!")
    log(f"   • {arquivos_ok} arquivo(s) individual(is) salvo(s) em: {pasta_saida}")
    log(f"   • Arquivo unido: {arquivo_final}")
    messagebox.showinfo(
        "Sucesso",
        f"{arquivos_ok} arquivo(s) gerado(s) individualmente.\n\nArquivo unido:\n{arquivo_final}"
    )
    btn_iniciar.config(state="normal")


def iniciar_thread(entrada_var, saida_var, paginas_var, log, progress, btn_iniciar):
    pasta_entrada = entrada_var.get().strip()
    pasta_saida = saida_var.get().strip()
    spec_paginas = paginas_var.get().strip()

    if not pasta_entrada:
        messagebox.showwarning("Atenção", "Selecione a pasta com os PDFs.")
        return
    if not os.path.isdir(pasta_entrada):
        messagebox.showerror("Erro", "Pasta de entrada não encontrada.")
        return
    if not pasta_saida:
        messagebox.showwarning("Atenção", "Selecione a pasta de saída.")
        return

    if spec_paginas:
        teste = parse_paginas(spec_paginas, 9999)
        if teste is None:
            messagebox.showerror(
                "Erro nas páginas",
                "Formato inválido.\nExemplos válidos: 1 | 1,3 | 1-3 | 1-3,5,7-9"
            )
            return
    else:
        paginas_var.set("1")

    log_widget.config(state="normal")
    log_widget.delete("1.0", tk.END)
    log_widget.config(state="disabled")
    progress["value"] = 0
    btn_iniciar.config(state="disabled")

    threading.Thread(
        target=processar_pdfs,
        args=(pasta_entrada, pasta_saida, paginas_var.get().strip(), log, progress, btn_iniciar),
        daemon=True
    ).start()


# ── Interface ────────────────────────────────────────────────────────────────

root = tk.Tk()
root.title("Extrair e Juntar PDFs")
root.resizable(False, False)

PADX = 12
PADY = 5

root.configure(padx=PADX, pady=PADX)

tk.Label(root, text="📄 Extrair e Juntar PDFs", font=("Segoe UI", 14, "bold")).grid(
    row=0, column=0, columnspan=3, pady=(0, 10), sticky="w"
)

tk.Label(root, text="Pasta com os PDFs (entrada):", font=("Segoe UI", 9)).grid(
    row=1, column=0, columnspan=3, sticky="w"
)
entrada_var = tk.StringVar()
tk.Entry(root, textvariable=entrada_var, width=55, font=("Segoe UI", 9)).grid(
    row=2, column=0, columnspan=2, sticky="ew", pady=(0, PADY)
)
tk.Button(
    root, text="Selecionar", font=("Segoe UI", 9),
    command=lambda: entrada_var.set(
        filedialog.askdirectory(title="Selecione a pasta com os PDFs")
    )
).grid(row=2, column=2, padx=(6, 0), pady=(0, PADY))

tk.Label(root, text="Pasta de saída (onde salvar os arquivos):", font=("Segoe UI", 9)).grid(
    row=3, column=0, columnspan=3, sticky="w"
)
saida_var = tk.StringVar()
tk.Entry(root, textvariable=saida_var, width=55, font=("Segoe UI", 9)).grid(
    row=4, column=0, columnspan=2, sticky="ew", pady=(0, PADY)
)
tk.Button(
    root, text="Selecionar", font=("Segoe UI", 9),
    command=lambda: saida_var.set(
        filedialog.askdirectory(title="Selecione a pasta de saída")
    )
).grid(row=4, column=2, padx=(6, 0), pady=(0, PADY))

frame_pag = tk.LabelFrame(
    root, text="  Páginas a extrair  ", font=("Segoe UI", 9), padx=8, pady=6
)
frame_pag.grid(row=5, column=0, columnspan=3, sticky="ew", pady=(4, PADY))

tk.Label(
    frame_pag,
    text="Informe as páginas (ex.: 1 | 1,3 | 2-4 | 1-3,5,7-9)\nDeixe vazio para extrair apenas a 1ª página:",
    font=("Segoe UI", 9), justify="left"
).grid(row=0, column=0, sticky="w")

paginas_var = tk.StringVar(value="1")
tk.Entry(frame_pag, textvariable=paginas_var, width=30, font=("Segoe UI", 9)).grid(
    row=1, column=0, sticky="w", pady=(4, 0)
)

tk.Label(root, text="Log:", font=("Segoe UI", 9)).grid(
    row=6, column=0, columnspan=3, sticky="w", pady=(4, 0)
)
log_widget = tk.Text(
    root, height=10, width=65, font=("Consolas", 9),
    state="disabled", bg="#f4f4f4"
)
log_widget.grid(row=7, column=0, columnspan=3, pady=(0, PADY))


def log(msg):
    log_widget.config(state="normal")
    log_widget.insert(tk.END, msg + "\n")
    log_widget.see(tk.END)
    log_widget.config(state="disabled")


progress = ttk.Progressbar(root, length=520, mode="determinate")
progress.grid(row=8, column=0, columnspan=3, pady=(0, PADY), sticky="ew")

btn_iniciar = tk.Button(
    root, text="▶  Iniciar", font=("Segoe UI", 10, "bold"),
    bg="#0078D4", fg="white", relief="flat", padx=16, pady=6,
    command=lambda: iniciar_thread(
        entrada_var, saida_var, paginas_var, log, progress, btn_iniciar
    )
)
btn_iniciar.grid(row=9, column=0, columnspan=3, pady=(4, 0))

root.mainloop()
