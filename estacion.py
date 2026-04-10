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

import tkinter as tk
from tkinter import ttk
from datetime import date

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

tk.Label(aba_movimentacao,text="Saída: ").grid(row=1, column=6, padx=5,sticky="e")
entrada_entrada = tk.Entry(aba_movimentacao)
entrada_entrada.grid(row=1, column=7, padx=5, sticky="e")

# Outras abas (apenas placeholders)
aba_financeiro = tk.Frame(abas)
abas.add(aba_financeiro, text="Financeiro")

aba_relatorio = tk.Frame(abas)
abas.add(aba_relatorio, text="Relatório")

janela.mainloop()

#blablablablublublu 