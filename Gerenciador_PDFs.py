"""
Gerenciador de PDFs
Funcionalidades:
  - Extrair/Juntar páginas
  - Excluir páginas
  - Dividir PDF
  - Reorganizar páginas
  - Renomear arquivos
  - Girar páginas
  - Proteger/Desproteger com senha
  - Informações do PDF
"""

import os
import re
import threading
import tkinter as tk
from tkinter import filedialog, messagebox, ttk
from pypdf import PdfReader, PdfWriter


# ── Utilitários ───────────────────────────────────────────────────────────────

def ordenar_numerico(nome):
    numeros = re.findall(r'\d+', nome)
    return int(numeros[0]) if numeros else 0


def parse_paginas(texto, total_paginas):
    indices = set()
    texto = texto.strip()
    if not texto:
        return None
    for parte in texto.split(","):
        parte = parte.strip()
        if "-" in parte:
            bounds = parte.split("-")
            if len(bounds) != 2:
                return None
            try:
                inicio, fim = int(bounds[0].strip()), int(bounds[1].strip())
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


def log_write(widget, msg):
    widget.config(state="normal")
    widget.insert(tk.END, msg + "\n")
    widget.see(tk.END)
    widget.config(state="disabled")


def log_clear(widget):
    widget.config(state="normal")
    widget.delete("1.0", tk.END)
    widget.config(state="disabled")


def make_log_widget(parent, row, col=0, colspan=3, height=8):
    tk.Label(parent, text="Log:", font=("Segoe UI", 9)).grid(
        row=row, column=col, columnspan=colspan, sticky="w", pady=(6, 0)
    )
    w = tk.Text(parent, height=height, width=65, font=("Consolas", 9),
                state="disabled", bg="#f4f4f4")
    w.grid(row=row + 1, column=col, columnspan=colspan, pady=(0, 4))
    return w


def make_progress(parent, row, col=0, colspan=3):
    p = ttk.Progressbar(parent, length=520, mode="determinate")
    p.grid(row=row, column=col, columnspan=colspan, sticky="ew", pady=(0, 4))
    return p


def escolher_pdf_entrada(var):
    f = filedialog.askopenfilename(title="Selecione o PDF", filetypes=[("PDF", "*.pdf")])
    if f:
        var.set(f)


def escolher_pasta(var, title="Selecione a pasta"):
    p = filedialog.askdirectory(title=title)
    if p:
        var.set(p)


def escolher_pdf_saida(var, initial="saida.pdf"):
    f = filedialog.asksaveasfilename(
        title="Salvar como", defaultextension=".pdf",
        filetypes=[("PDF", "*.pdf")], initialfile=initial
    )
    if f:
        var.set(f)


def row_entrada_pdf(parent, row, label, var):
    tk.Label(parent, text=label, font=("Segoe UI", 9)).grid(
        row=row, column=0, columnspan=3, sticky="w")
    tk.Entry(parent, textvariable=var, width=52, font=("Segoe UI", 9),
             state="readonly").grid(row=row+1, column=0, columnspan=2, sticky="ew", pady=(0, 4))
    tk.Button(parent, text="Selecionar", font=("Segoe UI", 9),
              command=lambda: escolher_pdf_entrada(var)).grid(
        row=row+1, column=2, padx=(6, 0), pady=(0, 4))


def row_saida_pdf(parent, row, label, var, initial="saida.pdf"):
    tk.Label(parent, text=label, font=("Segoe UI", 9)).grid(
        row=row, column=0, columnspan=3, sticky="w")
    tk.Entry(parent, textvariable=var, width=52, font=("Segoe UI", 9),
             state="readonly").grid(row=row+1, column=0, columnspan=2, sticky="ew", pady=(0, 4))
    tk.Button(parent, text="Salvar em…", font=("Segoe UI", 9),
              command=lambda: escolher_pdf_saida(var, initial)).grid(
        row=row+1, column=2, padx=(6, 0), pady=(0, 4))


def row_pasta(parent, row, label, var):
    tk.Label(parent, text=label, font=("Segoe UI", 9)).grid(
        row=row, column=0, columnspan=3, sticky="w")
    tk.Entry(parent, textvariable=var, width=52, font=("Segoe UI", 9),
             state="readonly").grid(row=row+1, column=0, columnspan=2, sticky="ew", pady=(0, 4))
    tk.Button(parent, text="Selecionar", font=("Segoe UI", 9),
              command=lambda: escolher_pasta(var)).grid(
        row=row+1, column=2, padx=(6, 0), pady=(0, 4))


def btn_iniciar(parent, row, text, cmd):
    b = tk.Button(parent, text=text, font=("Segoe UI", 10, "bold"),
                  bg="#0078D4", fg="white", relief="flat", padx=16, pady=6,
                  command=cmd)
    b.grid(row=row, column=0, columnspan=3, pady=(4, 8))
    return b


def btn_limpar(parent, row, cmd):
    tk.Button(parent, text="🗑  Limpar", font=("Segoe UI", 9),
              fg="#cc0000", relief="flat",
              command=cmd).grid(row=row, column=2, sticky="e", pady=(4, 0))


# ══════════════════════════════════════════════════════════════════════════════
# ABA 1 — Extrair / Juntar
# ══════════════════════════════════════════════════════════════════════════════

def build_aba_extrair(nb):
    frame = ttk.Frame(nb, padding=12)
    nb.add(frame, text="  Extrair / Juntar  ")

    frame_modo = tk.LabelFrame(frame, text="  Modo  ", font=("Segoe UI", 9), padx=8, pady=6)
    frame_modo.grid(row=0, column=0, columnspan=3, sticky="ew", pady=(0, 6))
    modo_var = tk.IntVar(value=1)

    def atualizar_nome(*_):
        if modo_var.get() in (1, 3):
            lnome.grid(); enome.grid()
        else:
            lnome.grid_remove(); enome.grid_remove()

    tk.Radiobutton(frame_modo, text="1 — Salvar individuais + arquivo final unido",
                   variable=modo_var, value=1, font=("Segoe UI", 9),
                   command=atualizar_nome).grid(row=0, column=0, sticky="w")
    tk.Radiobutton(frame_modo, text="2 — Salvar apenas arquivos individuais",
                   variable=modo_var, value=2, font=("Segoe UI", 9),
                   command=atualizar_nome).grid(row=1, column=0, sticky="w")
    tk.Radiobutton(frame_modo, text="3 — Apenas juntar em um arquivo final",
                   variable=modo_var, value=3, font=("Segoe UI", 9),
                   command=atualizar_nome).grid(row=2, column=0, sticky="w")

    arqs_sel = []
    tipo_var = tk.StringVar(value="pasta")
    entrada_var = tk.StringVar()
    saida_var = tk.StringVar()

    def adicionar_arquivos():
        arqs = filedialog.askopenfilenames(title="Selecionar PDFs", filetypes=[("PDF", "*.pdf")])
        for a in arqs:
            if a not in arqs_sel:
                arqs_sel.append(a)
        if arqs_sel:
            tipo_var.set("arquivos")
            n = len(arqs_sel)
            entrada_var.set(arqs_sel[0] if n == 1 else f"{n} arquivo(s) selecionado(s)")

    def sel_pasta():
        p = filedialog.askdirectory(title="Pasta com os PDFs")
        if p:
            arqs_sel.clear()
            tipo_var.set("pasta")
            entrada_var.set(p)

    def limpar_entrada():
        arqs_sel.clear()
        tipo_var.set("pasta")
        entrada_var.set("")

    def limpar_tudo():
        limpar_entrada()
        saida_var.set("")
        nome_var.set("Arquivo_Final.pdf")
        paginas_var.set("")
        modo_var.set(1)
        atualizar_nome()
        log_clear(log_w)
        prog["value"] = 0

    tk.Label(frame, text="Entrada (pasta ou arquivos):", font=("Segoe UI", 9)).grid(
        row=1, column=0, columnspan=3, sticky="w")
    tk.Entry(frame, textvariable=entrada_var, width=52, font=("Segoe UI", 9),
             state="readonly").grid(row=2, column=0, columnspan=2, sticky="ew", pady=(0, 2))
    fb = tk.Frame(frame)
    fb.grid(row=2, column=2, padx=(6, 0), pady=(0, 2))
    tk.Button(fb, text="📁 Pasta", font=("Segoe UI", 9), width=10,
              command=sel_pasta).pack(side="top", pady=(0, 2))
    tk.Button(fb, text="📄 + Arquivos", font=("Segoe UI", 9), width=10,
              command=adicionar_arquivos).pack(side="top", pady=(0, 2))
    tk.Button(fb, text="🗑 Limpar", font=("Segoe UI", 9), width=10, fg="red",
              command=limpar_entrada).pack(side="top")

    row_pasta(frame, 3, "Pasta de saída:", saida_var)

    lnome = tk.Label(frame, text="Nome do arquivo final:", font=("Segoe UI", 9))
    lnome.grid(row=5, column=0, columnspan=3, sticky="w")
    nome_var = tk.StringVar(value="Arquivo_Final.pdf")
    enome = tk.Entry(frame, textvariable=nome_var, width=52, font=("Segoe UI", 9))
    enome.grid(row=6, column=0, columnspan=2, sticky="ew", pady=(0, 4))

    fp = tk.LabelFrame(frame, text="  Páginas a extrair  ", font=("Segoe UI", 9), padx=8, pady=6)
    fp.grid(row=7, column=0, columnspan=3, sticky="ew", pady=(4, 6))
    tk.Label(fp, text="Ex.: 1 | 1,3 | 2-4 | 1-3,5,7-9  —  vazio = todas as páginas",
             font=("Segoe UI", 9)).grid(row=0, column=0, sticky="w")
    paginas_var = tk.StringVar(value="")
    tk.Entry(fp, textvariable=paginas_var, width=30, font=("Segoe UI", 9)).grid(
        row=1, column=0, sticky="w", pady=(4, 0))

    log_w = make_log_widget(frame, 8)
    prog = make_progress(frame, 10)
    log = lambda m: log_write(log_w, m)

    def processar(caminhos, pasta_saida, spec, modo, nome_final, btn):
        os.makedirs(pasta_saida, exist_ok=True)
        arquivo_final = os.path.join(pasta_saida, nome_final)
        caminhos = sorted(caminhos, key=lambda p: ordenar_numerico(os.path.basename(p)))
        total = len(caminhos)
        log(f"📂 {total} arquivo(s) encontrado(s)\n")
        writer_final = PdfWriter()
        ok = 0
        for i, caminho in enumerate(caminhos):
            nome = os.path.basename(caminho)
            try:
                reader = PdfReader(caminho)
                tp = len(reader.pages)
                if tp == 0:
                    log(f"⚠️  Vazio: {nome}"); continue
                indices = parse_paginas(spec, tp) if spec.strip() else list(range(tp))
                if indices is None:
                    log(f"⚠️  Páginas fora do intervalo em '{nome}' — usando todas")
                    indices = list(range(tp))
                if modo in (1, 2):
                    w = PdfWriter()
                    for idx in indices:
                        w.add_page(reader.pages[idx])
                    with open(os.path.join(pasta_saida, nome), "wb") as f:
                        w.write(f)
                if modo in (1, 3):
                    for idx in indices:
                        writer_final.add_page(reader.pages[idx])
                pstr = spec if spec.strip() else "todas"
                log(f"✔  {nome}  →  págs. [{pstr}]  ({tp} pág.)")
                ok += 1
            except Exception as e:
                log(f"❌ Erro em {nome}: {e}")
            prog["value"] = int((i + 1) / total * 95)
        if ok == 0:
            messagebox.showerror("Erro", "Nenhuma página extraída.")
            btn.config(state="normal"); return
        if modo in (1, 3):
            with open(arquivo_final, "wb") as f:
                writer_final.write(f)
        prog["value"] = 100
        log(f"\n✅ Concluído! {ok} arquivo(s) processado(s).")
        if modo == 1:
            messagebox.showinfo("Sucesso", f"{ok} individual(is) + arquivo unido:\n{arquivo_final}")
        elif modo == 2:
            messagebox.showinfo("Sucesso", f"{ok} arquivo(s) salvo(s) em:\n{pasta_saida}")
        else:
            messagebox.showinfo("Sucesso", f"Arquivo unido:\n{arquivo_final}")
        btn.config(state="normal")

    def iniciar(btn):
        entrada = entrada_var.get().strip()
        saida = saida_var.get().strip()
        spec = paginas_var.get().strip()
        modo = modo_var.get()
        nome = nome_var.get().strip()
        if not entrada: messagebox.showwarning("Atenção", "Selecione a entrada."); return
        if not saida: messagebox.showwarning("Atenção", "Selecione a pasta de saída."); return
        if modo in (1, 3) and not nome:
            messagebox.showwarning("Atenção", "Defina o nome do arquivo final."); return
        if nome and not nome.lower().endswith(".pdf"):
            nome += ".pdf"; nome_var.set(nome)
        if spec and parse_paginas(spec, 9999) is None:
            messagebox.showerror("Erro", "Formato de páginas inválido.\nEx.: 1 | 1,3 | 1-3"); return
        if tipo_var.get() == "arquivos":
            caminhos = list(arqs_sel)
        else:
            if not os.path.isdir(entrada):
                messagebox.showerror("Erro", "Pasta não encontrada."); return
            caminhos = [os.path.join(entrada, f) for f in os.listdir(entrada)
                        if f.lower().endswith(".pdf") and f != nome]
        if not caminhos:
            messagebox.showerror("Erro", "Nenhum PDF encontrado."); return
        log_clear(log_w); prog["value"] = 0; btn.config(state="disabled")
        threading.Thread(target=processar,
                         args=(caminhos, saida, spec, modo, nome, btn),
                         daemon=True).start()

    btn_limpar(frame, 11, limpar_tudo)
    b = btn_iniciar(frame, 12, "▶  Iniciar", lambda: iniciar(b))


# ══════════════════════════════════════════════════════════════════════════════
# ABA 2 — Excluir Páginas
# ══════════════════════════════════════════════════════════════════════════════

def build_aba_excluir(nb):
    frame = ttk.Frame(nb, padding=12)
    nb.add(frame, text="  Excluir Páginas  ")

    entrada_var = tk.StringVar()
    saida_var = tk.StringVar()
    paginas_var = tk.StringVar()

    row_entrada_pdf(frame, 0, "Arquivo PDF:", entrada_var)
    row_saida_pdf(frame, 2, "Salvar resultado como:", saida_var, "sem_paginas.pdf")
    tk.Label(frame, text="Páginas a EXCLUIR (ex.: 1 | 2,4 | 3-5 | 1,3-5,7):",
             font=("Segoe UI", 9)).grid(row=4, column=0, columnspan=3, sticky="w")
    tk.Entry(frame, textvariable=paginas_var, width=30, font=("Segoe UI", 9)).grid(
        row=5, column=0, sticky="w", pady=(0, 6))

    log_w = make_log_widget(frame, 6)
    prog = make_progress(frame, 8)
    log = lambda m: log_write(log_w, m)

    def limpar_tudo():
        entrada_var.set(""); saida_var.set(""); paginas_var.set("")
        log_clear(log_w); prog["value"] = 0

    def processar(entrada, saida, spec, btn):
        try:
            reader = PdfReader(entrada)
            tp = len(reader.pages)
            excluir = parse_paginas(spec, tp)
            if excluir is None:
                messagebox.showerror("Erro", "Formato de páginas inválido.")
                btn.config(state="normal"); return
            manter = [i for i in range(tp) if i not in excluir]
            if not manter:
                messagebox.showerror("Erro", "Todas as páginas seriam excluídas.")
                btn.config(state="normal"); return
            writer = PdfWriter()
            for i, idx in enumerate(manter):
                writer.add_page(reader.pages[idx])
                prog["value"] = int((i+1)/len(manter)*95)
            with open(saida, "wb") as f:
                writer.write(f)
            prog["value"] = 100
            log(f"✅ {len(excluir)} página(s) excluída(s), {len(manter)} mantida(s).")
            log(f"📄 Salvo em: {saida}")
            messagebox.showinfo("Sucesso", f"PDF salvo com {len(manter)} página(s):\n{saida}")
        except Exception as e:
            log(f"❌ Erro: {e}"); messagebox.showerror("Erro", str(e))
        btn.config(state="normal")

    def iniciar(btn):
        e = entrada_var.get().strip(); s = saida_var.get().strip(); p = paginas_var.get().strip()
        if not e: messagebox.showwarning("Atenção", "Selecione o PDF."); return
        if not s: messagebox.showwarning("Atenção", "Defina o arquivo de saída."); return
        if not p: messagebox.showwarning("Atenção", "Informe as páginas a excluir."); return
        log_clear(log_w); prog["value"] = 0; btn.config(state="disabled")
        threading.Thread(target=processar, args=(e, s, p, btn), daemon=True).start()

    btn_limpar(frame, 9, limpar_tudo)
    b = btn_iniciar(frame, 10, "▶  Excluir Páginas", lambda: iniciar(b))


# ══════════════════════════════════════════════════════════════════════════════
# ABA 3 — Dividir PDF
# ══════════════════════════════════════════════════════════════════════════════

def build_aba_dividir(nb):
    frame = ttk.Frame(nb, padding=12)
    nb.add(frame, text="  Dividir PDF  ")

    entrada_var = tk.StringVar()
    saida_var = tk.StringVar()
    modo_var = tk.IntVar(value=1)
    intervalos_var = tk.StringVar()

    row_entrada_pdf(frame, 0, "Arquivo PDF:", entrada_var)
    row_pasta(frame, 2, "Pasta de saída:", saida_var)

    fm = tk.LabelFrame(frame, text="  Modo de divisão  ", font=("Segoe UI", 9), padx=8, pady=6)
    fm.grid(row=4, column=0, columnspan=3, sticky="ew", pady=(4, 6))
    tk.Radiobutton(fm, text="1 página por arquivo", variable=modo_var, value=1,
                   font=("Segoe UI", 9)).grid(row=0, column=0, sticky="w")
    tk.Radiobutton(fm, text="Intervalos personalizados (ex.: 1-3,4-6,7)",
                   variable=modo_var, value=2, font=("Segoe UI", 9)).grid(row=1, column=0, sticky="w")
    tk.Entry(fm, textvariable=intervalos_var, width=35, font=("Segoe UI", 9)).grid(
        row=2, column=0, sticky="w", pady=(4, 0))

    log_w = make_log_widget(frame, 5)
    prog = make_progress(frame, 7)
    log = lambda m: log_write(log_w, m)

    def limpar_tudo():
        entrada_var.set(""); saida_var.set(""); intervalos_var.set(""); modo_var.set(1)
        log_clear(log_w); prog["value"] = 0

    def processar(entrada, saida, modo, intervalos, btn):
        try:
            reader = PdfReader(entrada)
            tp = len(reader.pages)
            os.makedirs(saida, exist_ok=True)
            base = os.path.splitext(os.path.basename(entrada))[0]
            if modo == 1:
                for i in range(tp):
                    w = PdfWriter()
                    w.add_page(reader.pages[i])
                    out = os.path.join(saida, f"{base}_pag{i+1:03d}.pdf")
                    with open(out, "wb") as f:
                        w.write(f)
                    log(f"✔  Página {i+1} → {os.path.basename(out)}")
                    prog["value"] = int((i+1)/tp*95)
            else:
                grupos = []
                for parte in intervalos.split(","):
                    parte = parte.strip()
                    idx = parse_paginas(parte, tp)
                    if idx is None:
                        messagebox.showerror("Erro", f"Intervalo inválido: '{parte}'")
                        btn.config(state="normal"); return
                    grupos.append(idx)
                for g, grupo in enumerate(grupos):
                    w = PdfWriter()
                    for idx in grupo:
                        w.add_page(reader.pages[idx])
                    out = os.path.join(saida, f"{base}_parte{g+1:03d}.pdf")
                    with open(out, "wb") as f:
                        w.write(f)
                    log(f"✔  Parte {g+1} ({len(grupo)} pág.) → {os.path.basename(out)}")
                    prog["value"] = int((g+1)/len(grupos)*95)
            prog["value"] = 100
            log(f"\n✅ Concluído! Arquivos salvos em: {saida}")
            messagebox.showinfo("Sucesso", f"PDF dividido!\n{saida}")
        except Exception as e:
            log(f"❌ Erro: {e}"); messagebox.showerror("Erro", str(e))
        btn.config(state="normal")

    def iniciar(btn):
        e = entrada_var.get().strip(); s = saida_var.get().strip()
        m = modo_var.get(); iv = intervalos_var.get().strip()
        if not e: messagebox.showwarning("Atenção", "Selecione o PDF."); return
        if not s: messagebox.showwarning("Atenção", "Selecione a pasta de saída."); return
        if m == 2 and not iv: messagebox.showwarning("Atenção", "Informe os intervalos."); return
        log_clear(log_w); prog["value"] = 0; btn.config(state="disabled")
        threading.Thread(target=processar, args=(e, s, m, iv, btn), daemon=True).start()

    btn_limpar(frame, 8, limpar_tudo)
    b = btn_iniciar(frame, 9, "▶  Dividir", lambda: iniciar(b))


# ══════════════════════════════════════════════════════════════════════════════
# ABA 4 — Reorganizar Páginas
# ══════════════════════════════════════════════════════════════════════════════

def build_aba_reorganizar(nb):
    frame = ttk.Frame(nb, padding=12)
    nb.add(frame, text="  Reorganizar  ")

    entrada_var = tk.StringVar()
    saida_var = tk.StringVar()

    row_entrada_pdf(frame, 0, "Arquivo PDF:", entrada_var)
    row_saida_pdf(frame, 2, "Salvar resultado como:", saida_var, "reorganizado.pdf")

    tk.Label(frame, text="Ordem das páginas (selecione e mova):",
             font=("Segoe UI", 9)).grid(row=4, column=0, columnspan=3, sticky="w", pady=(6, 0))

    frame_lista = tk.Frame(frame)
    frame_lista.grid(row=5, column=0, columnspan=3, sticky="ew", pady=(0, 4))

    scrollbar = tk.Scrollbar(frame_lista, orient="vertical")
    listbox = tk.Listbox(frame_lista, height=10, width=45, font=("Segoe UI", 9),
                         selectmode="extended", yscrollcommand=scrollbar.set,
                         activestyle="dotbox")
    scrollbar.config(command=listbox.yview)
    listbox.pack(side="left", fill="both")
    scrollbar.pack(side="left", fill="y")

    frame_ctrl = tk.Frame(frame_lista)
    frame_ctrl.pack(side="left", padx=(8, 0), anchor="n")

    def mover_cima():
        sels = list(listbox.curselection())
        if not sels or sels[0] == 0: return
        for i in sels:
            texto = listbox.get(i)
            listbox.delete(i)
            listbox.insert(i - 1, texto)
            listbox.selection_set(i - 1)

    def mover_baixo():
        sels = list(listbox.curselection())
        if not sels or sels[-1] == listbox.size() - 1: return
        for i in reversed(sels):
            texto = listbox.get(i)
            listbox.delete(i)
            listbox.insert(i + 1, texto)
            listbox.selection_set(i + 1)

    def mover_para():
        sels = list(listbox.curselection())
        if not sels:
            messagebox.showwarning("Atenção", "Selecione ao menos uma página."); return
        try:
            pos = int(pos_var.get().strip()) - 1
            if pos < 0 or pos >= listbox.size(): raise ValueError()
        except ValueError:
            messagebox.showerror("Erro", f"Posição inválida. Digite entre 1 e {listbox.size()}."); return
        itens = [listbox.get(i) for i in sels]
        for i in reversed(sels):
            listbox.delete(i)
        for j, item in enumerate(itens):
            listbox.insert(pos + j, item)
        for j in range(len(itens)):
            listbox.selection_set(pos + j)
        listbox.see(pos)

    def inverter():
        itens = list(listbox.get(0, tk.END))
        listbox.delete(0, tk.END)
        for item in reversed(itens):
            listbox.insert(tk.END, item)

    def carregar_paginas():
        e = entrada_var.get().strip()
        if not e:
            messagebox.showwarning("Atenção", "Selecione o PDF primeiro."); return
        try:
            reader = PdfReader(e)
            tp = len(reader.pages)
            listbox.delete(0, tk.END)
            for i in range(tp):
                listbox.insert(tk.END, f"Página {i+1:>4}")
            log(f"📄 {tp} página(s) carregada(s). Reorganize e clique em Salvar.")
        except Exception as ex:
            messagebox.showerror("Erro", str(ex))

    tk.Button(frame_ctrl, text="▲ Subir", font=("Segoe UI", 9), width=12,
              command=mover_cima).pack(pady=(0, 4))
    tk.Button(frame_ctrl, text="▼ Descer", font=("Segoe UI", 9), width=12,
              command=mover_baixo).pack(pady=(0, 4))
    tk.Button(frame_ctrl, text="↕ Inverter", font=("Segoe UI", 9), width=12,
              command=inverter).pack(pady=(0, 10))
    tk.Label(frame_ctrl, text="Mover para\nposição:", font=("Segoe UI", 8)).pack()
    pos_var = tk.StringVar()
    tk.Entry(frame_ctrl, textvariable=pos_var, width=6, font=("Segoe UI", 9),
             justify="center").pack(pady=(2, 4))
    tk.Button(frame_ctrl, text="→ Mover", font=("Segoe UI", 9), width=12,
              command=mover_para).pack()

    tk.Button(frame, text="📥  Carregar páginas do PDF", font=("Segoe UI", 9),
              command=carregar_paginas).grid(row=6, column=0, sticky="w", pady=(0, 4))

    log_w = make_log_widget(frame, 7, height=4)
    prog = make_progress(frame, 9)
    log = lambda m: log_write(log_w, m)

    def limpar_tudo():
        entrada_var.set(""); saida_var.set(""); listbox.delete(0, tk.END)
        log_clear(log_w); prog["value"] = 0

    def processar(entrada, saida, ordem, btn):
        try:
            reader = PdfReader(entrada)
            writer = PdfWriter()
            for i, idx in enumerate(ordem):
                writer.add_page(reader.pages[idx])
                prog["value"] = int((i+1)/len(ordem)*95)
            with open(saida, "wb") as f:
                writer.write(f)
            prog["value"] = 100
            log(f"\n✅ {len(ordem)} página(s) reorganizadas.")
            log(f"📄 Salvo em: {saida}")
            messagebox.showinfo("Sucesso", f"PDF reorganizado:\n{saida}")
        except Exception as e:
            log(f"❌ Erro: {e}"); messagebox.showerror("Erro", str(e))
        btn.config(state="normal")

    def iniciar(btn):
        e = entrada_var.get().strip(); s = saida_var.get().strip()
        if not e: messagebox.showwarning("Atenção", "Selecione o PDF."); return
        if not s: messagebox.showwarning("Atenção", "Defina o arquivo de saída."); return
        if listbox.size() == 0:
            messagebox.showwarning("Atenção", "Carregue as páginas primeiro."); return
        ordem = [int(listbox.get(i).strip().split()[-1]) - 1 for i in range(listbox.size())]
        log_clear(log_w); prog["value"] = 0; btn.config(state="disabled")
        threading.Thread(target=processar, args=(e, s, ordem, btn), daemon=True).start()

    btn_limpar(frame, 10, limpar_tudo)
    b = btn_iniciar(frame, 11, "▶  Salvar PDF Reorganizado", lambda: iniciar(b))


# ══════════════════════════════════════════════════════════════════════════════
# ABA 5 — Renomear Arquivos
# ══════════════════════════════════════════════════════════════════════════════

def build_aba_renomear(nb):
    frame = ttk.Frame(nb, padding=12)
    nb.add(frame, text="  Renomear  ")

    pasta_var = tk.StringVar()
    linhas = []  # lista de (var_orig, var_novo, ext)

    # ── Seleção de pasta ou arquivos ──
    tk.Label(frame, text="Pasta ou arquivos de entrada:", font=("Segoe UI", 9)).grid(
        row=0, column=0, columnspan=3, sticky="w")
    tk.Entry(frame, textvariable=pasta_var, width=52, font=("Segoe UI", 9),
             state="readonly").grid(row=1, column=0, columnspan=2, sticky="ew", pady=(0, 4))

    fb = tk.Frame(frame)
    fb.grid(row=1, column=2, padx=(6, 0), pady=(0, 4))

    def sel_pasta():
        p = filedialog.askdirectory(title="Selecione a pasta")
        if p:
            pasta_var.set(p)
            carregar_de_pasta(p)

    def sel_arquivos():
        arqs = filedialog.askopenfilenames(title="Selecione os arquivos")
        if arqs:
            pasta_var.set(f"{len(arqs)} arquivo(s) selecionado(s)")
            carregar_lista(list(arqs))

    tk.Button(fb, text="📁 Pasta", font=("Segoe UI", 9), width=10,
              command=sel_pasta).pack(side="top", pady=(0, 2))
    tk.Button(fb, text="📄 Arquivos", font=("Segoe UI", 9), width=10,
              command=sel_arquivos).pack(side="top")

    # ── Tabela ──
    tk.Label(frame,
             text="Nome atual  (copie p/ Excel)  →  Nome novo  (cole do Excel ou digite):",
             font=("Segoe UI", 9)).grid(row=2, column=0, columnspan=3, sticky="w")

    frame_tabela = tk.Frame(frame, relief="sunken", bd=1)
    frame_tabela.grid(row=3, column=0, columnspan=3, sticky="nsew", pady=(0, 4))

    header_frame = tk.Frame(frame_tabela, bg="#0078D4")
    header_frame.pack(fill="x")
    tk.Label(header_frame, text="Nome atual", font=("Segoe UI", 9, "bold"),
             bg="#0078D4", fg="white", width=36, anchor="w", padx=4).pack(side="left")
    tk.Label(header_frame, text="Nome novo", font=("Segoe UI", 9, "bold"),
             bg="#0078D4", fg="white", width=36, anchor="w", padx=4).pack(side="left")

    canvas = tk.Canvas(frame_tabela, height=180, highlightthickness=0)
    vsb = tk.Scrollbar(frame_tabela, orient="vertical", command=canvas.yview)
    canvas.configure(yscrollcommand=vsb.set)
    vsb.pack(side="right", fill="y")
    canvas.pack(side="left", fill="both", expand=True)

    inner = tk.Frame(canvas)
    canvas_window = canvas.create_window((0, 0), window=inner, anchor="nw")

    def on_configure(e):
        canvas.configure(scrollregion=canvas.bbox("all"))
    inner.bind("<Configure>", on_configure)

    def on_canvas_resize(e):
        canvas.itemconfig(canvas_window, width=e.width)
    canvas.bind("<Configure>", on_canvas_resize)

    def preencher_tabela(nomes_com_caminho):
        for widget in inner.winfo_children():
            widget.destroy()
        linhas.clear()
        for i, (nome, _caminho) in enumerate(nomes_com_caminho):
            bg = "#ffffff" if i % 2 == 0 else "#f4f4f4"
            row_f = tk.Frame(inner, bg=bg)
            row_f.pack(fill="x")
            ext = os.path.splitext(nome)[1]
            var_orig = tk.StringVar(value=nome)
            var_novo = tk.StringVar(value="")   # começa VAZIO
            tk.Label(row_f, textvariable=var_orig, font=("Segoe UI", 9),
                     bg=bg, width=34, anchor="w", padx=4).pack(side="left")
            tk.Entry(row_f, textvariable=var_novo, font=("Segoe UI", 9), width=34).pack(
                side="left", padx=(2, 0))
            linhas.append((var_orig, var_novo, ext, _caminho))
        log(f"📂 {len(linhas)} arquivo(s) carregado(s).")

    def carregar_de_pasta(pasta):
        nomes = sorted(os.listdir(pasta))
        pares = [(n, os.path.join(pasta, n)) for n in nomes]
        preencher_tabela(pares)

    def carregar_lista(caminhos):
        pares = [(os.path.basename(c), c) for c in sorted(caminhos)]
        preencher_tabela(pares)

    # ── Botões de ação na tabela ──
    frame_btns = tk.Frame(frame)
    frame_btns.grid(row=4, column=0, columnspan=3, sticky="w", pady=(0, 4))

    def copiar_nomes_atuais():
        nomes = "\n".join(v[0].get() for v in linhas)
        if not nomes:
            messagebox.showwarning("Atenção", "Nenhum arquivo carregado."); return
        frame.clipboard_clear()
        frame.clipboard_append(nomes)
        log(f"📋 {len(linhas)} nome(s) copiado(s) para a área de transferência.")

    def colar_nomes_novos():
        try:
            texto = frame.clipboard_get()
        except tk.TclError:
            messagebox.showwarning("Atenção", "Área de transferência vazia."); return
        nomes = [l.strip() for l in texto.splitlines() if l.strip()]
        if not nomes:
            messagebox.showwarning("Atenção", "Nenhum valor encontrado."); return
        for i, nome in enumerate(nomes):
            if i >= len(linhas): break
            linhas[i][1].set(nome)
        log(f"📋 {min(len(nomes), len(linhas))} nome(s) colado(s).")

    def limpar_nomes_novos():
        for _, var_novo, _, _ in linhas:
            var_novo.set("")

    tk.Button(frame_btns, text="📋 Copiar nomes atuais", font=("Segoe UI", 9),
              command=copiar_nomes_atuais).pack(side="left", padx=(0, 6))
    tk.Button(frame_btns, text="📥 Colar nomes novos", font=("Segoe UI", 9),
              command=colar_nomes_novos).pack(side="left", padx=(0, 6))
    tk.Button(frame_btns, text="🗑 Limpar col. Nova", font=("Segoe UI", 9), fg="red",
              command=limpar_nomes_novos).pack(side="left")

    log_w = make_log_widget(frame, 5, height=4)
    log = lambda m: log_write(log_w, m)

    def limpar_tudo():
        pasta_var.set("")
        for widget in inner.winfo_children():
            widget.destroy()
        linhas.clear()
        log_clear(log_w)

    def executar_rename(btn):
        if not linhas:
            messagebox.showwarning("Atenção", "Carregue os arquivos primeiro.")
            btn.config(state="normal"); return
        erros = 0; ok = 0
        log_clear(log_w)
        for var_orig, var_novo, ext, caminho_orig in linhas:
            orig_nome = var_orig.get().strip()
            novo = var_novo.get().strip()
            if not novo:
                continue  # nome novo vazio = não renomeia
            nome_novo_completo = novo if novo.lower().endswith(ext.lower()) else novo + ext
            pasta = os.path.dirname(caminho_orig)
            src = caminho_orig
            dst = os.path.join(pasta, nome_novo_completo)
            if orig_nome == nome_novo_completo:
                continue
            try:
                if not os.path.exists(src):
                    log(f"⚠️  Não encontrado: {orig_nome}"); continue
                if os.path.exists(dst):
                    log(f"⚠️  Já existe: {nome_novo_completo}, ignorado."); continue
                os.rename(src, dst)
                log(f"✔  {orig_nome}  →  {nome_novo_completo}")
                var_orig.set(nome_novo_completo)
                # Atualiza caminho interno
                idx = linhas.index((var_orig, var_novo, ext, caminho_orig))
                linhas[idx] = (var_orig, var_novo, ext, dst)
                ok += 1
            except Exception as e:
                log(f"❌ Erro em {orig_nome}: {e}"); erros += 1
        log(f"\n✅ Concluído! {ok} renomeado(s), {erros} erro(s).")
        if ok > 0:
            messagebox.showinfo("Sucesso", f"{ok} arquivo(s) renomeado(s) com sucesso!")
        btn.config(state="normal")

    def iniciar(btn):
        btn.config(state="disabled")
        executar_rename(btn)

    btn_limpar(frame, 6, limpar_tudo)
    b = btn_iniciar(frame, 7, "▶  Renomear Arquivos", lambda: iniciar(b))


# ══════════════════════════════════════════════════════════════════════════════
# ABA 6 — Girar Páginas
# ══════════════════════════════════════════════════════════════════════════════

def build_aba_girar(nb):
    frame = ttk.Frame(nb, padding=12)
    nb.add(frame, text="  Girar Páginas  ")

    entrada_var = tk.StringVar()
    saida_var = tk.StringVar()
    paginas_var = tk.StringVar()
    angulo_var = tk.IntVar(value=90)

    row_entrada_pdf(frame, 0, "Arquivo PDF:", entrada_var)
    row_saida_pdf(frame, 2, "Salvar resultado como:", saida_var, "girado.pdf")

    tk.Label(frame, text="Páginas a girar (vazio = todas):", font=("Segoe UI", 9)).grid(
        row=4, column=0, columnspan=3, sticky="w")
    tk.Entry(frame, textvariable=paginas_var, width=30, font=("Segoe UI", 9)).grid(
        row=5, column=0, sticky="w", pady=(0, 6))

    fa = tk.LabelFrame(frame, text="  Ângulo de rotação  ", font=("Segoe UI", 9), padx=8, pady=6)
    fa.grid(row=6, column=0, columnspan=3, sticky="ew", pady=(0, 6))
    for ang in [90, 180, 270]:
        tk.Radiobutton(fa, text=f"{ang}°", variable=angulo_var, value=ang,
                       font=("Segoe UI", 9)).pack(side="left", padx=10)

    log_w = make_log_widget(frame, 7)
    prog = make_progress(frame, 9)
    log = lambda m: log_write(log_w, m)

    def limpar_tudo():
        entrada_var.set(""); saida_var.set(""); paginas_var.set(""); angulo_var.set(90)
        log_clear(log_w); prog["value"] = 0

    def processar(entrada, saida, spec, angulo, btn):
        try:
            reader = PdfReader(entrada)
            tp = len(reader.pages)
            indices = parse_paginas(spec, tp) if spec.strip() else list(range(tp))
            if indices is None:
                messagebox.showerror("Erro", "Formato de páginas inválido.")
                btn.config(state="normal"); return
            writer = PdfWriter()
            for i in range(tp):
                page = reader.pages[i]
                if i in indices:
                    page.rotate(angulo)
                writer.add_page(page)
                prog["value"] = int((i+1)/tp*95)
            with open(saida, "wb") as f:
                writer.write(f)
            prog["value"] = 100
            log(f"✅ {len(indices)} página(s) girada(s) {angulo}°.")
            log(f"📄 Salvo em: {saida}")
            messagebox.showinfo("Sucesso", f"PDF salvo:\n{saida}")
        except Exception as e:
            log(f"❌ Erro: {e}"); messagebox.showerror("Erro", str(e))
        btn.config(state="normal")

    def iniciar(btn):
        e = entrada_var.get().strip(); s = saida_var.get().strip()
        if not e: messagebox.showwarning("Atenção", "Selecione o PDF."); return
        if not s: messagebox.showwarning("Atenção", "Defina o arquivo de saída."); return
        log_clear(log_w); prog["value"] = 0; btn.config(state="disabled")
        threading.Thread(target=processar,
                         args=(e, s, paginas_var.get().strip(), angulo_var.get(), btn),
                         daemon=True).start()

    btn_limpar(frame, 10, limpar_tudo)
    b = btn_iniciar(frame, 11, "▶  Girar", lambda: iniciar(b))


# ══════════════════════════════════════════════════════════════════════════════
# ABA 7 — Proteger / Desproteger
# ══════════════════════════════════════════════════════════════════════════════

def build_aba_senha(nb):
    frame = ttk.Frame(nb, padding=12)
    nb.add(frame, text="  Senha  ")

    entrada_var = tk.StringVar()
    saida_var = tk.StringVar()
    senha_var = tk.StringVar()
    conf_var = tk.StringVar()
    acao_var = tk.IntVar(value=1)
    senha_atual_var = tk.StringVar()

    row_entrada_pdf(frame, 0, "Arquivo PDF:", entrada_var)
    row_saida_pdf(frame, 2, "Salvar resultado como:", saida_var, "protegido.pdf")

    fa = tk.LabelFrame(frame, text="  Ação  ", font=("Segoe UI", 9), padx=8, pady=6)
    fa.grid(row=4, column=0, columnspan=3, sticky="ew", pady=(4, 6))

    def atualizar_acao(*_):
        if acao_var.get() == 1:
            frame_prot.grid(); frame_desprot.grid_remove()
        else:
            frame_prot.grid_remove(); frame_desprot.grid()

    tk.Radiobutton(fa, text="Adicionar senha", variable=acao_var, value=1,
                   font=("Segoe UI", 9), command=atualizar_acao).pack(side="left", padx=10)
    tk.Radiobutton(fa, text="Remover senha", variable=acao_var, value=2,
                   font=("Segoe UI", 9), command=atualizar_acao).pack(side="left", padx=10)

    frame_prot = tk.Frame(frame)
    frame_prot.grid(row=5, column=0, columnspan=3, sticky="ew")
    tk.Label(frame_prot, text="Nova senha:", font=("Segoe UI", 9)).grid(row=0, column=0, sticky="w")
    tk.Entry(frame_prot, textvariable=senha_var, show="*", width=30, font=("Segoe UI", 9)).grid(
        row=1, column=0, sticky="w", pady=(0, 4))
    tk.Label(frame_prot, text="Confirmar senha:", font=("Segoe UI", 9)).grid(row=2, column=0, sticky="w")
    tk.Entry(frame_prot, textvariable=conf_var, show="*", width=30, font=("Segoe UI", 9)).grid(
        row=3, column=0, sticky="w", pady=(0, 4))

    frame_desprot = tk.Frame(frame)
    frame_desprot.grid(row=5, column=0, columnspan=3, sticky="ew")
    frame_desprot.grid_remove()
    tk.Label(frame_desprot, text="Senha atual do PDF:", font=("Segoe UI", 9)).grid(row=0, column=0, sticky="w")
    tk.Entry(frame_desprot, textvariable=senha_atual_var, show="*", width=30, font=("Segoe UI", 9)).grid(
        row=1, column=0, sticky="w", pady=(0, 4))

    log_w = make_log_widget(frame, 6, height=5)
    prog = make_progress(frame, 8)
    log = lambda m: log_write(log_w, m)

    def limpar_tudo():
        entrada_var.set(""); saida_var.set(""); senha_var.set("")
        conf_var.set(""); senha_atual_var.set(""); acao_var.set(1); atualizar_acao()
        log_clear(log_w); prog["value"] = 0

    def processar(entrada, saida, acao, senha, conf, senha_atual, btn):
        try:
            reader = PdfReader(entrada)
            if reader.is_encrypted:
                if not reader.decrypt(senha_atual):
                    messagebox.showerror("Erro", "Senha incorreta.")
                    btn.config(state="normal"); return
            writer = PdfWriter()
            for page in reader.pages:
                writer.add_page(page)
            if acao == 1:
                if senha != conf:
                    messagebox.showerror("Erro", "As senhas não coincidem.")
                    btn.config(state="normal"); return
                if len(senha) < 4:
                    messagebox.showerror("Erro", "A senha deve ter ao menos 4 caracteres.")
                    btn.config(state="normal"); return
                writer.encrypt(senha)
                log("🔒 Senha adicionada.")
            else:
                log("🔓 Senha removida.")
            with open(saida, "wb") as f:
                writer.write(f)
            prog["value"] = 100
            log(f"📄 Salvo em: {saida}")
            messagebox.showinfo("Sucesso", f"PDF salvo:\n{saida}")
        except Exception as e:
            log(f"❌ Erro: {e}"); messagebox.showerror("Erro", str(e))
        btn.config(state="normal")

    def iniciar(btn):
        e = entrada_var.get().strip(); s = saida_var.get().strip(); a = acao_var.get()
        if not e: messagebox.showwarning("Atenção", "Selecione o PDF."); return
        if not s: messagebox.showwarning("Atenção", "Defina o arquivo de saída."); return
        if a == 1 and not senha_var.get():
            messagebox.showwarning("Atenção", "Informe a senha."); return
        log_clear(log_w); prog["value"] = 0; btn.config(state="disabled")
        threading.Thread(target=processar,
                         args=(e, s, a, senha_var.get(), conf_var.get(),
                               senha_atual_var.get(), btn),
                         daemon=True).start()

    btn_limpar(frame, 9, limpar_tudo)
    b = btn_iniciar(frame, 10, "▶  Executar", lambda: iniciar(b))


# ══════════════════════════════════════════════════════════════════════════════
# ABA 8 — Informações do PDF
# ══════════════════════════════════════════════════════════════════════════════

def build_aba_info(nb):
    frame = ttk.Frame(nb, padding=12)
    nb.add(frame, text="  Informações  ")

    entrada_var = tk.StringVar()
    row_entrada_pdf(frame, 0, "Arquivo PDF:", entrada_var)

    info_widget = tk.Text(frame, height=16, width=65, font=("Consolas", 9),
                          state="disabled", bg="#f4f4f4")
    info_widget.grid(row=2, column=0, columnspan=3, pady=(10, 6))

    def limpar_tudo():
        entrada_var.set("")
        info_widget.config(state="normal")
        info_widget.delete("1.0", tk.END)
        info_widget.config(state="disabled")

    def mostrar(entrada):
        info_widget.config(state="normal")
        info_widget.delete("1.0", tk.END)
        try:
            reader = PdfReader(entrada)
            tp = len(reader.pages)
            tam = os.path.getsize(entrada)
            tam_str = f"{tam/1024:.1f} KB" if tam < 1024*1024 else f"{tam/1024/1024:.2f} MB"
            meta = reader.metadata or {}
            linhas = [
                f"📄 Arquivo:       {os.path.basename(entrada)}",
                f"📁 Caminho:       {entrada}",
                f"📏 Tamanho:       {tam_str}",
                f"📑 Páginas:       {tp}",
                f"🔒 Criptografado: {'Sim' if reader.is_encrypted else 'Não'}",
                "",
                "── Metadados ──────────────────────────────",
                f"Título:          {meta.get('/Title', '—')}",
                f"Autor:           {meta.get('/Author', '—')}",
                f"Assunto:         {meta.get('/Subject', '—')}",
                f"Criador:         {meta.get('/Creator', '—')}",
                f"Produtor:        {meta.get('/Producer', '—')}",
                f"Criado em:       {meta.get('/CreationDate', '—')}",
                f"Modificado em:   {meta.get('/ModDate', '—')}",
                "",
                "── Tamanho das páginas ────────────────────",
            ]
            for i, page in enumerate(reader.pages):
                w = float(page.mediabox.width)
                h = float(page.mediabox.height)
                linhas.append(f"  Pág. {i+1:>3}: {w:.0f} x {h:.0f} pts  "
                              f"({w/72*2.54:.1f} x {h/72*2.54:.1f} cm)")
            info_widget.insert(tk.END, "\n".join(linhas))
        except Exception as e:
            info_widget.insert(tk.END, f"❌ Erro ao ler o arquivo:\n{e}")
        info_widget.config(state="disabled")

    def analisar():
        e = entrada_var.get().strip()
        if not e: messagebox.showwarning("Atenção", "Selecione um PDF."); return
        mostrar(e)

    btn_limpar(frame, 3, limpar_tudo)
    btn_iniciar(frame, 4, "🔍  Analisar PDF", analisar)


# ══════════════════════════════════════════════════════════════════════════════
# JANELA PRINCIPAL
# ══════════════════════════════════════════════════════════════════════════════

root = tk.Tk()
root.title("Gerenciador de PDFs")
root.resizable(False, False)
root.configure(padx=4, pady=4)

header = tk.Frame(root, bg="#0078D4", padx=14, pady=10)
header.pack(fill="x")
tk.Label(header, text="📄  Gerenciador de PDFs", font=("Segoe UI", 15, "bold"),
         bg="#0078D4", fg="white").pack(side="left")

style = ttk.Style()
style.theme_use("default")
style.configure("TNotebook.Tab", font=("Segoe UI", 9), padding=[10, 4])

nb = ttk.Notebook(root)
nb.pack(fill="both", expand=True, padx=6, pady=6)

build_aba_extrair(nb)
build_aba_excluir(nb)
build_aba_dividir(nb)
build_aba_reorganizar(nb)
build_aba_renomear(nb)
build_aba_girar(nb)
build_aba_senha(nb)
build_aba_info(nb)

root.mainloop()
