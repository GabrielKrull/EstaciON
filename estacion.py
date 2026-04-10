import tkinter as tk
from tkinter import ttk, messagebox

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

janela = tk.Tk()
janela.title("estaciON")

abas = ttk.Notebook(janela)
abas.pack(expand=True, fill="both")

# ABA CADASTRO DE CLIENTES 
aba_cadastroCliente = tk.Frame(abas)
abas.add(aba_cadastroCliente, text="Cadastro de Clientes")

tk.Label(aba_cadastroCliente, text="Cadastro de Clientes")

tk.Label(aba_cadastroCliente, text="Nome:").grid(row=1, column=0)
entrada_nomeCliente = tk.Entry(aba_cadastroCliente)
entrada_nomeCliente.grid(row=1, column=1)

tk.Label(aba_cadastroCliente, text="CPF:").grid(row=1, column=2)
entrada_cpf = tk.Entry(aba_cadastroCliente)
entrada_cpf.grid(row=1, column=3)

tk.Label(aba_cadastroCliente, text="Placa do veículo:").grid(row=1, column=4)
entrada_placaVeiculo = tk.Entry(aba_cadastroCliente)
entrada_placaVeiculo.grid(row=1, column=5)

aba_movimentacao = tk.Frame(abas)
abas.add(aba_movimentacao, text="Movimentação")

tk.Label(aba_movimentacao, text="Placa do veículo: ")
entrada_placaVeiculo = tk.Entry(aba_movimentacao)
entrada_placaVeiculo.grid(row=1, column=1)

aba_financeiro = tk.Frame(abas)
abas.add(aba_financeiro, text="Financeiro")

aba_relatorio = tk.Frame(abas)
abas.add(aba_relatorio, text="Recebimento em Aberto")

janela.mainloop()
#blablablablublublu 