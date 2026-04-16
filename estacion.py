import tkinter as tk
from tkinter import ttk, messagebox
from datetime import datetime, date
import re
import sqlite3

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

# BANCO DE DADOS
conexao = sqlite3.connect("estacionamento.db")
cursor = conexao.cursor()

cursor.executescript("""
CREATE TABLE IF NOT EXISTS clientes (
    id    INTEGER PRIMARY KEY AUTOINCREMENT,
    nome  TEXT    NOT NULL,
    cpf   TEXT    NOT NULL UNIQUE,
    placa TEXT    NOT NULL
);

CREATE TABLE IF NOT EXISTS movimentacoes (
    id      INTEGER PRIMARY KEY AUTOINCREMENT,
    placa   TEXT    NOT NULL,
    data    TEXT    NOT NULL,
    entrada TEXT    NOT NULL,
    saida   TEXT,
    valor   REAL    DEFAULT 0.0,
    pago    INTEGER DEFAULT 0,
    FOREIGN KEY (placa) REFERENCES clientes(placa)
);
""")
conexao.commit()

janela = tk.Tk()
janela.title("estaciON")
janela.geometry("900x580")
janela.configure(bg=BG)

# --- ESTILIZAÇÃO DO NOTEBOOK (ABAS) ---
style = ttk.Style()
style.theme_use('default')
style.configure("TNotebook", background=BG, borderwidth=0)
style.configure("TNotebook.Tab", background=BG3, foreground=BRAN, padding=[10, 5], font=FONTB)
style.map("TNotebook.Tab", background=[("selected", AZUL)], foreground=[("selected", BRAN)])
style.configure("TFrame", background=BG)

# Estilo do Treeview
style.configure("Treeview",
    background=BG2,
    foreground=BRAN,
    fieldbackground=BG2,
    rowheight=28,
    font=FONT,
    borderwidth=0
)
style.configure("Treeview.Heading",
    background=BG3,
    foreground=AZUL,
    font=FONTB,
    relief="flat"
)
style.map("Treeview",
    background=[("selected", AZUL)],
    foreground=[("selected", BRAN)]
)
style.map("Treeview.Heading",
    background=[("active", AZUL2)]
)

abas = ttk.Notebook(janela)
abas.pack(expand=True, fill="both", padx=10, pady=10)

# Funções de Validação

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

    padrao_antigo = r'^[A-Z]{3}[0-9]{4}$'
    padrao_mercosul = r'^[A-Z]{3}[0-9][A-Z][0-9]{2}$'

    return re.match(padrao_antigo, placa) or re.match(padrao_mercosul, placa)

# Funções do sistema

def salvar():
    nome = entrada_nomeCliente.get().strip()
    cpf = entrada_cpf.get().strip()
    placa = entrada_placaVeiculo.get()

    if not validar_cpf(cpf):
        messagebox.showerror("Erro", "CPF inválido")
        return

    if not validar_placa(entrada_placaVeiculo.get()):
        messagebox.showerror("Erro", "Placa inválida")
        return

    cursor.execute("SELECT id FROM clientes WHERE cpf = ?", (cpf,))
    if cursor.fetchone():
        messagebox.showerror("Erro", "Este CPF já está cadastrado.")
        return

    cursor.execute("""
        INSERT INTO clientes (nome, cpf, placa)
        VALUES (?, ?, ?)
    """, (nome, cpf, placa))

    conexao.commit()
    messagebox.showinfo("Sucesso", "Cliente registrado com sucesso")


def limpar_movimentacao():
    entrada_placa_mov.delete(0, tk.END)
    entrada_hora_in.delete(0, tk.END)
    entrada_hora_out.delete(0, tk.END)

    entrada_data.delete(0, tk.END)
    entrada_data.insert(0, date.today().strftime("%Y-%m-%d"))

def limpar_tabela():
    selecionado = tabela_mov.selection()

    if not selecionado:
        messagebox.showwarning("Atenção", "Selecione um registro para excluir.")
        return

    item = tabela_mov.item(selecionado)
    id_mov = item["values"][0]

    confirmar = messagebox.askyesno("Confirmar", "Deseja realmente excluir este registro?")
    if not confirmar:
        return

    try:
        cursor.execute("DELETE FROM movimentacoes WHERE id = ?", (id_mov,))
        conexao.commit()

        messagebox.showinfo("Sucesso", "Registro excluído com sucesso!")
        carregar_movimentacoes()

    except Exception as e:
        messagebox.showerror("Erro", str(e))

    entrada_data.delete(0, tk.END)
    entrada_data.insert(0, date.today().strftime("%Y-%m-%d"))

# --- FUNÇÃO PARA CARREGAR MOVIMENTAÇÕES NA TABELA ---
def carregar_movimentacoes():
    for item in tabela_mov.get_children():
        tabela_mov.delete(item)

    cursor.execute("SELECT id, placa, data, entrada, saida, valor, pago FROM movimentacoes ORDER BY id DESC")
    rows = cursor.fetchall()

    for row in rows:
        id_, placa, data, entrada, saida, valor, pago = row

        saida_exib  = saida if saida else "—"
        valor_exib  = f"R$ {valor:.2f}" if valor else "—"
        pago_exib   = "✓" if pago else "✗"

        tag = "nao_pago" if not pago else "pago"

        tabela_mov.insert("", "end",
            values=(id_, placa, data, entrada, saida_exib, valor_exib, pago_exib),
            tags=(tag,)
        )

# --- FUNÇÃO REGISTRAR ENTRADA ---
def registrar_entrada():
    placa = entrada_placa_mov.get().strip().upper()
    data  = entrada_data.get().strip()
    hora_in = entrada_hora_in.get()

    if not placa:
        messagebox.showwarning("Atenção", "Preencha a Placa.")
        return

    if not hora_in:
        messagebox.showwarning("Atenção", "Preencha o Horário de entrada")
        return

    try:
        cursor.execute(
            "INSERT INTO movimentacoes (placa, data, entrada) VALUES (?, ?, ?)",
            (placa, data, hora_in)
        )
        conexao.commit()
        messagebox.showinfo("Sucesso", f"Entrada registrada para {placa} às {hora_in}.")
        limpar_movimentacao()
        carregar_movimentacoes()
    except Exception as e:
        messagebox.showerror("Erro", str(e))

# --- FUNÇÃO REGISTRAR SAÍDA ---
def registrar_saida():
    placa    = entrada_placa_mov.get().strip().upper()
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

    try:
        h_in,  m_in  = map(int, hora_in.split(":"))
        h_out, m_out = map(int, hora_out.split(":"))
        minutos = (h_out * 60 + m_out) - (h_in * 60 + m_in)
        if minutos < 0:
            minutos += 24 * 60
        valor = round((minutos / 60) * 5.0, 2)
    except ValueError:
        valor = 0.0

    try:
        cursor.execute(
            "UPDATE movimentacoes SET saida=?, valor=?, pago=1 WHERE id=?",
            (hora_out, valor, mov_id)
        )
        conexao.commit()
        messagebox.showinfo("Sucesso", f"Saída registrada para {placa}. Valor: R$ {valor:.2f}")
        limpar_movimentacao()
        carregar_movimentacoes()
    except Exception as e:
        messagebox.showerror("Erro", str(e))

# ===========================================================
# --- ABA CADASTRO DE CLIENTES ---
# ===========================================================
aba_cadastroCliente = tk.Frame(abas, bg=BG)
abas.add(aba_cadastroCliente, text="Clientes ")

tk.Label(aba_cadastroCliente, text="CADASTRO DE CLIENTES", font=FONTH, bg=BG, fg=AZUL).grid(row=0, column=0, columnspan=6, pady=20)

labels_cad = ["Nome:", "CPF:", "Placa:"]
for i, texto in enumerate(labels_cad):
    tk.Label(aba_cadastroCliente, text=texto, font=FONTB, bg=BG, fg=BRAN).grid(row=1, column=i*2, padx=10, sticky="e")

entrada_nomeCliente = tk.Entry(aba_cadastroCliente, bg=BG2, fg=BRAN, insertbackground=BRAN, borderwidth=0, font=FONT)
entrada_nomeCliente.grid(row=1, column=1, padx=5, pady=10, sticky="ew")

entrada_cpf = tk.Entry(aba_cadastroCliente, bg=BG2, fg=BRAN, insertbackground=BRAN, borderwidth=0, font=FONT)
entrada_cpf.grid(row=1, column=3, padx=5, pady=10, sticky="ew")

entrada_placaVeiculo = tk.Entry(aba_cadastroCliente, bg=BG2, fg=BRAN, insertbackground=BRAN, borderwidth=0, font=FONT)
entrada_placaVeiculo.grid(row=1, column=5, padx=5, pady=10, sticky="ew")

frame_botoes_cad = tk.Frame(aba_cadastroCliente, bg=BG)
frame_botoes_cad.grid(row=2, column=0, columnspan=9, pady=30)

btn_registrar_cliente = tk.Button(frame_botoes_cad, text="Registrar cliente", command=salvar, bg=AZUL, fg=BRAN, font=FONTB,
                                   relief="flat", width=18, cursor="hand2", activebackground=AZUL2, activeforeground=BRAN)
btn_registrar_cliente.pack(side="left", padx=10)

aba_cadastroCliente.columnconfigure((1, 3, 5), weight=1)


# ===========================================================
# --- ABA MOVIMENTAÇÃO ---
# ===========================================================
aba_movimentacao = tk.Frame(abas, bg=BG)
abas.add(aba_movimentacao, text="Movimentação ")

tk.Label(aba_movimentacao, text="MOVIMENTAÇÃO DE VAGAS", font=FONTH, bg=BG, fg=AZUL).grid(row=0, column=0, columnspan=9, pady=(20, 10))

# --- Linha de inputs ---
tk.Label(aba_movimentacao, text="Placa", font=FONTB, bg=BG, fg=BRAN).grid(row=1, column=0, padx=(15,2), sticky="e")
entrada_placa_mov = tk.Entry(aba_movimentacao, bg=BG2, fg=BRAN, insertbackground=BRAN, borderwidth=0, font=FONT, width=12)
entrada_placa_mov.grid(row=1, column=1, padx=5, pady=6, sticky="ew")

tk.Label(aba_movimentacao, text="Data (AAAA-MM-DD)", font=FONTB, bg=BG, fg=BRAN).grid(row=1, column=2, padx=(10,2), sticky="e")
entrada_data = tk.Entry(aba_movimentacao, bg=BG2, fg=BRAN, insertbackground=BRAN, borderwidth=0, font=FONT, width=14)
entrada_data.insert(0, date.today().strftime("%Y-%m-%d"))
entrada_data.grid(row=1, column=3, padx=5, pady=6, sticky="ew")

tk.Label(aba_movimentacao, text="Hora Entrada (HH:MM)", font=FONTB, bg=BG, fg=BRAN).grid(row=1, column=4, padx=(10,2), sticky="e")
entrada_hora_in = tk.Entry(aba_movimentacao, bg=BG2, fg=BRAN, insertbackground=BRAN, borderwidth=0, font=FONT, width=8)
entrada_hora_in.grid(row=1, column=5, padx=5, pady=6, sticky="ew")

tk.Label(aba_movimentacao, text="Hora Saída (HH:MM)", font=FONTB, bg=BG, fg=BRAN).grid(row=1, column=6, padx=(10,2), sticky="e")
entrada_hora_out = tk.Entry(aba_movimentacao, bg=BG2, fg=BRAN, insertbackground=BRAN, borderwidth=0, font=FONT, width=8)
entrada_hora_out.grid(row=1, column=7, padx=5, pady=6, sticky="ew")

aba_movimentacao.columnconfigure((1, 3, 5, 7), weight=1)

# --- TABELA DE MOVIMENTAÇÕES (Treeview) ---
frame_tabela = tk.Frame(aba_movimentacao, bg=BG, bd=1, relief="flat")
frame_tabela.grid(row=3, column=0, columnspan=9, sticky="nsew", padx=15, pady=(0, 15))

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

# --- Botões ---
frame_botoes = tk.Frame(aba_movimentacao, bg=BG)
frame_botoes.grid(row=2, column=0, columnspan=9, pady=(8, 12))

btn_entrada = tk.Button(frame_botoes, text="Registrar Entrada", bg=AZUL, fg=BRAN, font=FONTB,
                        relief="flat", width=18, cursor="hand2",
                        activebackground=AZUL2, activeforeground=BRAN,
                        command=registrar_entrada)
btn_entrada.pack(side="left", padx=10)

btn_saida = tk.Button(frame_botoes, text="Registrar Saída", bg=VERM, fg=BRAN, font=FONTB,
                       relief="flat", width=18, cursor="hand2",
                       activebackground="#E53935", activeforeground=BRAN,
                       command=registrar_saida)
btn_saida.pack(side="left", padx=10)

btn_limpar = tk.Button(frame_botoes, text="Limpar", bg=CINZA, fg=BG, font=FONTB,
                        relief="flat", width=18, cursor="hand2",
                        command=limpar_tabela)
btn_limpar.pack(side="left", padx=10)


# ===========================================================
# --- ABA FINANCEIRO ---
# ===========================================================
aba_financeiro = tk.Frame(abas, bg=BG)
abas.add(aba_financeiro, text="Financeiro ")


# ===========================================================
# --- ABA RELATÓRIOS ---
# ===========================================================
aba_relatorio = tk.Frame(abas, bg=BG)
abas.add(aba_relatorio, text="Relatórios ")

sub_notebook = ttk.Notebook(aba_relatorio)
sub_notebook.pack(expand=True, fill="both")

# Sub-aba clientes
sub_aba_clientes = tk.Frame(sub_notebook)
sub_notebook.add(sub_aba_clientes, text="Relatório Clientes")

tk.Label(sub_aba_clientes, text="Aqui vai o relatório de clientes").pack(pady=20)

# Sub-aba recebimentos
sub_aba_recebimentos = tk.Frame(sub_notebook)
sub_notebook.add(sub_aba_recebimentos, text="Recebimentos")

# Sub-aba recebimentos aberto
sub_aba_recebimentos_aberto = tk.Frame(sub_notebook)
sub_notebook.add(sub_aba_recebimentos_aberto, text="Recebimentos em aberto")

# Sub-aba top 5 clientes
sub_aba_top = tk.Frame(sub_notebook)
sub_notebook.add(sub_aba_top, text="Top 5 Clientes")

# --- Carrega os dados ao iniciar ---
carregar_movimentacoes()

janela.mainloop()