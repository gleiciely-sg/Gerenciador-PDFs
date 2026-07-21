"""
Extrai páginas específicas de cada PDF com 3 modos de operação:
  1 - Salva individuais + gera arquivo final unido
  2 - Salva apenas os arquivos individuais
  3 - Apenas gera o arquivo final unido
Interface gráfica — basta dar duplo clique no .exe para abrir.
"""

import os
import re
import threading
import tkinter as tk
from tkinter import filedialog, messagebox, ttk
from pypdf import PdfReader, PdfWriter


def ordenar_numerico(nome):
    numeros = re.findall(r'\d+', nome)
    return int(numeros[0]) if numeros else 0


def parse_paginas(texto, total_paginas):
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


def processar_pdfs(caminhos, pasta_saida, spec_paginas, modo, nome_final, log, progress, btn_iniciar):
    os.makedirs(pasta_saida, exist_ok=True)
    arquivo_final = os.path.join(pasta_saida, nome_final)

    if not caminhos:
        messagebox.showerror("Erro", "Nenhum PDF encontrado.")
        btn_iniciar.config(state="normal")
        return

    # Ordena pelos nomes dos arquivos numericamente
    caminhos = sorted(caminhos, key=lambda p: ordenar_numerico(os.path.basename(p)))
    total = len(caminhos)
    log(f"📂 {total} arquivo(s) encontrado(s)\n")

    writer_final = PdfWriter()
    arquivos_ok = 0

    for i, caminho in enumerate(caminhos):
        nome = os.path.basename(caminho)
        try:
            reader = PdfReader(caminho)
            total_pags = len(reader.pages)

            if total_pags == 0:
                log(f"⚠️  Vazio (ignorado): {nome}")
                progress["value"] = int((i + 1) / total * 95)
                continue

            if spec_paginas.strip():
                indices = parse_paginas(spec_paginas, total_pags)
                if indices is None:
                    log(f"⚠️  Páginas fora do intervalo em '{nome}' ({total_pags} pág.) — usando todas as páginas")
                    indices = list(range(total_pags))
            else:
                # Sem especificação: usa todas as páginas do arquivo
                indices = list(range(total_pags))

            # Modo 1 ou 2: salva arquivo individual
            if modo in (1, 2):
                writer_ind = PdfWriter()
                for idx in indices:
                    writer_ind.add_page(reader.pages[idx])
                saida_ind = os.path.join(pasta_saida, nome)
                with open(saida_ind, "wb") as f:
                    writer_ind.write(f)

            # Modo 1 ou 3: adiciona ao arquivo final
            if modo in (1, 3):
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

    # Grava arquivo final (modos 1 e 3)
    if modo in (1, 3):
        with open(arquivo_final, "wb") as f:
            writer_final.write(f)

    progress["value"] = 100
    log(f"\n✅ Concluído! {arquivos_ok} arquivo(s) processado(s).")

    if modo == 1:
        log(f"   • Individuais salvos em: {pasta_saida}")
        log(f"   • Arquivo unido: {arquivo_final}")
        msg = f"{arquivos_ok} arquivo(s) individual(is) gerado(s).\n\nArquivo unido:\n{arquivo_final}"
    elif modo == 2:
        log(f"   • Individuais salvos em: {pasta_saida}")
        msg = f"{arquivos_ok} arquivo(s) individual(is) salvo(s) em:\n{pasta_saida}"
    else:
        log(f"   • Arquivo unido: {arquivo_final}")
        msg = f"Arquivo unido gerado com sucesso!\n\n{arquivo_final}"

    messagebox.showinfo("Sucesso", msg)
    btn_iniciar.config(state="normal")


def selecionar_arquivos():
    arquivos = filedialog.askopenfilenames(
        title="Selecione os arquivos PDF",
        filetypes=[("PDF", "*.pdf")]
    )
    if arquivos:
        arquivos_selecionados.clear()
        arquivos_selecionados.extend(arquivos)
        nomes = ", ".join(os.path.basename(a) for a in arquivos)
        entrada_var.set(nomes)
        tipo_entrada_var.set("arquivos")


def selecionar_pasta():
    pasta = filedialog.askdirectory(title="Pasta com os PDFs")
    if pasta:
        arquivos_selecionados.clear()
        entrada_var.set(pasta)
        tipo_entrada_var.set("pasta")


def iniciar_thread(entrada_var, saida_var, paginas_var, modo_var, nome_var, log, progress, btn_iniciar):
    pasta_saida = saida_var.get().strip()
    spec_paginas = paginas_var.get().strip()
    modo = modo_var.get()
    nome_final = nome_var.get().strip()
    tipo = tipo_entrada_var.get()

    if not entrada_var.get().strip():
        messagebox.showwarning("Atenção", "Selecione a pasta ou os arquivos de entrada.")
        return
    if not pasta_saida:
        messagebox.showwarning("Atenção", "Selecione a pasta de saída.")
        return
    if modo in (1, 3) and not nome_final:
        messagebox.showwarning("Atenção", "Defina o nome do arquivo final.")
        return
    if nome_final and not nome_final.lower().endswith(".pdf"):
        nome_final += ".pdf"
        nome_var.set(nome_final)

    if spec_paginas:
        if parse_paginas(spec_paginas, 9999) is None:
            messagebox.showerror(
                "Erro nas páginas",
                "Formato inválido.\nExemplos válidos: 1 | 1,3 | 1-3 | 1-3,5,7-9"
            )
            return

    # Monta lista de caminhos
    if tipo == "arquivos":
        caminhos = list(arquivos_selecionados)
    else:
        pasta = entrada_var.get().strip()
        if not os.path.isdir(pasta):
            messagebox.showerror("Erro", "Pasta de entrada não encontrada.")
            return
        caminhos = [
            os.path.join(pasta, f) for f in os.listdir(pasta)
            if f.lower().endswith(".pdf") and f != nome_final
        ]

    if not caminhos:
        messagebox.showerror("Erro", "Nenhum PDF encontrado.")
        return

    log_widget.config(state="normal")
    log_widget.delete("1.0", tk.END)
    log_widget.config(state="disabled")
    progress["value"] = 0
    btn_iniciar.config(state="disabled")

    threading.Thread(
        target=processar_pdfs,
        args=(caminhos, pasta_saida, spec_paginas, modo, nome_final, log, progress, btn_iniciar),
        daemon=True
    ).start()


def atualizar_campos(*args):
    modo = modo_var.get()
    # Nome do arquivo final só aparece nos modos 1 e 3
    if modo in (1, 3):
        label_nome.grid()
        entry_nome.grid()
    else:
        label_nome.grid_remove()
        entry_nome.grid_remove()


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

# ── Modo de operação ──
frame_modo = tk.LabelFrame(root, text="  Modo de operação  ", font=("Segoe UI", 9), padx=8, pady=6)
frame_modo.grid(row=1, column=0, columnspan=3, sticky="ew", pady=(0, PADY))

modo_var = tk.IntVar(value=1)
tk.Radiobutton(
    frame_modo, text="1 — Salvar individuais + arquivo final unido",
    variable=modo_var, value=1, font=("Segoe UI", 9), command=atualizar_campos
).grid(row=0, column=0, sticky="w")
tk.Radiobutton(
    frame_modo, text="2 — Salvar apenas os arquivos individuais",
    variable=modo_var, value=2, font=("Segoe UI", 9), command=atualizar_campos
).grid(row=1, column=0, sticky="w")
tk.Radiobutton(
    frame_modo, text="3 — Apenas juntar em um arquivo final",
    variable=modo_var, value=3, font=("Segoe UI", 9), command=atualizar_campos
).grid(row=2, column=0, sticky="w")

# ── Entrada (pasta ou arquivos) ──
tk.Label(root, text="Entrada (pasta ou arquivos PDF):", font=("Segoe UI", 9)).grid(
    row=2, column=0, columnspan=3, sticky="w"
)
arquivos_selecionados = []
tipo_entrada_var = tk.StringVar(value="pasta")
entrada_var = tk.StringVar()
tk.Entry(root, textvariable=entrada_var, width=55, font=("Segoe UI", 9), state="readonly").grid(
    row=3, column=0, columnspan=2, sticky="ew", pady=(0, 2)
)
frame_btns_entrada = tk.Frame(root)
frame_btns_entrada.grid(row=3, column=2, padx=(6, 0), pady=(0, 2))
tk.Button(
    frame_btns_entrada, text="📁 Pasta", font=("Segoe UI", 9), width=8,
    command=selecionar_pasta
).pack(side="top", pady=(0, 2))
tk.Button(
    frame_btns_entrada, text="📄 Arquivos", font=("Segoe UI", 9), width=8,
    command=selecionar_arquivos
).pack(side="top")

# ── Pasta de saída ──
tk.Label(root, text="Pasta de saída:", font=("Segoe UI", 9)).grid(
    row=4, column=0, columnspan=3, sticky="w"
)
saida_var = tk.StringVar()
tk.Entry(root, textvariable=saida_var, width=55, font=("Segoe UI", 9)).grid(
    row=5, column=0, columnspan=2, sticky="ew", pady=(0, PADY)
)
tk.Button(
    root, text="Selecionar", font=("Segoe UI", 9),
    command=lambda: saida_var.set(filedialog.askdirectory(title="Pasta de saída"))
).grid(row=5, column=2, padx=(6, 0), pady=(0, PADY))

# ── Nome do arquivo final (oculto no modo 2) ──
label_nome = tk.Label(root, text="Nome do arquivo final:", font=("Segoe UI", 9))
label_nome.grid(row=6, column=0, columnspan=3, sticky="w")
nome_var = tk.StringVar(value="Arquivo_Final.pdf")
entry_nome = tk.Entry(root, textvariable=nome_var, width=55, font=("Segoe UI", 9))
entry_nome.grid(row=7, column=0, columnspan=2, sticky="ew", pady=(0, PADY))

# ── Páginas ──
frame_pag = tk.LabelFrame(root, text="  Páginas a extrair  ", font=("Segoe UI", 9), padx=8, pady=6)
frame_pag.grid(row=8, column=0, columnspan=3, sticky="ew", pady=(4, PADY))

tk.Label(
    frame_pag,
    text="Informe as páginas (ex.: 1 | 1,3 | 2-4 | 1-3,5,7-9)\nDeixe vazio para usar todas as páginas de cada arquivo:",
    font=("Segoe UI", 9), justify="left"
).grid(row=0, column=0, sticky="w")

paginas_var = tk.StringVar(value="")
tk.Entry(frame_pag, textvariable=paginas_var, width=30, font=("Segoe UI", 9)).grid(
    row=1, column=0, sticky="w", pady=(4, 0)
)

# ── Log ──
tk.Label(root, text="Log:", font=("Segoe UI", 9)).grid(
    row=9, column=0, columnspan=3, sticky="w", pady=(4, 0)
)
log_widget = tk.Text(root, height=10, width=65, font=("Consolas", 9), state="disabled", bg="#f4f4f4")
log_widget.grid(row=10, column=0, columnspan=3, pady=(0, PADY))


def log(msg):
    log_widget.config(state="normal")
    log_widget.insert(tk.END, msg + "\n")
    log_widget.see(tk.END)
    log_widget.config(state="disabled")


# ── Progresso ──
progress = ttk.Progressbar(root, length=520, mode="determinate")
progress.grid(row=11, column=0, columnspan=3, pady=(0, PADY), sticky="ew")

# ── Botão ──
btn_iniciar = tk.Button(
    root, text="▶  Iniciar", font=("Segoe UI", 10, "bold"),
    bg="#0078D4", fg="white", relief="flat", padx=16, pady=6,
    command=lambda: iniciar_thread(
        entrada_var, saida_var, paginas_var, modo_var, nome_var, log, progress, btn_iniciar
    )
)
btn_iniciar.grid(row=12, column=0, columnspan=3, pady=(4, 0))

root.mainloop()
