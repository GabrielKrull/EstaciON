import tkinter as tk
from tkinter import ttk, messagebox
from datetime import date

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

# BANCO OF DATA
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
    entrada TEXT    NOT NULL,
    saida   TEXT,
    valor   REAL    DEFAULT 0.0,
    pago    INTEGER DEFAULT 0,0
    FOREIGN KEY (placa) REFERENCES clientes(placa)
);
""")
conexao.commit()

janela = tk.Tk()
janela.title("estaciON")
janela.geometry("900x500")
janela.configure(bg=BG)

# --- ESTILIZAÇÃO DO NOTEBOOK (ABAS) ---
style = ttk.Style()
style.theme_use('default')
style.configure("TNotebook", background=BG, borderwidth=0)
style.configure("TNotebook.Tab", background=BG3, foreground=BRAN, padding=[10, 5], font=FONTB)
style.map("TNotebook.Tab", background=[("selected", AZUL)], foreground=[("selected", BRAN)])
style.configure("TFrame", background=BG)

abas = ttk.Notebook(janela)
abas.pack(expand=True, fill="both", padx=10, pady=10)

# --- FUNÇÃO AUXILIAR PARA LIMPAR ---
def limpar_movimentacao():
    entrada_placa_mov.delete(0, tk.END)
    entrada_hora_in.delete(0, tk.END)
    entrada_hora_out.delete(0, tk.END)

# --- ABA CADASTRO DE CLIENTES ---
aba_cadastroCliente = tk.Frame(abas, bg=BG)
abas.add(aba_cadastroCliente, text="Cadastro de Clientes")

tk.Label(aba_cadastroCliente, text="CADASTRO DE CLIENTES", font=FONTH, bg=BG, fg=AZUL).grid(row=0, column=0, columnspan=6, pady=20)

# Labels e Entrys Estilizados
labels_cad = ["Nome:", "CPF:", "Placa:"]
for i, texto in enumerate(labels_cad):
    tk.Label(aba_cadastroCliente, text=texto, font=FONTB, bg=BG, fg=BRAN).grid(row=1, column=i*2, padx=10, sticky="e")

entrada_nomeCliente = tk.Entry(aba_cadastroCliente, bg=BG2, fg=BRAN, insertbackground=BRAN, borderwidth=0, font=FONT)
entrada_nomeCliente.grid(row=1, column=1, padx=5, pady=10, sticky="ew")

entrada_cpf = tk.Entry(aba_cadastroCliente, bg=BG2, fg=BRAN, insertbackground=BRAN, borderwidth=0, font=FONT)
entrada_cpf.grid(row=1, column=3, padx=5, pady=10, sticky="ew")

entrada_placaVeiculo = tk.Entry(aba_cadastroCliente, bg=BG2, fg=BRAN, insertbackground=BRAN, borderwidth=0, font=FONT)
entrada_placaVeiculo.grid(row=1, column=5, padx=5, pady=10, sticky="ew")

aba_cadastroCliente.columnconfigure((1, 3, 5), weight=1)

# --- ABA MOVIMENTAÇÃO ---
aba_movimentacao = tk.Frame(abas, bg=BG)
abas.add(aba_movimentacao, text="Movimentação")

tk.Label(aba_movimentacao, text="CONTROLE DE FLUXO", font=FONTH, bg=BG, fg=AZUL).grid(row=0, column=0, columnspan=9, pady=20)

# Configuração de entradas de movimentação
# Placa
tk.Label(aba_movimentacao, text="Placa:", font=FONTB, bg=BG, fg=BRAN).grid(row=1, column=1, padx=5, sticky="e")
entrada_placa_mov = tk.Entry(aba_movimentacao, bg=BG2, fg=BRAN, insertbackground=BRAN, borderwidth=0, font=FONT)
entrada_placa_mov.grid(row=1, column=2, padx=5, pady=10, sticky="ew")

# Data
tk.Label(aba_movimentacao, text="Data:", font=FONTB, bg=BG, fg=BRAN).grid(row=1, column=3, padx=5, sticky="e")
entrada_data = tk.Entry(aba_movimentacao, bg=BG2, fg=BRAN, insertbackground=BRAN, borderwidth=0, font=FONT)
entrada_data.insert(0, date.today().strftime("%d/%m/%Y"))
entrada_data.grid(row=1, column=4, padx=5, pady=10, sticky="ew")

# Entrada
tk.Label(aba_movimentacao, text="Entrada:", font=FONTB, bg=BG, fg=BRAN).grid(row=1, column=5, padx=5, sticky="e")
entrada_hora_in = tk.Entry(aba_movimentacao, bg=BG2, fg=BRAN, insertbackground=BRAN, borderwidth=0, font=FONT)
entrada_hora_in.grid(row=1, column=6, padx=5, pady=10, sticky="ew")

# Saída
tk.Label(aba_movimentacao, text="Saída:", font=FONTB, bg=BG, fg=BRAN).grid(row=1, column=7, padx=5, sticky="e")
entrada_hora_out = tk.Entry(aba_movimentacao, bg=BG2, fg=BRAN, insertbackground=BRAN, borderwidth=0, font=FONT)
entrada_hora_out.grid(row=1, column=8, padx=5, pady=10, sticky="ew")

aba_movimentacao.columnconfigure((2, 4, 6, 8), weight=1)

# --- CONTAINER DE BOTÕES ---
frame_botoes = tk.Frame(aba_movimentacao, bg=BG)
frame_botoes.grid(row=2, column=0, columnspan=9, pady=30)

btn_entrada = tk.Button(frame_botoes, text="Registrar Entrada", bg=AZUL, fg=BRAN, font=FONTB, 
                        relief="flat", width=18, cursor="hand2", activebackground=AZUL2, activeforeground=BRAN)
btn_entrada.pack(side="left", padx=10)

btn_saida = tk.Button(frame_botoes, text="Registrar Saída", bg=VERM, fg=BRAN, font=FONTB, 
                       relief="flat", width=18, cursor="hand2", activebackground="#E53935", activeforeground=BRAN)
btn_saida.pack(side="left", padx=10)

btn_limpar = tk.Button(frame_botoes, text="Limpar", bg=CINZA, fg=BG, font=FONTB, 
                        relief="flat", width=18, cursor="hand2", command=limpar_movimentacao)
btn_limpar.pack(side="left", padx=10)

# Outras abas apenas com fundo configurado
aba_financeiro = tk.Frame(abas, bg=BG)
abas.add(aba_financeiro, text="Financeiro")

aba_relatorio = tk.Frame(abas, bg=BG)
abas.add(aba_relatorio, text="Relatório")

janela.mainloop()