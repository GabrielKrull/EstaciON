import tkinter as tk
from tkinter import ttk, messagebox
from datetime import datetime, date

BG    = "#0a0a0a"
BG2   = "#141414"
BG3   = "#1e1e1e"
AZUL  = "#1565C0"
AZUL2 = "#1976D2"
VERM  = "#C62828"
BRAN  = "#FFFFFF"
CINZA = "#9E9E9E"
FONT  = ("Arial", 10)
FONTB = ("Arial", 10, "bold")
FONTH = ("Arial", 12, "bold")

#Janelas

#Principal

<<<<<<< Updated upstream
import tkinter as tk
from tkinter import ttk
from datetime import date
=======
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
    pago    INTEGER DEFAULT 0,
    FOREIGN KEY (placa) REFERENCES clientes(placa)
);
""")
conexao.commit()
>>>>>>> Stashed changes

janela = tk.Tk()
janela.title("estaciON")
janela.geometry("800x400") # Definindo um tamanho inicial maior

abas = ttk.Notebook(janela)
abas.pack(expand=True, fill="both")

# --- ABA CADASTRO DE CLIENTES ---
aba_cadastroCliente = tk.Frame(abas)
abas.add(aba_cadastroCliente, text="Cadastro de Clientes")

# Título da aba (ocupando todas as colunas)
tk.Label(aba_cadastroCliente, text="CADASTRO DE CLIENTES", font=FONTH).grid(row=0, column=0, columnspan=6, pady=10)

# Configurando a responsividade das colunas de entrada (1, 3 e 5)
aba_cadastroCliente.columnconfigure((1, 3, 5), weight=1)

tk.Label(aba_cadastroCliente, text="Nome:").grid(row=1, column=0, padx=5, sticky="e")
entrada_nomeCliente = tk.Entry(aba_cadastroCliente)
entrada_nomeCliente.grid(row=1, column=1, padx=5, sticky="ew")

tk.Label(aba_cadastroCliente, text="CPF:").grid(row=1, column=2, padx=5, sticky="e")
entrada_cpf = tk.Entry(aba_cadastroCliente)
entrada_cpf.grid(row=1, column=3, padx=5, sticky="ew")

tk.Label(aba_cadastroCliente, text="Placa:").grid(row=1, column=4, padx=5, sticky="e")
entrada_placaVeiculo = tk.Entry(aba_cadastroCliente)
entrada_placaVeiculo.grid(row=1, column=5, padx=5, sticky="ew")

# --- ABA MOVIMENTAÇÃO ---
aba_movimentacao = tk.Frame(abas)
abas.add(aba_movimentacao, text="Movimentação")

# Configurando colunas 2 e 4 para expandirem
aba_movimentacao.columnconfigure((2, 4), weight=1)

tk.Label(aba_movimentacao, text="Placa: ").grid(row=1, column=1, padx=5, sticky="e")
entrada_placa_mov = tk.Entry(aba_movimentacao)
entrada_placa_mov.grid(row=1, column=2, padx=5, sticky="ew")

tk.Label(aba_movimentacao, text="Data: ").grid(row=1, column=3, padx=5, sticky="e")
entrada_data = tk.Entry(aba_movimentacao)
entrada_data.insert(0, date.today().isoformat())
entrada_data.grid(row=1, column=4, padx=5, sticky="ew")

tk.Label(aba_movimentacao,text="Entrada: ").grid(row=1, column=5, padx=5,sticky="e")
entrada_entrada = tk.Entry(aba_movimentacao)
entrada_entrada.grid(row=1, column=6, padx=5, sticky="e")

<<<<<<< Updated upstream
# Outras abas (apenas placeholders)
aba_financeiro = tk.Frame(abas)
abas.add(aba_financeiro, text="Financeiro")

aba_relatorio = tk.Frame(abas)
=======
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

# --- ABA FINANCEIRO ---
aba_financeiro = tk.Frame(abas, bg=BG)
abas.add(aba_financeiro, text="Financeiro")


# --- ABA RELATÓRIO ---
aba_relatorio = tk.Frame(abas, bg=BG)
>>>>>>> Stashed changes
abas.add(aba_relatorio, text="Relatório")
sub_notebook = ttk.Notebook(aba_relatorio)
sub_notebook.pack(expand=True, fill="both")


# Sub-aba clientes
sub_aba_clientes = tk.Frame(sub_notebook)
sub_notebook.add(sub_aba_clientes, text="Relatório Clientes")

tk.Label(sub_aba_clientes, text="Aqui vai o relatório de clientes").pack(pady=20)

#Sub-aba recebimentos
sub_aba_recebimentos = tk.Frame(sub_notebook)
sub_notebook.add(sub_aba_recebimentos, text="Recebimentos")

#Sub-aba recebimentos aberto
sub_aba_recebimentos_aberto = tk.Frame(sub_notebook)
sub_notebook.add(sub_aba_recebimentos_aberto, text="Recebimentos em aberto")

#Sub-aba top 5 clientes 
sub_aba_top_ = tk.Frame(sub_notebook)
sub_notebook.add(sub_aba_clientes, text="Relatório Clientes")

janela.mainloop()

#blablablablublublu 