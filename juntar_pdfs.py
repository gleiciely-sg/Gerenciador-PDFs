"""
Gerenciador de PDFs
Funcionalidades:
  - Extrair/Juntar páginas
  - Excluir páginas
  - Dividir PDF
  - Reorganizar páginas
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
    b.grid(row=row, column=0, columnspan=3, pady=(4, 0))
    return b


# ══════════════════════════════════════════════════════════════════════════════
# ABA 1 — Extrair / Juntar
# ══════════════════════════════════════════════════════════════════════════════

def build_aba_extrair(nb):
    frame = ttk.Frame(nb, padding=12)
    nb.add(frame, text="  Extrair / Juntar  ")

    # Modo
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

    # Entrada
    arqs_sel = []
    tipo_var = tk.StringVar(value="pasta")
    entrada_var = tk.StringVar()

    def adicionar_arquivos():
        arqs = filedialog.askopenfilenames(title="Selecionar PDFs", filetypes=[("PDF","*.pdf")])
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

    def limpar():
        arqs_sel.clear()
        tipo_var.set("pasta")
        entrada_var.set("")

    tk.Label(frame, text="Entrada (pasta ou arquivos):", font=("Segoe UI", 9)).grid(
        row=1, column=0, columnspan=3, sticky="w")
    tk.Entry(frame, textvariable=entrada_var, width=52, font=("Segoe UI", 9),
             state="readonly").grid(row=2, column=0, columnspan=2, sticky="ew", pady=(0, 2))
    fb = tk.Frame(frame)
    fb.grid(row=2, column=2, padx=(6,0), pady=(0,2))
    tk.Button(fb, text="📁 Pasta", font=("Segoe UI", 9), width=10,
              command=sel_pasta).pack(side="top", pady=(0,2))
    tk.Button(fb, text="📄 + Arquivos", font=("Segoe UI", 9), width=10,
              command=adicionar_arquivos).pack(side="top", pady=(0,2))
    tk.Button(fb, text="🗑 Limpar", font=("Segoe UI", 9), width=10, fg="red",
              command=limpar).pack(side="top")

    # Saída
    row_pasta(frame, 3, "Pasta de saída:", saida_var := tk.StringVar())

    # Nome arquivo final
    lnome = tk.Label(frame, text="Nome do arquivo final:", font=("Segoe UI", 9))
    lnome.grid(row=5, column=0, columnspan=3, sticky="w")
    nome_var = tk.StringVar(value="Arquivo_Final.pdf")
    enome = tk.Entry(frame, textvariable=nome_var, width=52, font=("Segoe UI", 9))
    enome.grid(row=6, column=0, columnspan=2, sticky="ew", pady=(0, 4))

    # Páginas
    fp = tk.LabelFrame(frame, text="  Páginas a extrair  ", font=("Segoe UI", 9), padx=8, pady=6)
    fp.grid(row=7, column=0, columnspan=3, sticky="ew", pady=(4, 6))
    tk.Label(fp, text="Ex.: 1 | 1,3 | 2-4 | 1-3,5,7-9  —  vazio = todas as páginas",
             font=("Segoe UI", 9)).grid(row=0, column=0, sticky="w")
    paginas_var = tk.StringVar(value="")
    tk.Entry(fp, textvariable=paginas_var, width=30, font=("Segoe UI", 9)).grid(
        row=1, column=0, sticky="w", pady=(4,0))

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
                    log(f"⚠️  Vazio: {nome}")
                    continue
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
            log(f"   • Individuais: {pasta_saida}\n   • Unido: {arquivo_final}")
            messagebox.showinfo("Sucesso", f"{ok} individual(is) + arquivo unido:\n{arquivo_final}")
        elif modo == 2:
            log(f"   • Individuais: {pasta_saida}")
            messagebox.showinfo("Sucesso", f"{ok} arquivo(s) salvo(s) em:\n{pasta_saida}")
        else:
            log(f"   • Unido: {arquivo_final}")
            messagebox.showinfo("Sucesso", f"Arquivo unido:\n{arquivo_final}")
        btn.config(state="normal")

    def iniciar(btn):
        entrada = entrada_var.get().strip()
        saida = saida_var.get().strip()
        spec = paginas_var.get().strip()
        modo = modo_var.get()
        nome = nome_var.get().strip()
        if not entrada:
            messagebox.showwarning("Atenção", "Selecione a entrada."); return
        if not saida:
            messagebox.showwarning("Atenção", "Selecione a pasta de saída."); return
        if modo in (1,3) and not nome:
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

    b = btn_iniciar(frame, 11, "▶  Iniciar", lambda: iniciar(b))


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
            log(f"✅ Concluído! {len(excluir)} página(s) excluída(s), {len(manter)} mantida(s).")
            log(f"📄 Salvo em: {saida}")
            messagebox.showinfo("Sucesso", f"PDF salvo com {len(manter)} página(s):\n{saida}")
        except Exception as e:
            log(f"❌ Erro: {e}")
            messagebox.showerror("Erro", str(e))
        btn.config(state="normal")

    def iniciar(btn):
        e = entrada_var.get().strip()
        s = saida_var.get().strip()
        p = paginas_var.get().strip()
        if not e: messagebox.showwarning("Atenção", "Selecione o PDF de entrada."); return
        if not s: messagebox.showwarning("Atenção", "Defina o arquivo de saída."); return
        if not p: messagebox.showwarning("Atenção", "Informe as páginas a excluir."); return
        log_clear(log_w); prog["value"] = 0; btn.config(state="disabled")
        threading.Thread(target=processar, args=(e, s, p, btn), daemon=True).start()

    b = btn_iniciar(frame, 9, "▶  Excluir Páginas", lambda: iniciar(b))


# ══════════════════════════════════════════════════════════════════════════════
# ABA 3 — Dividir PDF
# ══════════════════════════════════════════════════════════════════════════════

def build_aba_dividir(nb):
    frame = ttk.Frame(nb, padding=12)
    nb.add(frame, text="  Dividir PDF  ")

    entrada_var = tk.StringVar()
    saida_var = tk.StringVar()
    modo_var = tk.IntVar(value=1)

    row_entrada_pdf(frame, 0, "Arquivo PDF:", entrada_var)
    row_pasta(frame, 2, "Pasta de saída:", saida_var)

    fm = tk.LabelFrame(frame, text="  Modo de divisão  ", font=("Segoe UI", 9), padx=8, pady=6)
    fm.grid(row=4, column=0, columnspan=3, sticky="ew", pady=(4, 6))
    tk.Radiobutton(fm, text="1 página por arquivo", variable=modo_var, value=1,
                   font=("Segoe UI", 9)).grid(row=0, column=0, sticky="w")
    tk.Radiobutton(fm, text="Intervalos personalizados (ex.: 1-3,4-6,7)",
                   variable=modo_var, value=2, font=("Segoe UI", 9)).grid(row=1, column=0, sticky="w")
    intervalos_var = tk.StringVar()
    tk.Entry(fm, textvariable=intervalos_var, width=35, font=("Segoe UI", 9)).grid(
        row=2, column=0, sticky="w", pady=(4, 0))

    log_w = make_log_widget(frame, 5)
    prog = make_progress(frame, 7)
    log = lambda m: log_write(log_w, m)

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
            messagebox.showinfo("Sucesso", f"PDF dividido com sucesso!\n{saida}")
        except Exception as e:
            log(f"❌ Erro: {e}")
            messagebox.showerror("Erro", str(e))
        btn.config(state="normal")

    def iniciar(btn):
        e = entrada_var.get().strip()
        s = saida_var.get().strip()
        m = modo_var.get()
        iv = intervalos_var.get().strip()
        if not e: messagebox.showwarning("Atenção", "Selecione o PDF."); return
        if not s: messagebox.showwarning("Atenção", "Selecione a pasta de saída."); return
        if m == 2 and not iv: messagebox.showwarning("Atenção", "Informe os intervalos."); return
        log_clear(log_w); prog["value"] = 0; btn.config(state="disabled")
        threading.Thread(target=processar, args=(e, s, m, iv, btn), daemon=True).start()

    b = btn_iniciar(frame, 8, "▶  Dividir", lambda: iniciar(b))


# ══════════════════════════════════════════════════════════════════════════════
# ABA 4 — Reorganizar Páginas
# ══════════════════════════════════════════════════════════════════════════════

def build_aba_reorganizar(nb):
    frame = ttk.Frame(nb, padding=12)
    nb.add(frame, text="  Reorganizar  ")

    entrada_var = tk.StringVar()
    saida_var = tk.StringVar()
    ordem_var = tk.StringVar()

    row_entrada_pdf(frame, 0, "Arquivo PDF:", entrada_var)
    row_saida_pdf(frame, 2, "Salvar resultado como:", saida_var, "reorganizado.pdf")

    tk.Label(frame,
             text="Nova ordem das páginas (ex.: 3,1,2 | 2-4,1 | inverter com 3,2,1):",
             font=("Segoe UI", 9)).grid(row=4, column=0, columnspan=3, sticky="w")
    tk.Entry(frame, textvariable=ordem_var, width=40, font=("Segoe UI", 9)).grid(
        row=5, column=0, columnspan=2, sticky="w", pady=(0, 6))

    log_w = make_log_widget(frame, 6)
    prog = make_progress(frame, 8)
    log = lambda m: log_write(log_w, m)

    def processar(entrada, saida, ordem, btn):
        try:
            reader = PdfReader(entrada)
            tp = len(reader.pages)
            indices = parse_paginas(ordem, tp)
            if indices is None:
                messagebox.showerror("Erro", "Ordem inválida. Verifique os números de página.")
                btn.config(state="normal"); return
            writer = PdfWriter()
            for i, idx in enumerate(indices):
                writer.add_page(reader.pages[idx])
                prog["value"] = int((i+1)/len(indices)*95)
                log(f"✔  Posição {i+1} ← página original {idx+1}")
            with open(saida, "wb") as f:
                writer.write(f)
            prog["value"] = 100
            log(f"\n✅ Concluído! {len(indices)} página(s) reorganizadas.")
            log(f"📄 Salvo em: {saida}")
            messagebox.showinfo("Sucesso", f"PDF reorganizado:\n{saida}")
        except Exception as e:
            log(f"❌ Erro: {e}")
            messagebox.showerror("Erro", str(e))
        btn.config(state="normal")

    def iniciar(btn):
        e = entrada_var.get().strip()
        s = saida_var.get().strip()
        o = ordem_var.get().strip()
        if not e: messagebox.showwarning("Atenção", "Selecione o PDF."); return
        if not s: messagebox.showwarning("Atenção", "Defina o arquivo de saída."); return
        if not o: messagebox.showwarning("Atenção", "Informe a nova ordem das páginas."); return
        log_clear(log_w); prog["value"] = 0; btn.config(state="disabled")
        threading.Thread(target=processar, args=(e, s, o, btn), daemon=True).start()

    b = btn_iniciar(frame, 9, "▶  Reorganizar", lambda: iniciar(b))


# ══════════════════════════════════════════════════════════════════════════════
# ABA 5 — Girar Páginas
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
            log(f"❌ Erro: {e}")
            messagebox.showerror("Erro", str(e))
        btn.config(state="normal")

    def iniciar(btn):
        e = entrada_var.get().strip()
        s = saida_var.get().strip()
        p = paginas_var.get().strip()
        a = angulo_var.get()
        if not e: messagebox.showwarning("Atenção", "Selecione o PDF."); return
        if not s: messagebox.showwarning("Atenção", "Defina o arquivo de saída."); return
        log_clear(log_w); prog["value"] = 0; btn.config(state="disabled")
        threading.Thread(target=processar, args=(e, s, p, a, btn), daemon=True).start()

    b = btn_iniciar(frame, 10, "▶  Girar", lambda: iniciar(b))


# ══════════════════════════════════════════════════════════════════════════════
# ABA 6 — Proteger / Desproteger
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

    # Proteger
    frame_prot = tk.Frame(frame)
    frame_prot.grid(row=5, column=0, columnspan=3, sticky="ew")
    tk.Label(frame_prot, text="Nova senha:", font=("Segoe UI", 9)).grid(row=0, column=0, sticky="w")
    tk.Entry(frame_prot, textvariable=senha_var, show="*", width=30, font=("Segoe UI", 9)).grid(
        row=1, column=0, sticky="w", pady=(0, 4))
    tk.Label(frame_prot, text="Confirmar senha:", font=("Segoe UI", 9)).grid(row=2, column=0, sticky="w")
    tk.Entry(frame_prot, textvariable=conf_var, show="*", width=30, font=("Segoe UI", 9)).grid(
        row=3, column=0, sticky="w", pady=(0, 4))

    # Desproteger
    frame_desprot = tk.Frame(frame)
    frame_desprot.grid(row=5, column=0, columnspan=3, sticky="ew")
    frame_desprot.grid_remove()
    tk.Label(frame_desprot, text="Senha atual do PDF:", font=("Segoe UI", 9)).grid(row=0, column=0, sticky="w")
    tk.Entry(frame_desprot, textvariable=senha_atual_var, show="*", width=30, font=("Segoe UI", 9)).grid(
        row=1, column=0, sticky="w", pady=(0, 4))

    log_w = make_log_widget(frame, 6, height=5)
    prog = make_progress(frame, 8)
    log = lambda m: log_write(log_w, m)

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
                log("🔒 Senha adicionada com sucesso.")
            else:
                log("🔓 Senha removida com sucesso.")
            with open(saida, "wb") as f:
                writer.write(f)
            prog["value"] = 100
            log(f"📄 Salvo em: {saida}")
            messagebox.showinfo("Sucesso", f"PDF salvo:\n{saida}")
        except Exception as e:
            log(f"❌ Erro: {e}")
            messagebox.showerror("Erro", str(e))
        btn.config(state="normal")

    def iniciar(btn):
        e = entrada_var.get().strip()
        s = saida_var.get().strip()
        a = acao_var.get()
        if not e: messagebox.showwarning("Atenção", "Selecione o PDF."); return
        if not s: messagebox.showwarning("Atenção", "Defina o arquivo de saída."); return
        if a == 1 and not senha_var.get():
            messagebox.showwarning("Atenção", "Informe a senha."); return
        log_clear(log_w); prog["value"] = 0; btn.config(state="disabled")
        threading.Thread(target=processar,
                         args=(e, s, a, senha_var.get(), conf_var.get(),
                               senha_atual_var.get(), btn),
                         daemon=True).start()

    b = btn_iniciar(frame, 9, "▶  Executar", lambda: iniciar(b))


# ══════════════════════════════════════════════════════════════════════════════
# ABA 7 — Informações do PDF
# ══════════════════════════════════════════════════════════════════════════════

def build_aba_info(nb):
    frame = ttk.Frame(nb, padding=12)
    nb.add(frame, text="  Informações  ")

    entrada_var = tk.StringVar()
    row_entrada_pdf(frame, 0, "Arquivo PDF:", entrada_var)

    info_widget = tk.Text(frame, height=16, width=65, font=("Consolas", 9),
                          state="disabled", bg="#f4f4f4")
    info_widget.grid(row=2, column=0, columnspan=3, pady=(10, 6))

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
                f"📄 Arquivo:      {os.path.basename(entrada)}",
                f"📁 Caminho:      {entrada}",
                f"📏 Tamanho:      {tam_str}",
                f"📑 Páginas:      {tp}",
                f"🔒 Criptografado: {'Sim' if reader.is_encrypted else 'Não'}",
                "",
                "── Metadados ──────────────────────────────",
                f"Título:         {meta.get('/Title', '—')}",
                f"Autor:          {meta.get('/Author', '—')}",
                f"Assunto:        {meta.get('/Subject', '—')}",
                f"Criador:        {meta.get('/Creator', '—')}",
                f"Produtor:       {meta.get('/Producer', '—')}",
                f"Criado em:      {meta.get('/CreationDate', '—')}",
                f"Modificado em:  {meta.get('/ModDate', '—')}",
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
        if not e:
            messagebox.showwarning("Atenção", "Selecione um PDF."); return
        mostrar(e)

    btn_iniciar(frame, 3, "🔍  Analisar PDF", analisar)


# ══════════════════════════════════════════════════════════════════════════════
# JANELA PRINCIPAL
# ══════════════════════════════════════════════════════════════════════════════

root = tk.Tk()
root.title("Gerenciador de PDFs")
root.resizable(False, False)
root.configure(padx=4, pady=4)

# Cabeçalho
header = tk.Frame(root, bg="#0078D4", padx=14, pady=10)
header.pack(fill="x")
tk.Label(header, text="📄  Gerenciador de PDFs", font=("Segoe UI", 15, "bold"),
         bg="#0078D4", fg="white").pack(side="left")

# Notebook
style = ttk.Style()
style.theme_use("default")
style.configure("TNotebook.Tab", font=("Segoe UI", 9), padding=[10, 4])

nb = ttk.Notebook(root)
nb.pack(fill="both", expand=True, padx=6, pady=6)

build_aba_extrair(nb)
build_aba_excluir(nb)
build_aba_dividir(nb)
build_aba_reorganizar(nb)
build_aba_girar(nb)
build_aba_senha(nb)
build_aba_info(nb)

root.mainloop()
