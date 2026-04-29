import tkinter as tk
from tkinter import ttk, messagebox, filedialog
from datetime import datetime, date
import re
import sqlite3
import random
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib import colors
from reportlab.lib.units import cm
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_CENTER

# --- CONFIGURAÇÕES DE CORES E FONTES ---
BG    = "#081122"
BG2   = "#141414"
BG3   = "#1e1e1e"
AZUL  = "#1565C0"
AZUL2 = "#1976D2"
VERM  = "#C62828"
BRAN  = "#FFFFFF"
CINZA = "#9E9E9E"
FONT  = ("Arial", 10)
FONTB = ("Arial", 10, "bold")
FONTH = ("Arial", 14, "bold")

# --- BANCO DE DADOS ---
conexao = sqlite3.connect("estacionamento.db")
cursor = conexao.cursor()

cursor.executescript("""
CREATE TABLE IF NOT EXISTS clientes (
    id    INTEGER PRIMARY KEY AUTOINCREMENT,
    nome  TEXT    NOT NULL,
    cpf   TEXT    NOT NULL UNIQUE,
    placa TEXT    NOT NULL,
    tipo  TEXT    NOT NULL DEFAULT 'rotativo'
);

CREATE TABLE IF NOT EXISTS movimentacoes (
    id      INTEGER PRIMARY KEY AUTOINCREMENT,
    placa   TEXT    NOT NULL,
    data    TEXT    NOT NULL,
    entrada TEXT    NOT NULL,
    saida   TEXT,
    valor   REAL    DEFAULT 0.0,
    pago    INTEGER DEFAULT 0,
    vaga    INTEGER DEFAULT NULL,
    FOREIGN KEY (placa) REFERENCES clientes(placa)
);

CREATE TABLE IF NOT EXISTS config_financeiro (
    id            INTEGER PRIMARY KEY DEFAULT 1,
    unidade       TEXT    NOT NULL DEFAULT 'hora',
    valor_rotativo REAL   NOT NULL DEFAULT 5.0,
    valor_diarista REAL   NOT NULL DEFAULT 30.0,
    valor_mensalista REAL NOT NULL DEFAULT 200.0,
    limite_rotativo_horas INTEGER NOT NULL DEFAULT 12
);

CREATE TABLE IF NOT EXISTS contratos (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    placa        TEXT    NOT NULL,
    tipo         TEXT    NOT NULL,
    data_inicio  TEXT    NOT NULL,
    data_fim     TEXT,
    dias_semana  TEXT,
    valor        REAL    NOT NULL DEFAULT 0.0,
    pago         INTEGER DEFAULT 0,
    ativo        INTEGER DEFAULT 1
);
""")
conexao.commit()

TOTAL_VAGAS = 20

# Migrações seguras
for migration in [
    "ALTER TABLE movimentacoes ADD COLUMN vaga INTEGER DEFAULT NULL",
    "ALTER TABLE clientes ADD COLUMN tipo TEXT NOT NULL DEFAULT 'rotativo'",
]:
    try:
        cursor.execute(migration)
        conexao.commit()
    except Exception:
        pass

# Garante config padrão
cursor.execute("INSERT OR IGNORE INTO config_financeiro (id) VALUES (1)")
conexao.commit()

def get_config():
    cursor.execute("SELECT unidade, valor_rotativo, valor_diarista, valor_mensalista, limite_rotativo_horas FROM config_financeiro WHERE id=1")
    row = cursor.fetchone()
    if row:
        return {"unidade": row[0], "valor_rotativo": row[1], "valor_diarista": row[2],
                "valor_mensalista": row[3], "limite_rotativo_horas": row[4]}
    return {"unidade": "hora", "valor_rotativo": 5.0, "valor_diarista": 30.0,
            "valor_mensalista": 200.0, "limite_rotativo_horas": 12}

# --- JANELA PRINCIPAL ---
janela = tk.Tk()
janela.title("estaciON")
janela.geometry("1280x720")
janela.configure(bg=BG)

# --- ESTILIZAÇÃO ---
style = ttk.Style()
style.theme_use('default')
style.configure("TNotebook", background=BG, borderwidth=0)
style.configure("TNotebook.Tab", background=BG3, foreground=BRAN, padding=[10, 5], font=FONTB)
style.map("TNotebook.Tab", background=[("selected", AZUL)], foreground=[("selected", BRAN)])
style.configure("TFrame", background=BG)
style.configure("Treeview",
    background=BG2, foreground=BRAN, fieldbackground=BG2,
    rowheight=28, font=FONT, borderwidth=0
)
style.configure("Treeview.Heading",
    background=BG3, foreground=AZUL, font=FONTB, relief="flat"
)
style.map("Treeview",
    background=[("selected", AZUL)],
    foreground=[("selected", BRAN)]
)
style.map("Treeview.Heading",
    background=[("active", AZUL2)]
)

style.configure("Sub.TNotebook", background=BG, borderwidth=0)
style.configure("Sub.TNotebook.Tab", background=BG3, foreground=BRAN, padding=[10, 5], font=FONTB)
style.map("Sub.TNotebook.Tab", background=[("selected", AZUL)], foreground=[("selected", BRAN)])
style.layout("Sub.TNotebook", [("Sub.TNotebook.client", {"sticky": "nswe"})])

abas = ttk.Notebook(janela)
abas.pack(expand=True, fill="both", padx=10, pady=10)

# ===========================================================
# --- FUNÇÕES DE VALIDAÇÃO ---
# ===========================================================

def validar_cpf(cpf):
    cpf = re.sub(r'\D', '', cpf)
    if len(cpf) != 11 or cpf == cpf[0] * 11:
        return False
    soma = sum(int(cpf[i]) * (10 - i) for i in range(9))
    dig1 = (soma * 10 % 11) % 10
    soma = sum(int(cpf[i]) * (11 - i) for i in range(10))
    dig2 = (soma * 10 % 11) % 10
    return cpf[-2:] == f"{dig1}{dig2}"

def validar_placa(placa):
    placa = placa.upper()
    padrao_antigo   = r'^[A-Z]{3}[0-9]{4}$'
    padrao_mercosul = r'^[A-Z]{3}[0-9][A-Z][0-9]{2}$'
    return re.match(padrao_antigo, placa) or re.match(padrao_mercosul, placa)

def limpar_placa(placa):
    return placa.upper().replace("-", "").strip()

def formatar_placa_exibicao(placa):
    placa = limpar_placa(placa)
    if len(placa) >= 7:
        return placa[:3] + "-" + placa[3:]
    return placa

def mascara_placa(event):
    widget = event.widget
    texto_original = widget.get()
    pos_original = widget.index(tk.INSERT)
    texto = texto_original.upper().replace("-", "")
    texto = texto[:7]
    if len(texto) >= 5 and texto[4].isalpha():
        novo = texto
        tem_hifen = False
    else:
        if len(texto) > 3:
            novo = texto[:3] + "-" + texto[3:]
            tem_hifen = True
        else:
            novo = texto
            tem_hifen = False
    widget.delete(0, tk.END)
    widget.insert(0, novo)
    nova_pos = pos_original
    if tem_hifen and pos_original == 4:
        nova_pos += 1
    if not tem_hifen and "-" in texto_original and pos_original > 3:
        nova_pos -= 1
    try:
        widget.icursor(nova_pos)
    except Exception:
        pass

def formatar_data(event):
    texto = entrada_data.get().replace("/", "")[:8]
    if len(texto) >= 4:
        novo = texto[:4] + "/"
        if len(texto) >= 6:
            novo += texto[4:6] + "/" + texto[6:8]
        else:
            novo += texto[4:6]
    else:
        novo = texto
    entrada_data.delete(0, tk.END)
    entrada_data.insert(0, novo)

def formatar_hora(event):
    widget = event.widget
    texto = widget.get().replace(":", "")[:4]
    if len(texto) >= 3:
        texto = texto[:2] + ":" + texto[2:]
    widget.delete(0, tk.END)
    widget.insert(0, texto)

def atualizar_hora():
    agora = datetime.now().strftime("%H:%M")
    entrada_hora_in.delete(0, tk.END)
    entrada_hora_in.insert(0, agora)
    janela.after(1000, atualizar_hora)

def calcular_valor_rotativo(hora_in, hora_out):
    cfg = get_config()
    try:
        h_in,  m_in  = map(int, hora_in.split(":"))
        h_out, m_out = map(int, hora_out.split(":"))
        minutos = (h_out * 60 + m_out) - (h_in * 60 + m_in)
        if minutos < 0:
            minutos += 24 * 60
        if cfg["unidade"] == "hora":
            valor = round((minutos / 60) * cfg["valor_rotativo"], 2)
        else:  # 30 minutos
            valor = round((minutos / 30) * cfg["valor_rotativo"], 2)
        return valor
    except ValueError:
        return 0.0

# ===========================================================
# --- FUNÇÕES DO SISTEMA ---
# ===========================================================

def salvar():
    nome  = entrada_nomeCliente.get().strip()
    cpf   = re.sub(r'\D', '', entrada_cpf.get())
    placa = limpar_placa(entrada_placaVeiculo.get())
    tipo  = var_tipo_cliente.get()

    if not nome:
        messagebox.showerror("Erro", "Preencha o nome do cliente.")
        return
    if not validar_cpf(cpf):
        messagebox.showerror("Erro", "CPF inválido")
        return
    if not validar_placa(placa):
        messagebox.showerror("Erro", "Placa inválida")
        return

    cursor.execute("SELECT id FROM clientes WHERE cpf = ?", (cpf,))
    if cursor.fetchone():
        messagebox.showerror("Erro", "Este CPF já está cadastrado.")
        return

    cursor.execute("INSERT INTO clientes (nome, cpf, placa, tipo) VALUES (?, ?, ?, ?)", (nome, cpf, placa, tipo))
    conexao.commit()
    messagebox.showinfo("Sucesso", "Cliente registrado com sucesso")

    entrada_nomeCliente.delete(0, tk.END)
    entrada_cpf.delete(0, tk.END)
    entrada_placaVeiculo.delete(0, tk.END)
    var_tipo_cliente.set("rotativo")
    carregar_tabela_clientes_cad()
    carregar_cards_clientes()

def excluir_cliente():
    selecionado = tabela_clientes_cad.selection()
    if not selecionado:
        messagebox.showwarning("Atenção", "Selecione um cliente na lista para excluir.")
        return
    item   = tabela_clientes_cad.item(selecionado[0])
    nome   = item["values"][0]
    cpf    = re.sub(r'\D', '', str(item["values"][1]))
    if not messagebox.askyesno("Confirmar exclusão",
                               f"Deseja excluir o cliente '{nome}'?\nAs movimentações vinculadas serão mantidas."):
        return
    try:
        cursor.execute("DELETE FROM clientes WHERE cpf = ?", (cpf,))
        conexao.commit()
        messagebox.showinfo("Sucesso", f"Cliente '{nome}' excluído com sucesso.")
        carregar_tabela_clientes_cad()
    except Exception as e:
        messagebox.showerror("Erro", str(e))

def carregar_tabela_clientes_cad():
    for item in tabela_clientes_cad.get_children():
        tabela_clientes_cad.delete(item)
    cursor.execute("SELECT nome, cpf, placa, tipo FROM clientes ORDER BY nome")
    for row in cursor.fetchall():
        nome, cpf, placa, tipo = row
        cpf_fmt = f"{cpf[:3]}.{cpf[3:6]}.{cpf[6:9]}-{cpf[9:]}" if len(cpf) == 11 else cpf
        tabela_clientes_cad.insert("", "end", values=(nome, cpf_fmt, formatar_placa_exibicao(placa), tipo.capitalize()))

def limpar_movimentacao():
    entrada_placa_mov.delete(0, tk.END)
    entrada_hora_in.delete(0, tk.END)
    entrada_hora_out.delete(0, tk.END)
    entrada_data.delete(0, tk.END)
    entrada_data.insert(0, date.today().strftime("%d-%m-%Y"))

def limpar_tabela():
    selecionado = tabela_mov.selection()
    if not selecionado:
        messagebox.showwarning("Atenção", "Selecione um registro para excluir.")
        return
    item   = tabela_mov.item(selecionado[0])
    id_mov = item["values"][0]
    if not messagebox.askyesno("Confirmar", "Deseja realmente excluir este registro?"):
        return
    try:
        cursor.execute("DELETE FROM movimentacoes WHERE id = ?", (id_mov,))
        conexao.commit()
        messagebox.showinfo("Sucesso", "Registro excluído com sucesso!")
        carregar_movimentacoes()
    except Exception as e:
        messagebox.showerror("Erro", str(e))
    entrada_data.delete(0, tk.END)
    entrada_data.insert(0, date.today().strftime("%d-%m-%Y"))

def carregar_movimentacoes():
    for item in tabela_mov.get_children():
        tabela_mov.delete(item)
    cursor.execute("SELECT id, placa, data, entrada, saida, valor, pago FROM movimentacoes ORDER BY id DESC")
    for row in cursor.fetchall():
        id_, placa, data, entrada, saida, valor, pago = row
        placa = formatar_placa_exibicao(placa)
        tabela_mov.insert("", "end",
            values=(
                id_, placa, data, entrada,
                saida if saida else "—",
                f"R$ {valor:.2f}" if valor else "—",
                "✓" if pago else "✗"
            ),
            tags=("pago" if pago else "nao_pago",)
        )

def registrar_entrada():
    placa   = limpar_placa(entrada_placa_mov.get())
    data    = entrada_data.get().strip()
    hora_in = entrada_hora_in.get().strip()

    if not placa:
        messagebox.showwarning("Atenção", "Preencha a Placa.")
        return
    if not validar_placa(placa):
        messagebox.showerror("Erro", "Placa inválida. Use o formato ABC-1234 ou ABC1D23.")
        return
    if not hora_in:
        messagebox.showwarning("Atenção", "Preencha o Horário de entrada.")
        return

    cursor.execute("SELECT nome, tipo FROM clientes WHERE UPPER(placa) = UPPER(?)", (placa,))
    cliente = cursor.fetchone()
    if not cliente:
        messagebox.showerror("Erro", f"A placa {formatar_placa_exibicao(placa)} não está vinculada a nenhum cliente cadastrado.")
        return

    nome_cliente, tipo_cliente = cliente
    if tipo_cliente != "rotativo":
        messagebox.showerror("Erro", f"O cliente '{nome_cliente}' é do tipo '{tipo_cliente.capitalize()}'. Use a aba de Contratos para registrar movimentação.")
        return

    cursor.execute("SELECT vaga FROM movimentacoes WHERE saida IS NULL AND vaga IS NOT NULL")
    vagas_ocupadas = {row[0] for row in cursor.fetchall()}
    vagas_livres = [v for v in range(1, TOTAL_VAGAS + 1) if v not in vagas_ocupadas]

    if not vagas_livres:
        messagebox.showerror("Erro", "Não há vagas disponíveis no momento.")
        return

    vaga_escolhida = random.choice(vagas_livres)

    try:
        cursor.execute(
            "INSERT INTO movimentacoes (placa, data, entrada, vaga) VALUES (?, ?, ?, ?)",
            (placa, data, hora_in, vaga_escolhida)
        )
        conexao.commit()
        messagebox.showinfo("Sucesso", f"Entrada registrada para {formatar_placa_exibicao(placa)} ({nome_cliente}) às {hora_in}.\nVaga alocada: {vaga_escolhida}")
        limpar_movimentacao()
        carregar_movimentacoes()
        atualizar_mapa_vagas()
    except Exception as e:
        messagebox.showerror("Erro", str(e))

def registrar_saida():
    placa    = limpar_placa(entrada_placa_mov.get())
    hora_out = entrada_hora_out.get().strip()

    if not placa or not hora_out:
        messagebox.showwarning("Atenção", "Preencha a Placa e a Hora de Saída.")
        return

    cursor.execute(
        "SELECT id, entrada FROM movimentacoes WHERE placa=? AND saida IS NULL ORDER BY id DESC LIMIT 1",
        (placa,)
    )
    row = cursor.fetchone()
    if not row:
        messagebox.showerror("Erro", f"Nenhuma entrada em aberto encontrada para {placa}.")
        return

    mov_id, hora_in = row
    valor = calcular_valor_rotativo(hora_in, hora_out)

    try:
        cursor.execute(
            "UPDATE movimentacoes SET saida=?, valor=?, pago=1 WHERE id=?",
            (hora_out, valor, mov_id)
        )
        conexao.commit()
        messagebox.showinfo("Sucesso", f"Saída registrada para {placa}. Valor: R$ {valor:.2f}")
        limpar_movimentacao()
        carregar_movimentacoes()
        atualizar_mapa_vagas()
    except Exception as e:
        messagebox.showerror("Erro", str(e))

# ===========================================================
# --- FUNÇÕES DA SUB-ABA CLIENTES REGISTRADOS ---
# ===========================================================

def carregar_cards_clientes():
    for widget in frame_cards_inner.winfo_children():
        widget.destroy()

    cursor.execute("SELECT id, nome, cpf, placa, tipo FROM clientes ORDER BY nome")
    clientes = cursor.fetchall()

    if not clientes:
        tk.Label(frame_cards_inner, text="Nenhum cliente cadastrado.",
                 font=FONT, bg=BG, fg=CINZA).pack(pady=40)
        return

    for idx, (cid, nome, cpf, placa, tipo) in enumerate(clientes):
        cpf_fmt   = f"{cpf[:3]}.{cpf[3:6]}.{cpf[6:9]}-{cpf[9:]}" if len(cpf) == 11 else cpf
        placa_fmt = formatar_placa_exibicao(placa)
        _criar_card(frame_cards_inner, cid, nome, cpf_fmt, placa_fmt, tipo)

    frame_cards_inner.update_idletasks()
    canvas_cards.configure(scrollregion=canvas_cards.bbox("all"))

TIPO_CORES = {"rotativo": AZUL, "diarista": AZUL2, "mensalista": VERM}
TIPO_LABELS = {"rotativo": "Rotativo", "diarista": "Diarista", "mensalista": "Mensalista"}

def _criar_card(parent, cid, nome, cpf_fmt, placa_fmt, tipo="rotativo"):
    cor_tipo = TIPO_CORES.get(tipo, AZUL)
    card = tk.Frame(parent, bg=BG2, bd=0, relief="flat",
                    highlightbackground=cor_tipo, highlightthickness=1)
    card.pack(fill="x", padx=20, pady=6)

    frame_icon = tk.Frame(card, bg=cor_tipo, width=54)
    frame_icon.pack(side="left", fill="y")
    frame_icon.pack_propagate(False)
    inicial = nome[0].upper() if nome else "?"
    tk.Label(frame_icon, text=inicial, font=("Arial", 18, "bold"),
             bg=cor_tipo, fg=BRAN).place(relx=0.5, rely=0.5, anchor="center")

    frame_dados = tk.Frame(card, bg=BG2)
    frame_dados.pack(side="left", fill="both", expand=True, padx=14, pady=10)

    tk.Label(frame_dados, text=nome, font=FONTB, bg=BG2, fg=BRAN, anchor="w").grid(row=0, column=0, columnspan=6, sticky="w")

    tk.Label(frame_dados, text="CPF:", font=FONT, bg=BG2, fg=CINZA).grid(row=1, column=0, sticky="w", pady=(4,0))
    tk.Label(frame_dados, text=cpf_fmt, font=FONT, bg=BG2, fg=BRAN).grid(row=1, column=1, sticky="w", padx=(4,20), pady=(4,0))
    tk.Label(frame_dados, text="Placa:", font=FONT, bg=BG2, fg=CINZA).grid(row=1, column=2, sticky="w", pady=(4,0))
    tk.Label(frame_dados, text=placa_fmt, font=FONT, bg=BG2, fg=BRAN).grid(row=1, column=3, sticky="w", padx=(4,20), pady=(4,0))
    tk.Label(frame_dados, text="Tipo:", font=FONT, bg=BG2, fg=CINZA).grid(row=1, column=4, sticky="w", pady=(4,0))
    tk.Label(frame_dados, text=TIPO_LABELS.get(tipo, tipo), font=FONTB, bg=BG2, fg=cor_tipo).grid(row=1, column=5, sticky="w", padx=(4,0), pady=(4,0))

    frame_btns = tk.Frame(card, bg=BG2)
    frame_btns.pack(side="right", padx=12, pady=10)

    tk.Button(frame_btns, text="✏  Editar",
              bg=AZUL, fg=BRAN, font=FONTB, relief="flat", cursor="hand2",
              activebackground=AZUL2, activeforeground=BRAN, padx=10, pady=4,
              command=lambda i=cid, n=nome, c=cpf_fmt, p=placa_fmt, t=tipo: abrir_modal_edicao(i, n, c, p, t)
              ).pack(side="left", padx=(0, 6))
    tk.Button(frame_btns, text="🗑  Excluir",
              bg=VERM, fg=BRAN, font=FONTB, relief="flat", cursor="hand2",
              activebackground="#E53935", activeforeground=BRAN, padx=10, pady=4,
              command=lambda i=cid, n=nome: excluir_cliente_card(i, n)
              ).pack(side="left")

def excluir_cliente_card(cid, nome):
    if not messagebox.askyesno("Confirmar exclusão",
                               f"Deseja excluir o cliente '{nome}'?\nAs movimentações vinculadas serão mantidas."):
        return
    try:
        cursor.execute("DELETE FROM clientes WHERE id = ?", (cid,))
        conexao.commit()
        messagebox.showinfo("Sucesso", f"Cliente '{nome}' excluído com sucesso.")
        carregar_cards_clientes()
        carregar_tabela_clientes_cad()
    except Exception as e:
        messagebox.showerror("Erro", str(e))

def abrir_modal_edicao(cid, nome, cpf_fmt, placa_fmt, tipo="rotativo"):
    modal = tk.Toplevel(janela)
    modal.title("Editar Cliente")
    modal.configure(bg=BG)
    modal.resizable(False, False)
    modal.grab_set()

    w, h = 440, 320
    modal.geometry(f"{w}x{h}+{janela.winfo_x() + janela.winfo_width()//2 - w//2}"
                   f"+{janela.winfo_y() + janela.winfo_height()//2 - h//2}")

    tk.Label(modal, text="EDITAR CLIENTE", font=FONTH, bg=BG, fg=AZUL).pack(pady=(20, 14))

    frame_form = tk.Frame(modal, bg=BG)
    frame_form.pack(padx=30, fill="x")

    campos = [("Nome", nome), ("CPF", cpf_fmt), ("Placa", placa_fmt)]
    entries = {}

    for i, (label, valor) in enumerate(campos):
        tk.Label(frame_form, text=label + ":", font=FONTB, bg=BG, fg=BRAN).grid(
            row=i, column=0, sticky="e", padx=(0, 10), pady=6)
        e = tk.Entry(frame_form, bg=BG2, fg=BRAN, insertbackground=BRAN,
                     borderwidth=0, font=FONT, width=28)
        e.insert(0, valor)
        e.grid(row=i, column=1, sticky="ew", pady=6, ipady=4)
        if label == "Placa":
            e.bind("<KeyRelease>", mascara_placa)
        entries[label] = e

    tk.Label(frame_form, text="Tipo:", font=FONTB, bg=BG, fg=BRAN).grid(
        row=3, column=0, sticky="e", padx=(0, 10), pady=6)
    var_tipo_edit = tk.StringVar(value=tipo)
    frame_tipo_edit = tk.Frame(frame_form, bg=BG)
    frame_tipo_edit.grid(row=3, column=1, sticky="w", pady=6)
    for t, lbl in [("rotativo", "Rotativo"), ("diarista", "Diarista"), ("mensalista", "Mensalista")]:
        tk.Radiobutton(frame_tipo_edit, text=lbl, variable=var_tipo_edit, value=t,
                       bg=BG, fg=BRAN, selectcolor=BG2, activebackground=BG,
                       activeforeground=BRAN, font=FONT).pack(side="left", padx=6)

    frame_form.columnconfigure(1, weight=1)

    def salvar_edicao():
        novo_nome  = entries["Nome"].get().strip()
        novo_cpf   = re.sub(r'\D', '', entries["CPF"].get())
        nova_placa = limpar_placa(entries["Placa"].get())
        novo_tipo  = var_tipo_edit.get()

        if not novo_nome:
            messagebox.showerror("Erro", "Nome não pode ser vazio.", parent=modal)
            return
        if not validar_cpf(novo_cpf):
            messagebox.showerror("Erro", "CPF inválido.", parent=modal)
            return
        if not validar_placa(nova_placa):
            messagebox.showerror("Erro", "Placa inválida.", parent=modal)
            return

        cursor.execute("SELECT id FROM clientes WHERE cpf = ? AND id != ?", (novo_cpf, cid))
        if cursor.fetchone():
            messagebox.showerror("Erro", "Este CPF já está cadastrado em outro cliente.", parent=modal)
            return

        try:
            cursor.execute(
                "UPDATE clientes SET nome=?, cpf=?, placa=?, tipo=? WHERE id=?",
                (novo_nome, novo_cpf, nova_placa, novo_tipo, cid)
            )
            conexao.commit()
            messagebox.showinfo("Sucesso", "Cliente atualizado com sucesso!", parent=modal)
            modal.destroy()
            carregar_cards_clientes()
            carregar_tabela_clientes_cad()
        except Exception as e:
            messagebox.showerror("Erro", str(e), parent=modal)

    frame_btns = tk.Frame(modal, bg=BG)
    frame_btns.pack(pady=18)
    tk.Button(frame_btns, text="Salvar", command=salvar_edicao,
              bg=AZUL, fg=BRAN, font=FONTB, relief="flat", width=14, cursor="hand2",
              activebackground=AZUL2, activeforeground=BRAN).pack(side="left", padx=8)
    tk.Button(frame_btns, text="Cancelar", command=modal.destroy,
              bg=CINZA, fg=BG, font=FONTB, relief="flat", width=14, cursor="hand2").pack(side="left", padx=8)

# ===========================================================
# --- FUNÇÕES DE RELATÓRIO ---
# ===========================================================

def gerar_relatorio_clientes():
    for item in tabela_rel_clientes.get_children():
        tabela_rel_clientes.delete(item)
    cursor.execute("SELECT nome, cpf, placa, tipo FROM clientes ORDER BY nome")
    for cliente in cursor.fetchall():
        nome, cpf, placa, tipo = cliente
        cpf_fmt = f"{cpf[:3]}.{cpf[3:6]}.{cpf[6:9]}-{cpf[9:]}" if len(cpf) == 11 else cpf
        tabela_rel_clientes.insert("", "end", values=(nome, cpf_fmt, formatar_placa_exibicao(placa), tipo.capitalize()))

def gerar_relatorio_recebimentos():
    for item in tabela_rel_recebimentos.get_children():
        tabela_rel_recebimentos.delete(item)
    cursor.execute("""
        SELECT m.id, COALESCE(c.nome, '—'), m.placa, m.data, m.entrada, m.saida, m.valor
        FROM movimentacoes m
        LEFT JOIN clientes c ON UPPER(m.placa) = UPPER(c.placa)
        WHERE m.pago = 1
        ORDER BY m.data DESC
    """)
    for rec in cursor.fetchall():
        id_, nome, placa, data, entrada, saida, valor = rec
        tabela_rel_recebimentos.insert("", "end", values=(
            id_, nome, formatar_placa_exibicao(placa), data,
            entrada if entrada else "—",
            saida   if saida   else "—",
            f"R$ {valor:.2f}" if valor else "—"
        ))

def gerar_relatorio_recebimentos_abertos():
    for item in tabela_rel_recebimentos_abertos.get_children():
        tabela_rel_recebimentos_abertos.delete(item)
    cursor.execute("""
        SELECT m.id, COALESCE(c.nome, 'Cliente não cadastrado'), m.placa, m.data, m.entrada
        FROM movimentacoes m
        LEFT JOIN clientes c ON UPPER(m.placa) = UPPER(c.placa)
        WHERE m.pago = 0
        ORDER BY m.data DESC
    """)
    for rec in cursor.fetchall():
        id_, nome, placa, data, entrada = rec
        tabela_rel_recebimentos_abertos.insert("", "end", values=(
            id_, nome, formatar_placa_exibicao(placa), data,
            entrada if entrada else "—"
        ))

def gerar_relatorio_top_clientes():
    for item in tabela_rel_top_clientes.get_children():
        tabela_rel_top_clientes.delete(item)
    cursor.execute("""
        SELECT c.nome, c.cpf, c.placa, COUNT(m.id) AS total_visitas
        FROM clientes c
        LEFT JOIN movimentacoes m ON UPPER(c.placa) = UPPER(m.placa)
        GROUP BY c.id
        ORDER BY total_visitas DESC
        LIMIT 5
    """)
    for cliente in cursor.fetchall():
        tabela_rel_top_clientes.insert("", "end", values=cliente)

def pesquisar_clientes_cadastrados(termo):
    for widget in frame_cards_inner.winfo_children():
        widget.destroy()
    cursor.execute("SELECT id, nome, cpf, placa, tipo FROM clientes ORDER BY nome")
    clientes = cursor.fetchall()
    termo = termo.lower().strip()
    encontrados = []
    for cid, nome, cpf, placa, tipo in clientes:
        cpf_fmt   = f"{cpf[:3]}.{cpf[3:6]}.{cpf[6:9]}-{cpf[9:]}" if len(cpf) == 11 else cpf
        placa_fmt = formatar_placa_exibicao(placa)
        if termo in nome.lower() or termo in cpf_fmt or termo in placa_fmt.lower() or termo in tipo.lower():
            encontrados.append((cid, nome, cpf_fmt, placa_fmt, tipo))
    if not encontrados:
        tk.Label(frame_cards_inner, text="Nenhum cliente encontrado.",
                 font=FONT, bg=BG, fg=CINZA).pack(pady=40)
    else:
        for cid, nome, cpf_fmt, placa_fmt, tipo in encontrados:
            _criar_card(frame_cards_inner, cid, nome, cpf_fmt, placa_fmt, tipo)
    frame_cards_inner.update_idletasks()
    canvas_cards.configure(scrollregion=canvas_cards.bbox("all"))

def pesquisar_rel_clientes(termo):
    for item in tabela_rel_clientes.get_children():
        tabela_rel_clientes.delete(item)
    cursor.execute("SELECT nome, cpf, placa, tipo FROM clientes ORDER BY nome")
    termo = termo.lower().strip()
    for nome, cpf, placa, tipo in cursor.fetchall():
        cpf_fmt = f"{cpf[:3]}.{cpf[3:6]}.{cpf[6:9]}-{cpf[9:]}" if len(cpf) == 11 else cpf
        if termo in nome.lower() or termo in cpf_fmt or termo in formatar_placa_exibicao(placa).lower() or termo in tipo.lower():
            tabela_rel_clientes.insert("", "end", values=(nome, cpf_fmt, formatar_placa_exibicao(placa), tipo.capitalize()))

def pesquisar_rel_recebimentos(termo):
    for item in tabela_rel_recebimentos.get_children():
        tabela_rel_recebimentos.delete(item)
    cursor.execute("""
        SELECT m.id, COALESCE(c.nome, '—'), m.placa, m.data, m.entrada, m.saida, m.valor
        FROM movimentacoes m LEFT JOIN clientes c ON UPPER(m.placa) = UPPER(c.placa)
        WHERE m.pago = 1 ORDER BY m.data DESC
    """)
    termo = termo.lower().strip()
    for id_, nome, placa, data, entrada, saida, valor in cursor.fetchall():
        if (termo in str(id_) or termo in nome.lower() or termo in placa.lower()
                or termo in data or termo in (entrada or "") or termo in (saida or "")):
            tabela_rel_recebimentos.insert("", "end", values=(
                id_, nome, formatar_placa_exibicao(placa), data,
                entrada or "—", saida or "—",
                f"R$ {valor:.2f}" if valor else "—"
            ))

def pesquisar_rel_abertos(termo):
    for item in tabela_rel_recebimentos_abertos.get_children():
        tabela_rel_recebimentos_abertos.delete(item)
    cursor.execute("""
        SELECT m.id, COALESCE(c.nome, 'Cliente não cadastrado'), m.placa, m.data, m.entrada
        FROM movimentacoes m LEFT JOIN clientes c ON UPPER(m.placa) = UPPER(c.placa)
        WHERE m.pago = 0 ORDER BY m.data DESC
    """)
    termo = termo.lower().strip()
    for id_, nome, placa, data, entrada in cursor.fetchall():
        if termo in str(id_) or termo in nome.lower() or termo in placa.lower() or termo in data:
            tabela_rel_recebimentos_abertos.insert("", "end", values=(
                id_, nome, formatar_placa_exibicao(placa), data, entrada or "—"
            ))

def pesquisar_rel_top(termo):
    for item in tabela_rel_top_clientes.get_children():
        tabela_rel_top_clientes.delete(item)
    cursor.execute("""
        SELECT c.nome, c.cpf, c.placa, COUNT(m.id) AS total_visitas
        FROM clientes c LEFT JOIN movimentacoes m ON UPPER(c.placa) = UPPER(m.placa)
        GROUP BY c.id ORDER BY total_visitas DESC LIMIT 5
    """)
    termo = termo.lower().strip()
    for nome, cpf, placa, visitas in cursor.fetchall():
        if termo in nome.lower() or termo in cpf or termo in placa.lower():
            tabela_rel_top_clientes.insert("", "end", values=(nome, cpf, formatar_placa_exibicao(placa), visitas))

def atualizar_mapa_vagas():
    cursor.execute("SELECT vaga FROM movimentacoes WHERE saida IS NULL AND vaga IS NOT NULL")
    vagas_ocupadas = {row[0] for row in cursor.fetchall()}
    for num_vaga, cell in _vaga_canvas.items():
        cor = VERM if num_vaga in vagas_ocupadas else AZUL
        cell.configure(bg=cor)

def ao_trocar_aba(event):
    aba_selecionada = abas.tab(abas.select(), "text").strip()
    if aba_selecionada == "Clientes":
        carregar_cards_clientes()
    elif aba_selecionada == "Relatórios":
        gerar_relatorio_clientes()
        gerar_relatorio_recebimentos()
        gerar_relatorio_recebimentos_abertos()
        gerar_relatorio_top_clientes()
    elif aba_selecionada == "Mapa de vagas":
        atualizar_mapa_vagas()
    elif aba_selecionada == "Financeiro":
        atualizar_dashboard_financeiro()

# ===========================================================
# --- FUNÇÕES DE PESQUISA  ---
# ===========================================================

def criar_barra_pesquisa(parent, comando_pesquisa):
    frame_search = tk.Frame(parent, bg=BG)
    frame_search.pack(fill="x", padx=20, pady=(12, 4))
    canvas_search = tk.Canvas(frame_search, bg=BG3, height=34,
                               highlightthickness=1, highlightbackground=AZUL2, bd=0)
    canvas_search.pack(fill="x")
    frame_inner = tk.Frame(canvas_search, bg=BG3)
    canvas_search.create_window(0, 0, anchor="nw", window=frame_inner,
                                 width=canvas_search.winfo_reqwidth())
    def _resize(event):
        canvas_search.itemconfig(1, width=event.width)
    canvas_search.bind("<Configure>", _resize)
    tk.Label(frame_inner, text="🔍", bg=BG3, fg=CINZA, font=FONT).pack(side="left", padx=(10, 4))
    var = tk.StringVar()
    entry = tk.Entry(frame_inner, textvariable=var, bg=BG3, fg=BRAN,
                     insertbackground=BRAN, borderwidth=0, font=FONT, relief="flat")
    entry.pack(side="left", fill="x", expand=True, pady=6, padx=(0, 10))
    var.trace_add("write", lambda *_: comando_pesquisa(var.get()))
    return var

# ===========================================================
# --- FUNÇÕES DE EXPORTAÇÃO PDF ---
# ===========================================================

def _estilos_pdf():
    styles = getSampleStyleSheet()
    titulo_style = ParagraphStyle(
        'TituloEstaciON', parent=styles['Title'], fontSize=16,
        textColor=colors.HexColor("#1565C0"), spaceAfter=4, alignment=TA_CENTER,
    )
    sub_style = ParagraphStyle(
        'SubTituloEstaciON', parent=styles['Normal'], fontSize=9,
        textColor=colors.grey, spaceAfter=14, alignment=TA_CENTER,
    )
    return titulo_style, sub_style

def _estilo_tabela_pdf(num_cols):
    azul        = colors.HexColor("#1565C0")
    cinza_linha = colors.HexColor("#F5F5F5")
    return TableStyle([
        ('BACKGROUND',    (0, 0), (-1, 0), azul),
        ('TEXTCOLOR',     (0, 0), (-1, 0), colors.white),
        ('FONTNAME',      (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE',      (0, 0), (-1, 0), 10),
        ('ALIGN',         (0, 0), (-1, 0), 'CENTER'),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 8),
        ('TOPPADDING',    (0, 0), (-1, 0), 8),
        ('ROWBACKGROUNDS',(0, 1), (-1, -1), [colors.white, cinza_linha]),
        ('FONTNAME',      (0, 1), (-1, -1), 'Helvetica'),
        ('FONTSIZE',      (0, 1), (-1, -1), 9),
        ('ALIGN',         (0, 1), (-1, -1), 'CENTER'),
        ('TOPPADDING',    (0, 1), (-1, -1), 6),
        ('BOTTOMPADDING', (0, 1), (-1, -1), 6),
        ('GRID',          (0, 0), (-1, -1), 0.5, colors.HexColor("#BDBDBD")),
        ('LINEBELOW',     (0, 0), (-1, 0), 1.5, azul),
    ])

def _salvar_pdf(doc, story, titulo_relatorio):
    try:
        doc.build(story)
        messagebox.showinfo("PDF Gerado", f"Relatório '{titulo_relatorio}' exportado com sucesso!\nArquivo: {doc.filename}")
    except Exception as e:
        messagebox.showerror("Erro ao gerar PDF", str(e))

def _pedir_caminho(nome_sugerido):
    return filedialog.asksaveasfilename(
        defaultextension=".pdf",
        filetypes=[("PDF", "*.pdf")],
        initialfile=nome_sugerido,
        title="Salvar relatório como..."
    )

def exportar_pdf_clientes():
    caminho = _pedir_caminho(f"relatorio_clientes_{date.today()}.pdf")
    if not caminho:
        return
    titulo_style, sub_style = _estilos_pdf()
    doc = SimpleDocTemplate(caminho, pagesize=A4, leftMargin=2*cm, rightMargin=2*cm, topMargin=2*cm, bottomMargin=2*cm)
    story = []
    story.append(Paragraph("estaciON", titulo_style))
    story.append(Paragraph(f"Relatório de Clientes  •  Gerado em {datetime.now().strftime('%d/%m/%Y %H:%M')}", sub_style))
    cursor.execute("SELECT nome, cpf, placa, tipo FROM clientes ORDER BY nome")
    rows = cursor.fetchall()
    if not rows:
        story.append(Paragraph("Nenhum cliente cadastrado.", getSampleStyleSheet()['Normal']))
    else:
        dados = [["Nome", "CPF", "Placa", "Tipo"]]
        for nome, cpf, placa, tipo in rows:
            cpf_fmt = f"{cpf[:3]}.{cpf[3:6]}.{cpf[6:9]}-{cpf[9:]}" if len(cpf) == 11 else cpf
            dados.append([nome, cpf_fmt, formatar_placa_exibicao(placa), tipo.capitalize()])
        tabela = Table(dados, colWidths=[7*cm, 4.5*cm, 3.5*cm, 2.5*cm], repeatRows=1)
        tabela.setStyle(_estilo_tabela_pdf(4))
        story.append(tabela)
        story.append(Spacer(1, 0.5*cm))
        story.append(Paragraph(f"Total de clientes: {len(rows)}", ParagraphStyle('rodape', fontSize=9, textColor=colors.grey, alignment=TA_CENTER)))
    _salvar_pdf(doc, story, "Relatório Clientes")

def exportar_pdf_recebimentos():
    caminho = _pedir_caminho(f"relatorio_recebimentos_{date.today()}.pdf")
    if not caminho:
        return
    titulo_style, sub_style = _estilos_pdf()
    doc = SimpleDocTemplate(caminho, pagesize=landscape(A4), leftMargin=2*cm, rightMargin=2*cm, topMargin=2*cm, bottomMargin=2*cm)
    story = []
    story.append(Paragraph("estaciON", titulo_style))
    story.append(Paragraph(f"Relatório de Recebimentos  •  Gerado em {datetime.now().strftime('%d/%m/%Y %H:%M')}", sub_style))
    cursor.execute("""
        SELECT m.id, COALESCE(c.nome, '—'), m.placa, m.data, m.entrada, m.saida, m.valor
        FROM movimentacoes m LEFT JOIN clientes c ON UPPER(m.placa) = UPPER(c.placa)
        WHERE m.pago = 1 ORDER BY m.data DESC
    """)
    rows = cursor.fetchall()
    if not rows:
        story.append(Paragraph("Nenhum recebimento encontrado.", getSampleStyleSheet()['Normal']))
    else:
        dados = [["ID", "Cliente", "Placa", "Data", "Entrada", "Saída", "Valor"]]
        total = 0.0
        for id_, nome, placa, data, entrada, saida, valor in rows:
            total += valor or 0
            dados.append([str(id_), nome, formatar_placa_exibicao(placa), data, entrada or "—", saida or "—", f"R$ {valor:.2f}" if valor else "—"])
        dados.append(["", "", "", "", "", "TOTAL:", f"R$ {total:.2f}"])
        tabela = Table(dados, colWidths=[1.2*cm, 6*cm, 3*cm, 3*cm, 2.5*cm, 2.5*cm, 3*cm], repeatRows=1)
        ts = _estilo_tabela_pdf(7)
        ts.add('BACKGROUND', (0, len(dados)-1), (-1, len(dados)-1), colors.HexColor("#E3F2FD"))
        ts.add('FONTNAME',   (0, len(dados)-1), (-1, len(dados)-1), 'Helvetica-Bold')
        ts.add('LINEABOVE',  (0, len(dados)-1), (-1, len(dados)-1), 1, colors.HexColor("#1565C0"))
        tabela.setStyle(ts)
        story.append(tabela)
    _salvar_pdf(doc, story, "Relatório Recebimentos")

def exportar_pdf_abertos():
    caminho = _pedir_caminho(f"relatorio_abertos_{date.today()}.pdf")
    if not caminho:
        return
    titulo_style, sub_style = _estilos_pdf()
    doc = SimpleDocTemplate(caminho, pagesize=A4, leftMargin=2*cm, rightMargin=2*cm, topMargin=2*cm, bottomMargin=2*cm)
    story = []
    story.append(Paragraph("estaciON", titulo_style))
    story.append(Paragraph(f"Recebimentos em Aberto  •  Gerado em {datetime.now().strftime('%d/%m/%Y %H:%M')}", sub_style))
    cursor.execute("""
        SELECT m.id, COALESCE(c.nome, 'Cliente não cadastrado'), m.placa, m.data, m.entrada
        FROM movimentacoes m LEFT JOIN clientes c ON UPPER(m.placa) = UPPER(c.placa)
        WHERE m.pago = 0 ORDER BY m.data DESC
    """)
    rows = cursor.fetchall()
    if not rows:
        story.append(Paragraph("Nenhum recebimento em aberto.", getSampleStyleSheet()['Normal']))
    else:
        dados = [["ID", "Cliente", "Placa", "Data", "Entrada"]]
        for id_, nome, placa, data, entrada in rows:
            dados.append([str(id_), nome, formatar_placa_exibicao(placa), data, entrada or "—"])
        tabela = Table(dados, colWidths=[1.5*cm, 7*cm, 3.5*cm, 3.5*cm, 3*cm], repeatRows=1)
        ts = _estilo_tabela_pdf(5)
        for i in range(1, len(dados)):
            ts.add('TEXTCOLOR', (0, i), (-1, i), colors.HexColor("#B71C1C"))
        tabela.setStyle(ts)
        story.append(tabela)
        story.append(Spacer(1, 0.5*cm))
        story.append(Paragraph(f"Total em aberto: {len(rows)} registro(s)", ParagraphStyle('rodape', fontSize=9, textColor=colors.HexColor("#C62828"), alignment=TA_CENTER)))
    _salvar_pdf(doc, story, "Recebimentos em Aberto")

def exportar_pdf_top_clientes():
    caminho = _pedir_caminho(f"relatorio_top_clientes_{date.today()}.pdf")
    if not caminho:
        return
    titulo_style, sub_style = _estilos_pdf()
    doc = SimpleDocTemplate(caminho, pagesize=A4, leftMargin=2*cm, rightMargin=2*cm, topMargin=2*cm, bottomMargin=2*cm)
    story = []
    story.append(Paragraph("estaciON", titulo_style))
    story.append(Paragraph(f"Top 5 Clientes  •  Gerado em {datetime.now().strftime('%d/%m/%Y %H:%M')}", sub_style))
    cursor.execute("""
        SELECT c.nome, c.cpf, c.placa, COUNT(m.id) AS total_visitas
        FROM clientes c LEFT JOIN movimentacoes m ON UPPER(c.placa) = UPPER(m.placa)
        GROUP BY c.id ORDER BY total_visitas DESC LIMIT 5
    """)
    rows = cursor.fetchall()
    if not rows:
        story.append(Paragraph("Nenhum dado disponível.", getSampleStyleSheet()['Normal']))
    else:
        medalhas = ["1o", "2o", "3o", "4o", "5o"]
        dados = [["#", "Nome", "CPF", "Placa", "Visitas"]]
        for i, (nome, cpf, placa, visitas) in enumerate(rows):
            cpf_fmt = f"{cpf[:3]}.{cpf[3:6]}.{cpf[6:9]}-{cpf[9:]}" if len(cpf) == 11 else cpf
            dados.append([medalhas[i], nome, cpf_fmt, formatar_placa_exibicao(placa), str(visitas)])
        tabela = Table(dados, colWidths=[1.5*cm, 6.5*cm, 4*cm, 3*cm, 2.5*cm], repeatRows=1)
        ts = _estilo_tabela_pdf(5)
        if len(dados) > 1:
            ts.add('BACKGROUND', (0, 1), (-1, 1), colors.HexColor("#1A3A6B"))
            ts.add('FONTNAME',   (0, 1), (-1, 1), 'Helvetica-Bold')
        tabela.setStyle(ts)
        story.append(tabela)
    _salvar_pdf(doc, story, "Top 5 Clientes")

# ===========================================================
# --- ABA DE CLIENTES ---
# ===========================================================
aba_clientes_principal = tk.Frame(abas, bg=BG)
abas.add(aba_clientes_principal, text="Clientes ")

sub_notebook_clientes = ttk.Notebook(aba_clientes_principal, style="Sub.TNotebook")
sub_notebook_clientes.pack(expand=True, fill="both", padx=0, pady=10)

# --- Sub-aba Cadastro ---
aba_cadastroCliente = tk.Frame(sub_notebook_clientes, bg=BG)
sub_notebook_clientes.add(aba_cadastroCliente, text="Cadastro")

tk.Label(aba_cadastroCliente, text="CADASTRO DE CLIENTES", font=FONTH, bg=BG, fg=AZUL).grid(row=0, column=0, columnspan=6, pady=20)

for i, texto in enumerate(["Nome:", "CPF:", "Placa:"]):
    tk.Label(aba_cadastroCliente, text=texto, font=FONTB, bg=BG, fg=BRAN).grid(row=1, column=i*2, padx=10, sticky="e")

entrada_nomeCliente = tk.Entry(aba_cadastroCliente, bg=BG2, fg=BRAN, insertbackground=BRAN, borderwidth=0, font=FONT)
entrada_nomeCliente.grid(row=1, column=1, padx=5, pady=10, sticky="ew")

entrada_cpf = tk.Entry(aba_cadastroCliente, bg=BG2, fg=BRAN, insertbackground=BRAN, borderwidth=0, font=FONT)
entrada_cpf.grid(row=1, column=3, padx=5, pady=10, sticky="ew")

entrada_placaVeiculo = tk.Entry(aba_cadastroCliente, bg=BG2, fg=BRAN, insertbackground=BRAN, borderwidth=0, font=FONT)
entrada_placaVeiculo.bind("<KeyRelease>", mascara_placa)
entrada_placaVeiculo.grid(row=1, column=5, padx=5, pady=10, sticky="ew")

# Tipo de cliente
tk.Label(aba_cadastroCliente, text="Tipo:", font=FONTB, bg=BG, fg=BRAN).grid(row=2, column=0, padx=10, sticky="e")
var_tipo_cliente = tk.StringVar(value="rotativo")
frame_tipo_radio = tk.Frame(aba_cadastroCliente, bg=BG)
frame_tipo_radio.grid(row=2, column=1, columnspan=5, sticky="w", pady=4)
for t, lbl in [("rotativo", "Rotativo"), ("diarista", "Diarista"), ("mensalista", "Mensalista")]:
    tk.Radiobutton(frame_tipo_radio, text=lbl, variable=var_tipo_cliente, value=t,
                   bg=BG, fg=BRAN, selectcolor=BG2, activebackground=BG,
                   activeforeground=BRAN, font=FONTB).pack(side="left", padx=14)

frame_botoes_cad = tk.Frame(aba_cadastroCliente, bg=BG)
frame_botoes_cad.grid(row=3, column=0, columnspan=9, pady=(10, 6))

tk.Button(frame_botoes_cad, text="Registrar cliente", command=salvar, bg=AZUL, fg=BRAN, font=FONTB,
          relief="flat", width=18, cursor="hand2", activebackground=AZUL2, activeforeground=BRAN).pack(side="left", padx=10)

frame_tabela_cad = tk.Frame(aba_cadastroCliente, bg=BG)
frame_tabela_cad.grid(row=4, column=0, columnspan=9, sticky="nsew", padx=15, pady=(10, 15))
aba_cadastroCliente.rowconfigure(4, weight=1)

tabela_clientes_cad = ttk.Treeview(frame_tabela_cad,
    columns=("Nome", "CPF", "Placa", "Tipo"), show="headings", selectmode="browse")
for col, w in [("Nome", 220), ("CPF", 150), ("Placa", 110), ("Tipo", 100)]:
    tabela_clientes_cad.heading(col, text=col)
    tabela_clientes_cad.column(col, width=w, anchor="center", minwidth=60)

scrollbar_cad = ttk.Scrollbar(frame_tabela_cad, orient="vertical", command=tabela_clientes_cad.yview)
tabela_clientes_cad.configure(yscrollcommand=scrollbar_cad.set)
tabela_clientes_cad.pack(side="left", fill="both", expand=True)
scrollbar_cad.pack(side="right", fill="y")
aba_cadastroCliente.columnconfigure((1, 3, 5), weight=1)

# --- Sub-aba Clientes Cadastrados ---
aba_clientes_lista = tk.Frame(sub_notebook_clientes, bg=BG)
sub_notebook_clientes.add(aba_clientes_lista, text="Clientes Cadastrados")

criar_barra_pesquisa(aba_clientes_lista, pesquisar_clientes_cadastrados)

frame_scroll_lista = tk.Frame(aba_clientes_lista, bg=BG)
frame_scroll_lista.pack(fill="both", expand=True)

canvas_cards = tk.Canvas(frame_scroll_lista, bg=BG, highlightthickness=0, bd=0)
scrollbar_cards = ttk.Scrollbar(frame_scroll_lista, orient="vertical", command=canvas_cards.yview)
canvas_cards.configure(yscrollcommand=scrollbar_cards.set)

scrollbar_cards.pack(side="right", fill="y")
canvas_cards.pack(side="left", fill="both", expand=True)

frame_cards_inner = tk.Frame(canvas_cards, bg=BG)
canvas_cards.create_window((0, 0), window=frame_cards_inner, anchor="nw")

def _on_resize_cards(event):
    canvas_cards.itemconfig(1, width=event.width)
canvas_cards.bind("<Configure>", _on_resize_cards)

def _scroll_mouse(event):
    canvas_cards.yview_scroll(int(-1 * (event.delta / 120)), "units")
canvas_cards.bind_all("<MouseWheel>", _scroll_mouse)

# ===========================================================
# --- ABA MOVIMENTAÇÃO (ROTATIVO) ---
# ===========================================================
aba_movimentacao = tk.Frame(abas, bg=BG)
abas.add(aba_movimentacao, text="Movimentação ")

tk.Label(aba_movimentacao, text="MOVIMENTAÇÃO DE VAGAS — ROTATIVO", font=FONTH, bg=BG, fg=AZUL).grid(row=0, column=0, columnspan=9, pady=(20, 10))

tk.Label(aba_movimentacao, text="Placa", font=FONTB, bg=BG, fg=BRAN).grid(row=1, column=0, padx=(15,2), sticky="e")
entrada_placa_mov = tk.Entry(aba_movimentacao, bg=BG2, fg=BRAN, insertbackground=BRAN, borderwidth=0, font=FONT, width=12)
entrada_placa_mov.bind("<KeyRelease>", mascara_placa)
entrada_placa_mov.grid(row=1, column=1, padx=5, pady=6, sticky="ew")

tk.Label(aba_movimentacao, text="Data (DD-MM-AAAA)", font=FONTB, bg=BG, fg=BRAN).grid(row=1, column=2, padx=(10,2), sticky="e")
entrada_data = tk.Entry(aba_movimentacao, bg=BG2, fg=BRAN, insertbackground=BRAN, borderwidth=0, font=FONT, width=14)
entrada_data.insert(0, date.today().strftime("%d-%m-%Y"))
entrada_data.bind("<KeyRelease>", formatar_data)
entrada_data.grid(row=1, column=3, padx=5, pady=6, sticky="ew")

tk.Label(aba_movimentacao, text="Hora Entrada (HH:MM)", font=FONTB, bg=BG, fg=BRAN).grid(row=1, column=4, padx=(10,2), sticky="e")
entrada_hora_in = tk.Entry(aba_movimentacao, bg=BG2, fg=BRAN, insertbackground=BRAN, borderwidth=0, font=FONT, width=8)
entrada_hora_in.bind("<KeyRelease>", formatar_hora)
entrada_hora_in.grid(row=1, column=5, padx=5, pady=6, sticky="ew")

tk.Label(aba_movimentacao, text="Hora Saída (HH:MM)", font=FONTB, bg=BG, fg=BRAN).grid(row=1, column=6, padx=(10,2), sticky="e")
entrada_hora_out = tk.Entry(aba_movimentacao, bg=BG2, fg=BRAN, insertbackground=BRAN, borderwidth=0, font=FONT, width=8)
entrada_hora_out.bind("<KeyRelease>", formatar_hora)
entrada_hora_out.grid(row=1, column=7, padx=5, pady=6, sticky="ew")

aba_movimentacao.columnconfigure((1, 3, 5, 7), weight=1)

frame_tabela = tk.Frame(aba_movimentacao, bg=BG, bd=1, relief="flat")
frame_tabela.grid(row=3, column=0, columnspan=9, sticky="nsew", padx=15, pady=(10, 15))
aba_movimentacao.rowconfigure(3, weight=1)

colunas = ("ID", "Placa", "Data", "Entrada", "Saída", "Valor", "Pago")
tabela_mov = ttk.Treeview(frame_tabela, columns=colunas, show="headings", selectmode="browse")
larguras = {"ID": 50, "Placa": 100, "Data": 110, "Entrada": 80, "Saída": 80, "Valor": 90, "Pago": 60}
for col in colunas:
    tabela_mov.heading(col, text=col)
    tabela_mov.column(col, width=larguras[col], anchor="center", minwidth=40)

tabela_mov.tag_configure("pago",     foreground=BRAN)
tabela_mov.tag_configure("nao_pago", foreground=VERM)

scrollbar_y = ttk.Scrollbar(frame_tabela, orient="vertical", command=tabela_mov.yview)
tabela_mov.configure(yscrollcommand=scrollbar_y.set)
tabela_mov.pack(side="left", fill="both", expand=True)
scrollbar_y.pack(side="right", fill="y")

frame_botoes = tk.Frame(aba_movimentacao, bg=BG)
frame_botoes.grid(row=2, column=0, columnspan=9, pady=(8, 12))

tk.Button(frame_botoes, text="Registrar Entrada", bg=AZUL, fg=BRAN, font=FONTB,
          relief="flat", width=18, cursor="hand2", activebackground=AZUL2, activeforeground=BRAN,
          command=registrar_entrada).pack(side="left", padx=10)
tk.Button(frame_botoes, text="Registrar Saída", bg=VERM, fg=BRAN, font=FONTB,
          relief="flat", width=18, cursor="hand2", activebackground="#E53935", activeforeground=BRAN,
          command=registrar_saida).pack(side="left", padx=10)
tk.Button(frame_botoes, text="Limpar", bg=CINZA, fg=BG, font=FONTB,
          relief="flat", width=18, cursor="hand2",
          command=limpar_tabela).pack(side="left", padx=10)

# ===========================================================
# --- ABA CONTRATOS (DIARISTA / MENSALISTA) ---
# ===========================================================
aba_contratos = tk.Frame(abas, bg=BG)
abas.add(aba_contratos, text="Contratos ")

sub_nb_contratos = ttk.Notebook(aba_contratos, style="Sub.TNotebook")
sub_nb_contratos.pack(expand=True, fill="both", padx=0, pady=10)

# --- Sub-aba Diarista ---
aba_diarista = tk.Frame(sub_nb_contratos, bg=BG)
sub_nb_contratos.add(aba_diarista, text="Diarista")

tk.Label(aba_diarista, text="CONTRATO DIARISTA", font=FONTH, bg=BG, fg=AZUL).grid(row=0, column=0, columnspan=8, pady=(20, 10))

# Formulário diarista
tk.Label(aba_diarista, text="Placa:", font=FONTB, bg=BG, fg=BRAN).grid(row=1, column=0, padx=(15,2), sticky="e")
entrada_placa_diarista = tk.Entry(aba_diarista, bg=BG2, fg=BRAN, insertbackground=BRAN, borderwidth=0, font=FONT, width=12)
entrada_placa_diarista.bind("<KeyRelease>", mascara_placa)
entrada_placa_diarista.grid(row=1, column=1, padx=5, pady=6, sticky="ew")

tk.Label(aba_diarista, text="Data:", font=FONTB, bg=BG, fg=BRAN).grid(row=1, column=2, padx=(10,2), sticky="e")
entrada_data_diarista = tk.Entry(aba_diarista, bg=BG2, fg=BRAN, insertbackground=BRAN, borderwidth=0, font=FONT, width=14)
entrada_data_diarista.insert(0, date.today().strftime("%d/%m/%Y"))
entrada_data_diarista.grid(row=1, column=3, padx=5, pady=6, sticky="ew")

tk.Label(aba_diarista, text="Valor (R$):", font=FONTB, bg=BG, fg=BRAN).grid(row=1, column=4, padx=(10,2), sticky="e")
entrada_valor_diarista = tk.Entry(aba_diarista, bg=BG2, fg=BRAN, insertbackground=BRAN, borderwidth=0, font=FONT, width=10)
entrada_valor_diarista.grid(row=1, column=5, padx=5, pady=6, sticky="ew")

aba_diarista.columnconfigure((1, 3, 5), weight=1)

def _preencher_valor_diarista():
    cfg = get_config()
    entrada_valor_diarista.delete(0, tk.END)
    entrada_valor_diarista.insert(0, str(cfg["valor_diarista"]))

def registrar_diarista():
    placa = limpar_placa(entrada_placa_diarista.get())
    data  = entrada_data_diarista.get().strip()
    try:
        valor = float(entrada_valor_diarista.get().replace(",", "."))
    except ValueError:
        messagebox.showerror("Erro", "Valor inválido.")
        return

    if not placa or not validar_placa(placa):
        messagebox.showerror("Erro", "Placa inválida.")
        return

    cursor.execute("SELECT nome, tipo FROM clientes WHERE UPPER(placa) = UPPER(?)", (placa,))
    cli = cursor.fetchone()
    if not cli:
        messagebox.showerror("Erro", "Placa não cadastrada.")
        return
    nome_cli, tipo_cli = cli
    if tipo_cli not in ("diarista", "mensalista", "rotativo"):
        messagebox.showerror("Erro", f"Tipo de cliente não suportado: {tipo_cli}")
        return

    try:
        cursor.execute(
            "INSERT INTO contratos (placa, tipo, data_inicio, valor, pago, ativo) VALUES (?, 'diarista', ?, ?, 1, 1)",
            (placa, data, valor)
        )
        conexao.commit()
        messagebox.showinfo("Sucesso", f"Contrato diarista registrado para {nome_cli} ({formatar_placa_exibicao(placa)}).\nValor: R$ {valor:.2f}")
        entrada_placa_diarista.delete(0, tk.END)
        entrada_data_diarista.delete(0, tk.END)
        entrada_data_diarista.insert(0, date.today().strftime("%d/%m/%Y"))
        _preencher_valor_diarista()
        carregar_tabela_diarista()
    except Exception as e:
        messagebox.showerror("Erro", str(e))

def carregar_tabela_diarista():
    for item in tabela_diarista.get_children():
        tabela_diarista.delete(item)
    cursor.execute("""
        SELECT ct.id, COALESCE(c.nome,'—'), ct.placa, ct.data_inicio, ct.valor, ct.pago
        FROM contratos ct LEFT JOIN clientes c ON UPPER(ct.placa) = UPPER(c.placa)
        WHERE ct.tipo = 'diarista' ORDER BY ct.id DESC
    """)
    for row in cursor.fetchall():
        id_, nome, placa, data, valor, pago = row
        tabela_diarista.insert("", "end", values=(
            id_, nome, formatar_placa_exibicao(placa), data,
            f"R$ {valor:.2f}", "✓ Pago" if pago else "✗ Aberto"
        ), tags=("pago" if pago else "aberto",))

def excluir_contrato_diarista():
    sel = tabela_diarista.selection()
    if not sel:
        messagebox.showwarning("Atenção", "Selecione um registro para excluir.")
        return
    id_ct = tabela_diarista.item(sel[0])["values"][0]
    if not messagebox.askyesno("Confirmar", "Excluir este contrato?"):
        return
    cursor.execute("DELETE FROM contratos WHERE id = ?", (id_ct,))
    conexao.commit()
    carregar_tabela_diarista()

frame_btns_diarista = tk.Frame(aba_diarista, bg=BG)
frame_btns_diarista.grid(row=2, column=0, columnspan=8, pady=(8, 4))

tk.Button(frame_btns_diarista, text="Registrar Diarista", bg=AZUL, fg=BRAN, font=FONTB,
          relief="flat", width=18, cursor="hand2", activebackground=AZUL2, activeforeground=BRAN,
          command=registrar_diarista).pack(side="left", padx=10)
tk.Button(frame_btns_diarista, text="Excluir", bg=VERM, fg=BRAN, font=FONTB,
          relief="flat", width=14, cursor="hand2",
          command=excluir_contrato_diarista).pack(side="left", padx=10)

frame_tab_diarista = tk.Frame(aba_diarista, bg=BG)
frame_tab_diarista.grid(row=3, column=0, columnspan=8, sticky="nsew", padx=15, pady=(6, 12))
aba_diarista.rowconfigure(3, weight=1)

tabela_diarista = ttk.Treeview(frame_tab_diarista,
    columns=("ID", "Cliente", "Placa", "Data", "Valor", "Status"), show="headings", selectmode="browse")
for col, w in [("ID", 50), ("Cliente", 200), ("Placa", 110), ("Data", 120), ("Valor", 90), ("Status", 90)]:
    tabela_diarista.heading(col, text=col)
    tabela_diarista.column(col, width=w, anchor="center")
tabela_diarista.tag_configure("pago",   foreground=AZUL2)
tabela_diarista.tag_configure("aberto", foreground=VERM)
sb_dia = ttk.Scrollbar(frame_tab_diarista, orient="vertical", command=tabela_diarista.yview)
tabela_diarista.configure(yscrollcommand=sb_dia.set)
tabela_diarista.pack(side="left", fill="both", expand=True)
sb_dia.pack(side="right", fill="y")

# --- Sub-aba Mensalista ---
aba_mensalista = tk.Frame(sub_nb_contratos, bg=BG)
sub_nb_contratos.add(aba_mensalista, text="Mensalista")

tk.Label(aba_mensalista, text="CONTRATO MENSALISTA", font=FONTH, bg=BG, fg=AZUL).grid(
    row=0, column=0, columnspan=10, pady=(16, 8))

# Linha de campos
tk.Label(aba_mensalista, text="Placa:", font=FONTB, bg=BG, fg=BRAN).grid(row=1, column=0, padx=(15,2), sticky="e")
entrada_placa_mensal = tk.Entry(aba_mensalista, bg=BG2, fg=BRAN, insertbackground=BRAN, borderwidth=0, font=FONT, width=12)
entrada_placa_mensal.bind("<KeyRelease>", mascara_placa)
entrada_placa_mensal.grid(row=1, column=1, padx=5, pady=6, sticky="ew")

tk.Label(aba_mensalista, text="Mês/Ano (MM/AAAA):", font=FONTB, bg=BG, fg=BRAN).grid(row=1, column=2, padx=(10,2), sticky="e")
entrada_mes_mensal = tk.Entry(aba_mensalista, bg=BG2, fg=BRAN, insertbackground=BRAN, borderwidth=0, font=FONT, width=12)
entrada_mes_mensal.insert(0, date.today().strftime("%m/%Y"))
entrada_mes_mensal.grid(row=1, column=3, padx=5, pady=6, sticky="ew")

tk.Label(aba_mensalista, text="Valor mensal (R$):", font=FONTB, bg=BG, fg=BRAN).grid(row=1, column=4, padx=(10,2), sticky="e")
entrada_valor_mensal = tk.Entry(aba_mensalista, bg=BG2, fg=BRAN, insertbackground=BRAN, borderwidth=0, font=FONT, width=10)
entrada_valor_mensal.grid(row=1, column=5, padx=5, pady=6, sticky="ew")

tk.Label(aba_mensalista, text="Valor do contrato:", font=FONTB, bg=BG, fg=CINZA).grid(row=1, column=6, padx=(10,2), sticky="e")
lbl_valor_final_mensal = tk.Label(aba_mensalista, text="—", font=FONTB, bg=BG, fg=AZUL2, width=10)
lbl_valor_final_mensal.grid(row=1, column=7, padx=5, pady=6, sticky="w")

aba_mensalista.columnconfigure((1, 3, 5), weight=1)

# ── Calendário interativo ──────────────────────────────────
import calendar as _cal_mod

# Wrapper centralizado — não expande verticalmente
frame_cal_center = tk.Frame(aba_mensalista, bg=BG)
frame_cal_center.grid(row=2, column=0, columnspan=10, pady=(6, 4))

# Container horizontal: calendário | atalhos
frame_cal_outer = tk.Frame(frame_cal_center, bg=BG)
frame_cal_outer.pack()

# Painel esquerdo: calendário
frame_cal_left = tk.Frame(frame_cal_outer, bg=BG2, highlightbackground=AZUL, highlightthickness=1)
frame_cal_left.pack(side="left", padx=(0, 10))

# Cabeçalho do calendário
frame_cal_header = tk.Frame(frame_cal_left, bg=AZUL)
frame_cal_header.pack(fill="x")

btn_mes_prev = tk.Button(frame_cal_header, text="◀", font=FONTB, bg=AZUL, fg=BRAN,
                         relief="flat", cursor="hand2", activebackground=AZUL2, activeforeground=BRAN, bd=0)
btn_mes_prev.pack(side="left", padx=10, pady=5)

lbl_mes_cal = tk.Label(frame_cal_header, text="", font=FONTB, bg=AZUL, fg=BRAN, width=18, anchor="center")
lbl_mes_cal.pack(side="left", expand=True)

btn_mes_next = tk.Button(frame_cal_header, text="▶", font=FONTB, bg=AZUL, fg=BRAN,
                         relief="flat", cursor="hand2", activebackground=AZUL2, activeforeground=BRAN, bd=0)
btn_mes_next.pack(side="right", padx=10, pady=5)

# Grade do calendário
frame_cal_grade = tk.Frame(frame_cal_left, bg=BG2)
frame_cal_grade.pack(padx=10, pady=8)

dias_header = ["Seg", "Ter", "Qua", "Qui", "Sex", "Sáb", "Dom"]
for ci, dh in enumerate(dias_header):
    cor_h = VERM if dh in ("Sáb", "Dom") else CINZA
    tk.Label(frame_cal_grade, text=dh, font=FONTB, bg=BG2, fg=cor_h, width=4).grid(
        row=0, column=ci, padx=2, pady=(2, 4))

# Estado do calendário
_cal_ano  = [date.today().year]
_cal_mes  = [date.today().month]
_dias_botoes  = {}   # num_dia -> Button widget
_dias_ativos  = {}   # num_dia -> bool (True = incluso no contrato)

def _atualizar_valor_final_mensal():
    try:
        base = float(entrada_valor_mensal.get().replace(",", "."))
    except ValueError:
        lbl_valor_final_mensal.config(text="—")
        return
    dias_selecionados = sum(1 for v in _dias_ativos.values() if v)
    # calcula total dias úteis do mês para proporção
    total_dias_mes = _cal_mod.monthrange(_cal_ano[0], _cal_mes[0])[1]
    if total_dias_mes == 0:
        lbl_valor_final_mensal.config(text="—")
        return
    proporcional = round(base * (dias_selecionados / total_dias_mes), 2)
    lbl_valor_final_mensal.config(text=f"R$ {proporcional:.2f}")

def _toggle_dia(dia):
    _dias_ativos[dia] = not _dias_ativos[dia]
    ativo = _dias_ativos[dia]
    btn = _dias_botoes[dia]
    btn.configure(bg=AZUL if ativo else BG3, fg=BRAN if ativo else CINZA,
                  relief="flat" if ativo else "flat")
    _atualizar_valor_final_mensal()

def _renderizar_calendario():
    for w in list(_dias_botoes.values()):
        w.destroy()
    _dias_botoes.clear()
    _dias_ativos.clear()

    ano, mes = _cal_ano[0], _cal_mes[0]
    nomes_mes = ["Janeiro","Fevereiro","Março","Abril","Maio","Junho",
                 "Julho","Agosto","Setembro","Outubro","Novembro","Dezembro"]
    lbl_mes_cal.config(text=f"{nomes_mes[mes-1]} {ano}")
    entrada_mes_mensal.delete(0, tk.END)
    entrada_mes_mensal.insert(0, f"{mes:02d}/{ano}")

    cal = _cal_mod.monthcalendar(ano, mes)
    for ri, semana in enumerate(cal):
        for ci, dia in enumerate(semana):
            if dia == 0:
                tk.Label(frame_cal_grade, text="", bg=BG2, width=4).grid(
                    row=ri+1, column=ci, padx=2, pady=2)
                continue
            is_fds = ci >= 5  # sábado/domingo
            _dias_ativos[dia] = True  # todos ativos por padrão
            cor_bg = AZUL if not is_fds else AZUL2
            btn = tk.Button(frame_cal_grade, text=str(dia), font=FONT,
                            bg=cor_bg, fg=BRAN, relief="flat",
                            width=4, cursor="hand2",
                            activebackground=AZUL2, activeforeground=BRAN,
                            command=lambda d=dia: _toggle_dia(d))
            btn.grid(row=ri+1, column=ci, padx=2, pady=2, ipady=3)
            _dias_botoes[dia] = btn
    _atualizar_valor_final_mensal()

def _mes_anterior():
    m, a = _cal_mes[0] - 1, _cal_ano[0]
    if m < 1:
        m, a = 12, a - 1
    _cal_mes[0], _cal_ano[0] = m, a
    _renderizar_calendario()

def _mes_seguinte():
    m, a = _cal_mes[0] + 1, _cal_ano[0]
    if m > 12:
        m, a = 1, a + 1
    _cal_mes[0], _cal_ano[0] = m, a
    _renderizar_calendario()

btn_mes_prev.config(command=_mes_anterior)
btn_mes_next.config(command=_mes_seguinte)
entrada_valor_mensal.bind("<KeyRelease>", lambda e: _atualizar_valor_final_mensal())

# Painel direito: atalhos + resumo
frame_cal_right = tk.Frame(frame_cal_outer, bg=BG2, highlightbackground=AZUL, highlightthickness=1, width=200)
frame_cal_right.pack(side="left", fill="y")
frame_cal_right.pack_propagate(False)

tk.Label(frame_cal_right, text="Atalhos rápidos", font=FONTB, bg=AZUL, fg=BRAN).pack(fill="x", ipady=5)

def _selecionar_todos():
    for dia, btn in _dias_botoes.items():
        _dias_ativos[dia] = True
        btn.configure(bg=AZUL if _cal_mod.weekday(_cal_ano[0], _cal_mes[0], dia) < 5 else AZUL2)
    _atualizar_valor_final_mensal()

def _desmarcar_todos():
    for dia, btn in _dias_botoes.items():
        _dias_ativos[dia] = False
        btn.configure(bg=BG3, fg=CINZA)
    _atualizar_valor_final_mensal()

def _apenas_uteis():
    for dia, btn in _dias_botoes.items():
        wd = _cal_mod.weekday(_cal_ano[0], _cal_mes[0], dia)
        _dias_ativos[dia] = wd < 5
        btn.configure(bg=AZUL if wd < 5 else BG3, fg=BRAN if wd < 5 else CINZA)
    _atualizar_valor_final_mensal()

def _apenas_fds():
    for dia, btn in _dias_botoes.items():
        wd = _cal_mod.weekday(_cal_ano[0], _cal_mes[0], dia)
        _dias_ativos[dia] = wd >= 5
        btn.configure(bg=AZUL2 if wd >= 5 else BG3, fg=BRAN if wd >= 5 else CINZA)
    _atualizar_valor_final_mensal()

for txt, cmd in [
    ("Selecionar todos",    _selecionar_todos),
    ("Desmarcar todos",     _desmarcar_todos),
    ("Apenas dias uteis",   _apenas_uteis),
    ("Apenas fim de semana", _apenas_fds),
]:
    tk.Button(frame_cal_right, text=txt, font=FONT, bg=BG3, fg=BRAN,
              relief="flat", cursor="hand2", anchor="w", padx=14, pady=6,
              activebackground=AZUL, activeforeground=BRAN,
              command=cmd).pack(fill="x", pady=1)

tk.Label(frame_cal_right, text="", bg=BG2).pack(expand=True)

lbl_resumo_cal = tk.Label(frame_cal_right, text="0 dias selecionados",
                           font=FONT, bg=BG2, fg=CINZA, wraplength=200)
lbl_resumo_cal.pack(pady=(4, 10))

_orig_atualizar = _atualizar_valor_final_mensal
def _atualizar_valor_final_mensal():
    _orig_atualizar()
    dias_sel = sum(1 for v in _dias_ativos.values() if v)
    lbl_resumo_cal.config(text=f"{dias_sel} dia(s) selecionado(s)")

# Sobrescreve os comandos dos botões de atalho para usar nova versão
btn_mes_prev.config(command=_mes_anterior)
btn_mes_next.config(command=_mes_seguinte)
entrada_valor_mensal.bind("<KeyRelease>", lambda e: _atualizar_valor_final_mensal())

# redefinir _toggle_dia para usar nova versão
def _toggle_dia(dia):
    _dias_ativos[dia] = not _dias_ativos[dia]
    ativo = _dias_ativos[dia]
    btn = _dias_botoes[dia]
    wd = _cal_mod.weekday(_cal_ano[0], _cal_mes[0], dia)
    cor = (AZUL2 if wd >= 5 else AZUL) if ativo else BG3
    cor_fg = BRAN if ativo else CINZA
    btn.configure(bg=cor, fg=cor_fg)
    _atualizar_valor_final_mensal()

_renderizar_calendario()

def _preencher_valor_mensal():
    cfg = get_config()
    entrada_valor_mensal.delete(0, tk.END)
    entrada_valor_mensal.insert(0, str(cfg["valor_mensalista"]))
    _atualizar_valor_final_mensal()

def registrar_mensalista():
    placa   = limpar_placa(entrada_placa_mensal.get())
    mes_ano = entrada_mes_mensal.get().strip()

    # Valor final proporcional (exibido no label), senão usa o base
    try:
        txt_final = lbl_valor_final_mensal.cget("text").replace("R$", "").replace(",", ".").strip()
        valor = float(txt_final) if txt_final != "—" else float(entrada_valor_mensal.get().replace(",", "."))
    except ValueError:
        messagebox.showerror("Erro", "Valor inválido.")
        return

    if not placa or not validar_placa(placa):
        messagebox.showerror("Erro", "Placa inválida.")
        return

    cursor.execute("SELECT nome, tipo FROM clientes WHERE UPPER(placa) = UPPER(?)", (placa,))
    cli = cursor.fetchone()
    if not cli:
        messagebox.showerror("Erro", "Placa não cadastrada.")
        return

    # Monta string de dias a partir do calendário
    dias_ativos_lista = sorted([d for d, v in _dias_ativos.items() if v])
    if len(dias_ativos_lista) == _cal_mod.monthrange(_cal_ano[0], _cal_mes[0])[1]:
        dias_str = "Todos os dias"
    elif dias_ativos_lista:
        dias_str = ",".join(str(d) for d in dias_ativos_lista)
    else:
        messagebox.showerror("Erro", "Selecione ao menos um dia no calendário.")
        return

    try:
        partes   = mes_ano.split("/")
        mes_int  = int(partes[0])
        ano_int  = int(partes[1])
        data_inicio = f"{ano_int:04d}-{mes_int:02d}-01"
        import calendar as _c
        ultimo_dia  = _c.monthrange(ano_int, mes_int)[1]
        data_fim    = f"{ano_int:04d}-{mes_int:02d}-{ultimo_dia:02d}"
    except Exception:
        data_inicio = date.today().strftime("%Y-%m-%d")
        data_fim    = None

    cursor.execute(
        "INSERT INTO contratos (placa, tipo, data_inicio, data_fim, dias_semana, valor, pago, ativo) VALUES (?, 'mensalista', ?, ?, ?, ?, 1, 1)",
        (placa, data_inicio, data_fim, dias_str, valor)
    )
    conexao.commit()
    messagebox.showinfo("Sucesso",
        f"Contrato mensalista registrado para {formatar_placa_exibicao(placa)} ({cli[0]}).\n"
        f"Dias: {dias_str}\nValor: R$ {valor:.2f}")
    entrada_placa_mensal.delete(0, tk.END)
    _preencher_valor_mensal()
    _renderizar_calendario()
    carregar_tabela_mensalista()

def carregar_tabela_mensalista():
    for item in tabela_mensalista.get_children():
        tabela_mensalista.delete(item)
    cursor.execute("""
        SELECT ct.id, COALESCE(c.nome,'—'), ct.placa, ct.data_inicio, ct.data_fim, ct.dias_semana, ct.valor, ct.pago
        FROM contratos ct LEFT JOIN clientes c ON UPPER(ct.placa) = UPPER(c.placa)
        WHERE ct.tipo = 'mensalista' ORDER BY ct.id DESC
    """)
    for row in cursor.fetchall():
        id_, nome, placa, d_ini, d_fim, dias, valor, pago = row
        tabela_mensalista.insert("", "end", values=(
            id_, nome, formatar_placa_exibicao(placa),
            d_ini or "—", d_fim or "—", dias or "Todos",
            f"R$ {valor:.2f}", "✓ Pago" if pago else "✗ Aberto"
        ), tags=("pago" if pago else "aberto",))

def excluir_contrato_mensalista():
    sel = tabela_mensalista.selection()
    if not sel:
        messagebox.showwarning("Atenção", "Selecione um registro para excluir.")
        return
    id_ct = tabela_mensalista.item(sel[0])["values"][0]
    if not messagebox.askyesno("Confirmar", "Excluir este contrato?"):
        return
    cursor.execute("DELETE FROM contratos WHERE id = ?", (id_ct,))
    conexao.commit()
    carregar_tabela_mensalista()

frame_btns_mensal = tk.Frame(aba_mensalista, bg=BG)
frame_btns_mensal.grid(row=3, column=0, columnspan=10, pady=(8, 4))

tk.Button(frame_btns_mensal, text="Registrar Mensalista", bg=AZUL, fg=BRAN, font=FONTB,
          relief="flat", width=18, cursor="hand2", activebackground=AZUL2, activeforeground=BRAN,
          command=registrar_mensalista).pack(side="left", padx=10)
tk.Button(frame_btns_mensal, text="Excluir", bg=VERM, fg=BRAN, font=FONTB,
          relief="flat", width=14, cursor="hand2",
          command=excluir_contrato_mensalista).pack(side="left", padx=10)

frame_tab_mensal = tk.Frame(aba_mensalista, bg=BG)
frame_tab_mensal.grid(row=4, column=0, columnspan=10, sticky="nsew", padx=15, pady=(6, 12))
aba_mensalista.rowconfigure(4, weight=1)

tabela_mensalista = ttk.Treeview(frame_tab_mensal,
    columns=("ID", "Cliente", "Placa", "Início", "Fim", "Dias", "Valor", "Status"), show="headings", selectmode="browse")
for col, w in [("ID", 40), ("Cliente", 160), ("Placa", 90), ("Início", 90), ("Fim", 90), ("Dias", 180), ("Valor", 80), ("Status", 80)]:
    tabela_mensalista.heading(col, text=col)
    tabela_mensalista.column(col, width=w, anchor="center")
tabela_mensalista.tag_configure("pago",   foreground=AZUL2)
tabela_mensalista.tag_configure("aberto", foreground=VERM)
sb_men = ttk.Scrollbar(frame_tab_mensal, orient="vertical", command=tabela_mensalista.yview)
tabela_mensalista.configure(yscrollcommand=sb_men.set)
tabela_mensalista.pack(side="left", fill="both", expand=True)
sb_men.pack(side="right", fill="y")

# ===========================================================
# --- ABA MAPA DE VAGAS ---
# ===========================================================
aba_mapa = tk.Frame(abas, bg=BG)
abas.add(aba_mapa, text="Mapa de vagas")

tk.Label(aba_mapa, text="MAPA DE VAGAS", font=FONTH, bg=BG, fg=AZUL).pack(pady=(18, 6))

frame_legenda = tk.Frame(aba_mapa, bg=BG)
frame_legenda.pack(pady=(0, 10))
tk.Canvas(frame_legenda, width=18, height=18, bg=AZUL, highlightthickness=0).pack(side="left", padx=(0, 4))
tk.Label(frame_legenda, text="Livre", font=FONT, bg=BG, fg=BRAN).pack(side="left", padx=(0, 18))
tk.Canvas(frame_legenda, width=18, height=18, bg=VERM, highlightthickness=0).pack(side="left", padx=(0, 4))
tk.Label(frame_legenda, text="Ocupada", font=FONT, bg=BG, fg=BRAN).pack(side="left")

frame_secoes = tk.Frame(aba_mapa, bg=BG)
frame_secoes.pack(expand=True, fill="both", padx=30, pady=10)

VAGAS_POR_SECAO = 10
NUM_SECOES      = TOTAL_VAGAS // VAGAS_POR_SECAO
COLS_POR_SECAO  = 5
CELL_W = 80
CELL_H = 64
PAD    = 10

_vaga_canvas: dict = {}
_vaga_label:  dict = {}

for s in range(NUM_SECOES):
    inicio = s * VAGAS_POR_SECAO + 1
    fim    = inicio + VAGAS_POR_SECAO - 1
    frame_sec = tk.Frame(frame_secoes, bg=BG2, bd=0, relief="flat")
    frame_sec.pack(side="left", expand=True, fill="both", padx=12, pady=4)
    tk.Label(frame_sec, text=f"Seção {s + 1}  (vagas {inicio}–{fim})",
             font=FONTB, bg=BG2, fg=CINZA).grid(row=0, column=0, columnspan=COLS_POR_SECAO, pady=(10, 8))
    for i in range(VAGAS_POR_SECAO):
        num_vaga = inicio + i
        row_grid = (i // COLS_POR_SECAO) + 1
        col_grid =  i  % COLS_POR_SECAO
        cell = tk.Canvas(frame_sec, width=CELL_W, height=CELL_H,
                         bg=AZUL, highlightthickness=0, cursor="arrow")
        cell.grid(row=row_grid, column=col_grid, padx=PAD, pady=PAD)
        lbl = cell.create_text(CELL_W // 2, CELL_H // 2,
                               text=str(num_vaga), font=("Arial", 14, "bold"), fill=BRAN)
        _vaga_canvas[num_vaga] = cell
        _vaga_label[num_vaga]  = lbl
    for c in range(COLS_POR_SECAO):
        frame_sec.columnconfigure(c, weight=1)

# ===========================================================
# --- ABA FINANCEIRO ---
# ===========================================================
aba_financeiro = tk.Frame(abas, bg=BG)
abas.add(aba_financeiro, text="Financeiro")

sub_nb_financeiro = ttk.Notebook(aba_financeiro, style="Sub.TNotebook")
sub_nb_financeiro.pack(expand=True, fill="both", padx=0, pady=10)

# ---- Sub-aba: Dashboard ----
aba_fin_dashboard = tk.Frame(sub_nb_financeiro, bg=BG)
sub_nb_financeiro.add(aba_fin_dashboard, text="Resumo Financeiro")

tk.Label(aba_fin_dashboard, text="RESUMO FINANCEIRO", font=FONTH, bg=BG, fg=AZUL).pack(pady=(20, 16))

frame_cards_fin = tk.Frame(aba_fin_dashboard, bg=BG)
frame_cards_fin.pack(fill="x", padx=30, pady=(0, 16))

def _criar_card_fin(parent, titulo, valor_var, cor):
    card = tk.Frame(parent, bg=BG2, highlightbackground=cor, highlightthickness=2)
    card.pack(side="left", expand=True, fill="both", padx=10, pady=4)
    tk.Label(card, text=titulo, font=FONTB, bg=BG2, fg=CINZA).pack(pady=(14, 4))
    lbl = tk.Label(card, textvariable=valor_var, font=("Arial", 20, "bold"), bg=BG2, fg=cor)
    lbl.pack(pady=(0, 14))
    return lbl

var_fin_dia   = tk.StringVar(value="R$ 0,00")
var_fin_mes   = tk.StringVar(value="R$ 0,00")
var_fin_ano   = tk.StringVar(value="R$ 0,00")
var_fin_total = tk.StringVar(value="R$ 0,00")

_criar_card_fin(frame_cards_fin, "Hoje",       var_fin_dia,   AZUL)
_criar_card_fin(frame_cards_fin, "Mês",        var_fin_mes,   AZUL2)
_criar_card_fin(frame_cards_fin, "Ano",        var_fin_ano,   VERM)
_criar_card_fin(frame_cards_fin, "Total Geral",var_fin_total, CINZA)

# Tabela detalhada por período
tk.Label(aba_fin_dashboard, text="Detalhe de recebimentos por período:", font=FONTB, bg=BG, fg=CINZA).pack(anchor="w", padx=30, pady=(6, 4))

frame_tab_fin = tk.Frame(aba_fin_dashboard, bg=BG)
frame_tab_fin.pack(fill="both", expand=True, padx=30, pady=(0, 10))

tabela_fin_detalhe = ttk.Treeview(frame_tab_fin,
    columns=("Tipo", "Qtd", "Total"), show="headings", selectmode="none")
for col, w in [("Tipo", 200), ("Qtd", 100), ("Total", 160)]:
    tabela_fin_detalhe.heading(col, text=col)
    tabela_fin_detalhe.column(col, width=w, anchor="center")
sb_fin = ttk.Scrollbar(frame_tab_fin, orient="vertical", command=tabela_fin_detalhe.yview)
tabela_fin_detalhe.configure(yscrollcommand=sb_fin.set)
tabela_fin_detalhe.pack(side="left", fill="both", expand=True)
sb_fin.pack(side="right", fill="y")

tk.Button(aba_fin_dashboard, text="🔄 Atualizar", font=FONTB, bg=AZUL, fg=BRAN,
          relief="flat", cursor="hand2", activebackground=AZUL2, activeforeground=BRAN,
          command=lambda: atualizar_dashboard_financeiro()).pack(pady=10)

def atualizar_dashboard_financeiro():
    hoje   = date.today().strftime("%Y-%m-%d")
    mes    = date.today().strftime("%Y-%m")
    ano    = date.today().strftime("%Y")

    # Rotativo — usa tabela movimentacoes
    def soma_mov(filtro_sql, params=()):
        cursor.execute(f"SELECT COUNT(*), COALESCE(SUM(valor),0) FROM movimentacoes WHERE pago=1 AND {filtro_sql}", params)
        return cursor.fetchone()

    # Contratos — usa tabela contratos
    def soma_contratos(filtro_sql, params=()):
        cursor.execute(f"SELECT COUNT(*), COALESCE(SUM(valor),0) FROM contratos WHERE pago=1 AND {filtro_sql}", params)
        return cursor.fetchone()

    # Hoje
    qtd_rot_dia,  tot_rot_dia  = soma_mov("data = ?", (date.today().strftime("%d-%m-%Y"),))
    qtd_dia_dia,  tot_dia_dia  = soma_contratos("tipo='diarista' AND data_inicio LIKE ?", (f"%-%-{date.today().strftime('%d')}",))
    qtd_men_dia,  tot_men_dia  = (0, 0)
    total_dia = tot_rot_dia + tot_dia_dia

    # Mês
    qtd_rot_mes,  tot_rot_mes  = soma_mov("data LIKE ?", (f"%-%-{date.today().strftime('%Y')}",))  # fallback
    # Melhor: buscar por ano-mês no campo data
    cursor.execute("SELECT COUNT(*), COALESCE(SUM(valor),0) FROM movimentacoes WHERE pago=1 AND (data LIKE ? OR data LIKE ?)",
                   (f"%/{date.today().strftime('%m/%Y')}%", f"%-{date.today().strftime('%m-%Y')}%"))
    r = cursor.fetchone(); qtd_rot_mes, tot_rot_mes = r[0], r[1]
    cursor.execute("SELECT COUNT(*), COALESCE(SUM(valor),0) FROM contratos WHERE pago=1 AND tipo='diarista' AND (data_inicio LIKE ? OR data_inicio LIKE ?)",
                   (f"{ano}-{date.today().strftime('%m')}%", f"%/{date.today().strftime('%m/%Y')}%"))
    r2 = cursor.fetchone(); qtd_dia_mes, tot_dia_mes = r2[0], r2[1]
    cursor.execute("SELECT COUNT(*), COALESCE(SUM(valor),0) FROM contratos WHERE pago=1 AND tipo='mensalista' AND data_inicio LIKE ?",
                   (f"{ano}-{date.today().strftime('%m')}%",))
    r3 = cursor.fetchone(); qtd_men_mes, tot_men_mes = r3[0], r3[1]
    total_mes = tot_rot_mes + tot_dia_mes + tot_men_mes

    # Ano
    cursor.execute("SELECT COUNT(*), COALESCE(SUM(valor),0) FROM movimentacoes WHERE pago=1 AND (data LIKE ? OR data LIKE ?)",
                   (f"%/{ano}%", f"%-{ano}%"))
    r = cursor.fetchone(); qtd_rot_ano, tot_rot_ano = r[0], r[1]
    cursor.execute("SELECT COUNT(*), COALESCE(SUM(valor),0) FROM contratos WHERE pago=1 AND data_inicio LIKE ?", (f"{ano}%",))
    r2 = cursor.fetchone(); qtd_ct_ano, tot_ct_ano = r2[0], r2[1]
    total_ano = tot_rot_ano + tot_ct_ano

    # Total geral
    cursor.execute("SELECT COALESCE(SUM(valor),0) FROM movimentacoes WHERE pago=1")
    tot_mov_all = cursor.fetchone()[0]
    cursor.execute("SELECT COALESCE(SUM(valor),0) FROM contratos WHERE pago=1")
    tot_ct_all = cursor.fetchone()[0]
    total_geral = tot_mov_all + tot_ct_all

    # Hoje simplificado (rotativo do dia)
    cursor.execute("SELECT COUNT(*), COALESCE(SUM(valor),0) FROM movimentacoes WHERE pago=1 AND data=?",
                   (date.today().strftime("%d-%m-%Y"),))
    r = cursor.fetchone(); qtd_rot_dia2, tot_rot_dia2 = r[0], r[1]
    cursor.execute("SELECT COUNT(*), COALESCE(SUM(valor),0) FROM contratos WHERE pago=1 AND data_inicio=?",
                   (date.today().strftime("%Y-%m-%d"),))
    r2 = cursor.fetchone(); qtd_ct_dia2, tot_ct_dia2 = r2[0], r2[1]
    total_dia2 = tot_rot_dia2 + tot_ct_dia2

    var_fin_dia.set(f"R$ {total_dia2:,.2f}")
    var_fin_mes.set(f"R$ {total_mes:,.2f}")
    var_fin_ano.set(f"R$ {total_ano:,.2f}")
    var_fin_total.set(f"R$ {total_geral:,.2f}")

    # Detalhe
    for item in tabela_fin_detalhe.get_children():
        tabela_fin_detalhe.delete(item)

    cursor.execute("SELECT COUNT(*), COALESCE(SUM(valor),0) FROM movimentacoes WHERE pago=1")
    r = cursor.fetchone()
    tabela_fin_detalhe.insert("", "end", values=("Rotativo (movimentações)", r[0], f"R$ {r[1]:.2f}"))
    cursor.execute("SELECT COUNT(*), COALESCE(SUM(valor),0) FROM contratos WHERE pago=1 AND tipo='diarista'")
    r = cursor.fetchone()
    tabela_fin_detalhe.insert("", "end", values=("Diaristas (contratos)", r[0], f"R$ {r[1]:.2f}"))
    cursor.execute("SELECT COUNT(*), COALESCE(SUM(valor),0) FROM contratos WHERE pago=1 AND tipo='mensalista'")
    r = cursor.fetchone()
    tabela_fin_detalhe.insert("", "end", values=("Mensalistas (contratos)", r[0], f"R$ {r[1]:.2f}"))
    tabela_fin_detalhe.insert("", "end", values=("TOTAL GERAL", "—", f"R$ {total_geral:.2f}"))

# ---- Sub-aba: Configuração de Preços ----
aba_fin_config = tk.Frame(sub_nb_financeiro, bg=BG)
sub_nb_financeiro.add(aba_fin_config, text="Configuração de Preços")

# Título centralizado
tk.Label(aba_fin_config, text="CONFIGURAÇÃO DE PREÇOS",
         font=FONTH, bg=BG, fg=AZUL).pack(pady=(22, 4))
tk.Label(aba_fin_config, text="Defina as tarifas e regras de cobrança do estacionamento",
         font=FONT, bg=BG, fg=CINZA).pack(pady=(0, 16))

# Container principal centralizado e expansível
frame_cfg_main = tk.Frame(aba_fin_config, bg=BG)
frame_cfg_main.pack(fill="both", expand=True, padx=40, pady=(0, 10))
frame_cfg_main.columnconfigure(0, weight=1)
frame_cfg_main.columnconfigure(1, weight=1)
frame_cfg_main.rowconfigure(0, weight=1)

# ── Bloco 1: Rotativo ──
frame_bloco_rot = tk.Frame(frame_cfg_main, bg=BG2,
                            highlightbackground=AZUL, highlightthickness=1)
frame_bloco_rot.grid(row=0, column=0, sticky="nsew", padx=(0,10), pady=(0,10))
frame_bloco_rot.columnconfigure((0,1), weight=1)

tk.Frame(frame_bloco_rot, bg=AZUL, height=4).grid(row=0, column=0, columnspan=2, sticky="ew")
tk.Label(frame_bloco_rot, text="ROTATIVO", font=FONTB, bg=BG2, fg=AZUL).grid(
    row=1, column=0, columnspan=2, pady=(14,10))

tk.Label(frame_bloco_rot, text="Unidade de cobrança", font=FONTB, bg=BG2, fg=CINZA).grid(
    row=2, column=0, columnspan=2, pady=(4,6))
var_unidade = tk.StringVar(value="hora")
frame_unidade = tk.Frame(frame_bloco_rot, bg=BG2)
frame_unidade.grid(row=3, column=0, columnspan=2, pady=(0,10))
tk.Radiobutton(frame_unidade, text="Por hora", variable=var_unidade, value="hora",
               bg=BG2, fg=BRAN, selectcolor=BG3, activebackground=BG2,
               activeforeground=BRAN, font=FONTB).pack(side="left", padx=20)
tk.Radiobutton(frame_unidade, text="Por 30 minutos", variable=var_unidade, value="30min",
               bg=BG2, fg=BRAN, selectcolor=BG3, activebackground=BG2,
               activeforeground=BRAN, font=FONTB).pack(side="left", padx=20)

tk.Label(frame_bloco_rot, text="Valor por unidade (R$)", font=FONTB, bg=BG2, fg=CINZA).grid(
    row=4, column=0, pady=(8,4), padx=16, sticky="e")
entrada_cfg_rotativo = tk.Entry(frame_bloco_rot, bg=BG3, fg=BRAN, insertbackground=BRAN,
                                 borderwidth=0, font=FONTB, width=12, justify="center")
entrada_cfg_rotativo.grid(row=4, column=1, pady=(8,4), padx=16, sticky="w", ipady=6)

tk.Label(frame_bloco_rot, text="Limite máximo (horas)", font=FONTB, bg=BG2, fg=CINZA).grid(
    row=5, column=0, pady=(4,14), padx=16, sticky="e")
entrada_cfg_limite = tk.Entry(frame_bloco_rot, bg=BG3, fg=BRAN, insertbackground=BRAN,
                               borderwidth=0, font=FONTB, width=12, justify="center")
entrada_cfg_limite.grid(row=5, column=1, pady=(4,14), padx=16, sticky="w", ipady=6)

# Preview rotativo
frame_prev_rot = tk.Frame(frame_bloco_rot, bg=BG3)
frame_prev_rot.grid(row=6, column=0, columnspan=2, sticky="ew", padx=14, pady=(0, 14))
tk.Label(frame_prev_rot, text="Simulação de cobrança", font=FONTB, bg=BG3, fg=CINZA).pack(pady=(8,4))
lbl_exemplo = tk.Label(frame_prev_rot, text="", font=FONT, bg=BG3, fg=AZUL2, justify="center")
lbl_exemplo.pack(pady=(0,10))

# ── Bloco 2: Diarista / Mensalista ──
frame_bloco_dm = tk.Frame(frame_cfg_main, bg=BG2,
                           highlightbackground=AZUL, highlightthickness=1)
frame_bloco_dm.grid(row=0, column=1, sticky="nsew", padx=(10,0), pady=(0,10))
frame_bloco_dm.columnconfigure((0,1), weight=1)

tk.Frame(frame_bloco_dm, bg=AZUL, height=4).grid(row=0, column=0, columnspan=2, sticky="ew")
tk.Label(frame_bloco_dm, text="CONTRATOS", font=FONTB, bg=BG2, fg=AZUL).grid(
    row=1, column=0, columnspan=2, pady=(14,10))

tk.Label(frame_bloco_dm, text="Valor padrão Diarista (R$)", font=FONTB, bg=BG2, fg=CINZA).grid(
    row=2, column=0, pady=(8,4), padx=16, sticky="e")
entrada_cfg_diarista = tk.Entry(frame_bloco_dm, bg=BG3, fg=BRAN, insertbackground=BRAN,
                                 borderwidth=0, font=FONTB, width=12, justify="center")
entrada_cfg_diarista.grid(row=2, column=1, pady=(8,4), padx=16, sticky="w", ipady=6)

tk.Label(frame_bloco_dm, text="Valor padrão Mensalista (R$)", font=FONTB, bg=BG2, fg=CINZA).grid(
    row=3, column=0, pady=(4,14), padx=16, sticky="e")
entrada_cfg_mensalista = tk.Entry(frame_bloco_dm, bg=BG3, fg=BRAN, insertbackground=BRAN,
                                   borderwidth=0, font=FONTB, width=12, justify="center")
entrada_cfg_mensalista.grid(row=3, column=1, pady=(4,14), padx=16, sticky="w", ipady=6)

# Infos sobre contratos
frame_info_dm = tk.Frame(frame_bloco_dm, bg=BG3)
frame_info_dm.grid(row=4, column=0, columnspan=2, sticky="ew", padx=14, pady=(0, 14))
infos = [
    "Diarista — cobrado por dia de uso.",
    "Mensalista — valor proporcional aos dias selecionados no calendário.",
    "Os valores aqui são apenas sugestões e podem ser ajustados no ato do contrato.",
]
for info in infos:
    tk.Label(frame_info_dm, text=f"• {info}", font=("Arial", 9), bg=BG3, fg=CINZA,
             wraplength=280, justify="left", anchor="w").pack(fill="x", padx=12, pady=3)

# ── Botões de ação (row=1 spanning both cols) ──
frame_btn_cfg = tk.Frame(frame_cfg_main, bg=BG)
frame_btn_cfg.grid(row=1, column=0, columnspan=2, pady=(6, 4))

tk.Button(frame_btn_cfg, text="Salvar Configurações", command=lambda: salvar_config_financeiro(),
          bg=AZUL, fg=BRAN, font=FONTB, relief="flat", cursor="hand2",
          activebackground=AZUL2, activeforeground=BRAN, padx=24, pady=10).pack(padx=10)

tk.Label(aba_fin_config,
         text="* As configurações são salvas e aplicadas automaticamente a novos registros.",
         font=("Arial", 9), bg=BG, fg=CINZA).pack(pady=(4, 0))

def atualizar_exemplo(*_):
    try:
        v = float(entrada_cfg_rotativo.get().replace(",", "."))
        u = var_unidade.get()
        if u == "hora":
            lbl_exemplo.config(
                text=f"30 min → R$ {v/2:.2f}     1 hora → R$ {v:.2f}     2 horas → R$ {v*2:.2f}     3 horas → R$ {v*3:.2f}")
        else:
            lbl_exemplo.config(
                text=f"30 min → R$ {v:.2f}     1 hora → R$ {v*2:.2f}     2 horas → R$ {v*4:.2f}     3 horas → R$ {v*6:.2f}")
    except Exception:
        lbl_exemplo.config(text="Preencha o valor acima para ver a simulação")

entrada_cfg_rotativo.bind("<KeyRelease>", atualizar_exemplo)
var_unidade.trace_add("write", atualizar_exemplo)

def carregar_config_financeiro():
    cfg = get_config()
    var_unidade.set(cfg["unidade"])
    entrada_cfg_rotativo.delete(0, tk.END)
    entrada_cfg_rotativo.insert(0, str(cfg["valor_rotativo"]))
    entrada_cfg_diarista.delete(0, tk.END)
    entrada_cfg_diarista.insert(0, str(cfg["valor_diarista"]))
    entrada_cfg_mensalista.delete(0, tk.END)
    entrada_cfg_mensalista.insert(0, str(cfg["valor_mensalista"]))
    entrada_cfg_limite.delete(0, tk.END)
    entrada_cfg_limite.insert(0, str(cfg["limite_rotativo_horas"]))
    atualizar_exemplo()

def salvar_config_financeiro():
    try:
        v_rot  = float(entrada_cfg_rotativo.get().replace(",", "."))
        v_dia  = float(entrada_cfg_diarista.get().replace(",", "."))
        v_men  = float(entrada_cfg_mensalista.get().replace(",", "."))
        limite = int(entrada_cfg_limite.get())
        unid   = var_unidade.get()
    except ValueError:
        messagebox.showerror("Erro", "Preencha todos os valores corretamente.")
        return
    cursor.execute("""
        UPDATE config_financeiro SET unidade=?, valor_rotativo=?, valor_diarista=?,
        valor_mensalista=?, limite_rotativo_horas=? WHERE id=1
    """, (unid, v_rot, v_dia, v_men, limite))
    conexao.commit()
    messagebox.showinfo("Sucesso", "Configurações salvas com sucesso!")
    carregar_config_financeiro()  # recarrega automaticamente

# ===========================================================
# --- ABA RELATÓRIOS ---
# ===========================================================
aba_relatorio = tk.Frame(abas, bg=BG)
abas.add(aba_relatorio, text="Relatórios ")

sub_notebook = ttk.Notebook(aba_relatorio, style="Sub.TNotebook")
sub_notebook.pack(expand=True, fill="both", padx=10, pady=10)

# --- Sub-aba Relatório Clientes ---
sub_aba_clientes = tk.Frame(sub_notebook, bg=BG)
sub_notebook.add(sub_aba_clientes, text="Relatório Clientes")

criar_barra_pesquisa(sub_aba_clientes, pesquisar_rel_clientes)

frame_tree_rel_cli = tk.Frame(sub_aba_clientes, bg=BG)
frame_tree_rel_cli.pack(fill="both", expand=True, padx=15, pady=(4, 4))

tabela_rel_clientes = ttk.Treeview(frame_tree_rel_cli, columns=("Nome", "CPF", "Placa", "Tipo"), show="headings")
for col, w in [("Nome", 220), ("CPF", 160), ("Placa", 110), ("Tipo", 100)]:
    tabela_rel_clientes.heading(col, text=col)
    tabela_rel_clientes.column(col, width=w, anchor="center")
scroll_rel_cli = ttk.Scrollbar(frame_tree_rel_cli, orient="vertical", command=tabela_rel_clientes.yview)
tabela_rel_clientes.configure(yscrollcommand=scroll_rel_cli.set)
tabela_rel_clientes.pack(side="left", fill="both", expand=True)
scroll_rel_cli.pack(side="right", fill="y")

tk.Button(sub_aba_clientes, text="⬇  Exportar PDF", command=exportar_pdf_clientes,
          bg=AZUL2, fg=BRAN, font=FONTB, relief="flat", cursor="hand2",
          activebackground=AZUL2, activeforeground=BRAN, padx=16, pady=6).pack(pady=(4, 12))

# --- Sub-aba Recebimentos ---
sub_aba_recebimentos = tk.Frame(sub_notebook, bg=BG)
sub_notebook.add(sub_aba_recebimentos, text="Recebimentos")

criar_barra_pesquisa(sub_aba_recebimentos, pesquisar_rel_recebimentos)

frame_tree_rec = tk.Frame(sub_aba_recebimentos, bg=BG)
frame_tree_rec.pack(fill="both", expand=True, padx=15, pady=(4, 4))

tabela_rel_recebimentos = ttk.Treeview(frame_tree_rec,
    columns=("ID", "Cliente", "Placa", "Data", "Entrada", "Saída", "Valor"), show="headings")
colunas_recebimentos = {"ID": 50, "Cliente": 150, "Placa": 100, "Data": 110, "Entrada": 80, "Saída": 80, "Valor": 90}
for col in ("ID", "Cliente", "Placa", "Data", "Entrada", "Saída", "Valor"):
    tabela_rel_recebimentos.heading(col, text=col)
    tabela_rel_recebimentos.column(col, width=colunas_recebimentos[col], anchor="center")
scroll_rec = ttk.Scrollbar(frame_tree_rec, orient="vertical", command=tabela_rel_recebimentos.yview)
tabela_rel_recebimentos.configure(yscrollcommand=scroll_rec.set)
tabela_rel_recebimentos.pack(side="left", fill="both", expand=True)
scroll_rec.pack(side="right", fill="y")

tk.Button(sub_aba_recebimentos, text="⬇  Exportar PDF", command=exportar_pdf_recebimentos,
          bg=AZUL2, fg=BRAN, font=FONTB, relief="flat", cursor="hand2",
          activebackground=AZUL2, activeforeground=BRAN, padx=16, pady=6).pack(pady=(4, 12))

# --- Sub-aba Recebimentos em Aberto ---
sub_aba_recebimentos_aberto = tk.Frame(sub_notebook, bg=BG)
sub_notebook.add(sub_aba_recebimentos_aberto, text="Recebimentos em aberto")

criar_barra_pesquisa(sub_aba_recebimentos_aberto, pesquisar_rel_abertos)

frame_tree_aberto = tk.Frame(sub_aba_recebimentos_aberto, bg=BG)
frame_tree_aberto.pack(fill="both", expand=True, padx=15, pady=(4, 4))

tabela_rel_recebimentos_abertos = ttk.Treeview(frame_tree_aberto,
    columns=("ID", "Cliente", "Placa", "Data", "Entrada"), show="headings")
colunas_abertos = {"ID": 50, "Cliente": 150, "Placa": 100, "Data": 110, "Entrada": 80}
for col in ("ID", "Cliente", "Placa", "Data", "Entrada"):
    tabela_rel_recebimentos_abertos.heading(col, text=col)
    tabela_rel_recebimentos_abertos.column(col, width=colunas_abertos[col], anchor="center")
scroll_aberto = ttk.Scrollbar(frame_tree_aberto, orient="vertical", command=tabela_rel_recebimentos_abertos.yview)
tabela_rel_recebimentos_abertos.configure(yscrollcommand=scroll_aberto.set)
tabela_rel_recebimentos_abertos.pack(side="left", fill="both", expand=True)
scroll_aberto.pack(side="right", fill="y")

tk.Button(sub_aba_recebimentos_aberto, text="⬇  Exportar PDF", command=exportar_pdf_abertos,
          bg=AZUL2, fg=BRAN, font=FONTB, relief="flat", cursor="hand2",
          activebackground=AZUL2, activeforeground=BRAN, padx=16, pady=6).pack(pady=(4, 12))

# --- Sub-aba Top 5 Clientes ---
sub_aba_top = tk.Frame(sub_notebook, bg=BG)
sub_notebook.add(sub_aba_top, text="Top 5 Clientes")

criar_barra_pesquisa(sub_aba_top, pesquisar_rel_top)

frame_tree_top = tk.Frame(sub_aba_top, bg=BG)
frame_tree_top.pack(fill="both", expand=True, padx=15, pady=(4, 4))

tabela_rel_top_clientes = ttk.Treeview(frame_tree_top,
    columns=("Nome", "CPF", "Placa", "Visitas"), show="headings")
colunas_top = {"Nome": 150, "CPF": 100, "Placa": 100, "Visitas": 80}
for col in ("Nome", "CPF", "Placa", "Visitas"):
    tabela_rel_top_clientes.heading(col, text=col)
    tabela_rel_top_clientes.column(col, width=colunas_top[col], anchor="center")
scroll_top = ttk.Scrollbar(frame_tree_top, orient="vertical", command=tabela_rel_top_clientes.yview)
tabela_rel_top_clientes.configure(yscrollcommand=scroll_top.set)
tabela_rel_top_clientes.pack(side="left", fill="both", expand=True)
scroll_top.pack(side="right", fill="y")

tk.Button(sub_aba_top, text="⬇  Exportar PDF", command=exportar_pdf_top_clientes,
          bg=AZUL2, fg=BRAN, font=FONTB, relief="flat", cursor="hand2",
          activebackground=AZUL2, activeforeground=BRAN, padx=16, pady=6).pack(pady=(4, 12))

# ===========================================================
# --- INICIALIZAÇÃO ---
# ===========================================================
abas.bind("<<NotebookTabChanged>>", ao_trocar_aba)

carregar_movimentacoes()
carregar_tabela_clientes_cad()
gerar_relatorio_clientes()
gerar_relatorio_recebimentos()
gerar_relatorio_recebimentos_abertos()
gerar_relatorio_top_clientes()
atualizar_mapa_vagas()
atualizar_hora()
carregar_cards_clientes()
carregar_config_financeiro()
carregar_tabela_diarista()
carregar_tabela_mensalista()
_preencher_valor_diarista()
_preencher_valor_mensal()
atualizar_dashboard_financeiro()

janela.mainloop()