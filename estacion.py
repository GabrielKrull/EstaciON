import tkinter as tk
from tkinter import ttk, messagebox
from datetime import datetime, date
import re
import sqlite3
import random

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
    vaga    INTEGER DEFAULT NULL,
    FOREIGN KEY (placa) REFERENCES clientes(placa)
);
""")
conexao.commit()

TOTAL_VAGAS = 20  # Total de vagas do estacionamento

# Migração: garante que a coluna vaga existe em bancos antigos
try:
    cursor.execute("ALTER TABLE movimentacoes ADD COLUMN vaga INTEGER DEFAULT NULL")
    conexao.commit()
except Exception:
    pass  # Coluna já existe
conexao.commit()

janela = tk.Tk()
janela.title("estaciON")
janela.geometry("1280x720")
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

# --- FUNÇÕES DE VALIDAÇÃO ---

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

# --- ADICIONE JUNTO DAS FUNÇÕES ---

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

    # Detecta Mercosul (5º caractere é letra)
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

    # --- Ajuste inteligente do cursor ---
    nova_pos = pos_original

    # Se adicionou hífen
    if tem_hifen and pos_original == 4:
        nova_pos += 1

    # Se removeu hífen (Mercosul)
    if not tem_hifen and "-" in texto_original and pos_original > 3:
        nova_pos -= 1

    try:
        widget.icursor(nova_pos)
    except:
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

# --- FUNÇÕES DO SISTEMA ---

def salvar():
    nome  = entrada_nomeCliente.get().strip()
    cpf   = re.sub(r'\D', '', entrada_cpf.get())
    placa = limpar_placa(entrada_placaVeiculo.get())

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

    cursor.execute("INSERT INTO clientes (nome, cpf, placa) VALUES (?, ?, ?)", (nome, cpf, placa))
    conexao.commit()
    messagebox.showinfo("Sucesso", "Cliente registrado com sucesso")

    entrada_nomeCliente.delete(0, tk.END)
    entrada_cpf.delete(0, tk.END)
    entrada_placaVeiculo.delete(0, tk.END)


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
    placa = limpar_placa(entrada_placa_mov.get())
    data    = entrada_data.get().strip()
    hora_in = entrada_hora_in.get().strip()

    if not placa:
        messagebox.showwarning("Atenção", "Preencha a Placa.")
        return
    if not hora_in:
        messagebox.showwarning("Atenção", "Preencha o Horário de entrada.")
        return

    # Descobrir vagas ocupadas no momento
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
        messagebox.showinfo("Sucesso", f"Entrada registrada para {placa} às {hora_in}.\nVaga alocada: {vaga_escolhida}")
        limpar_movimentacao()
        carregar_movimentacoes()
        atualizar_mapa_vagas()
    except Exception as e:
        messagebox.showerror("Erro", str(e))


def registrar_saida():
    placa    = limpar_placa(entrada_placa_mov.get())
    hora_out = entrada_hora_out.get().strip()

    cursor.execute("""
    SELECT id, entrada FROM movimentacoes
    WHERE REPLACE(placa, '-', '') = ?
    AND saida IS NULL
    ORDER BY id DESC LIMIT 1
""", (placa,))
    
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
        atualizar_mapa_vagas()
    except Exception as e:
        messagebox.showerror("Erro", str(e))


# --- FUNÇÕES DE RELATÓRIO ---

def gerar_relatorio_clientes():
    for item in tabela_rel_clientes.get_children():
        tabela_rel_clientes.delete(item)
    cursor.execute("SELECT nome, cpf, placa FROM clientes ORDER BY nome")
    for cliente in cursor.fetchall():
        tabela_rel_clientes.insert("", "end", values=cliente)


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
            id_, nome, placa, data,
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
            id_, nome, placa, data,
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


def atualizar_mapa_vagas():
    """Atualiza as cores do mapa conforme vagas ocupadas no momento."""
    cursor.execute("SELECT vaga FROM movimentacoes WHERE saida IS NULL AND vaga IS NOT NULL")
    vagas_ocupadas = {row[0] for row in cursor.fetchall()}

    for num_vaga, cell in _vaga_canvas.items():
        cor = VERM if num_vaga in vagas_ocupadas else AZUL
        cell.configure(bg=cor)


# Chama ao trocar para a aba mapa
def ao_trocar_aba(event):
    aba_selecionada = abas.tab(abas.select(), "text").strip()
    if aba_selecionada == "Relatórios":
        gerar_relatorio_clientes()
        gerar_relatorio_recebimentos()
        gerar_relatorio_recebimentos_abertos()
        gerar_relatorio_top_clientes()
    elif aba_selecionada == "Mapa de vagas":
        atualizar_mapa_vagas()

# ===========================================================
# --- ABA CADASTRO DE CLIENTES ---
# ===========================================================
aba_cadastroCliente = tk.Frame(abas, bg=BG)
abas.add(aba_cadastroCliente, text="Clientes ")

tk.Label(aba_cadastroCliente, text="CADASTRO DE CLIENTES", font=FONTH, bg=BG, fg=AZUL).grid(row=0, column=0, columnspan=6, pady=20)

for i, texto in enumerate(["Nome:", "CPF:", "Placa:"]):
    tk.Label(aba_cadastroCliente, text=texto, font=FONTB, bg=BG, fg=BRAN).grid(row=1, column=i*2, padx=10, sticky="e")

entrada_nomeCliente  = tk.Entry(aba_cadastroCliente, bg=BG2, fg=BRAN, insertbackground=BRAN, borderwidth=0, font=FONT)
entrada_nomeCliente.grid(row=1, column=1, padx=5, pady=10, sticky="ew")

entrada_cpf = tk.Entry(aba_cadastroCliente, bg=BG2, fg=BRAN, insertbackground=BRAN, borderwidth=0, font=FONT)
entrada_cpf.grid(row=1, column=3, padx=5, pady=10, sticky="ew")

entrada_placaVeiculo = tk.Entry(aba_cadastroCliente, bg=BG2, fg=BRAN, insertbackground=BRAN, borderwidth=0, font=FONT)
entrada_placaVeiculo.bind("<KeyRelease>", mascara_placa)
entrada_placaVeiculo.grid(row=1, column=5, padx=5, pady=10, sticky="ew")

frame_botoes_cad = tk.Frame(aba_cadastroCliente, bg=BG)
frame_botoes_cad.grid(row=2, column=0, columnspan=9, pady=30)

tk.Button(frame_botoes_cad, text="Registrar cliente", command=salvar, bg=AZUL, fg=BRAN, font=FONTB,
          relief="flat", width=18, cursor="hand2", activebackground=AZUL2, activeforeground=BRAN).pack(side="left", padx=10)

aba_cadastroCliente.columnconfigure((1, 3, 5), weight=1)


# ===========================================================
# --- ABA MOVIMENTAÇÃO ---
# ===========================================================
aba_movimentacao = tk.Frame(abas, bg=BG)
abas.add(aba_movimentacao, text="Movimentação ")

tk.Label(aba_movimentacao, text="MOVIMENTAÇÃO DE VAGAS", font=FONTH, bg=BG, fg=AZUL).grid(row=0, column=0, columnspan=9, pady=(20, 10))

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
# --- ABA MAPA DE VAGAS ---
# ===========================================================
aba_mapa = tk.Frame(abas, bg=BG)
abas.add(aba_mapa, text="Mapa de vagas")

tk.Label(aba_mapa, text="MAPA DE VAGAS", font=FONTH, bg=BG, fg=AZUL).pack(pady=(18, 6))

# Legenda
frame_legenda = tk.Frame(aba_mapa, bg=BG)
frame_legenda.pack(pady=(0, 10))

tk.Canvas(frame_legenda, width=18, height=18, bg=AZUL, highlightthickness=0).pack(side="left", padx=(0, 4))
tk.Label(frame_legenda, text="Livre", font=FONT, bg=BG, fg=BRAN).pack(side="left", padx=(0, 18))
tk.Canvas(frame_legenda, width=18, height=18, bg=VERM, highlightthickness=0).pack(side="left", padx=(0, 4))
tk.Label(frame_legenda, text="Ocupada", font=FONT, bg=BG, fg=BRAN).pack(side="left")

# Frame para as seções de vagas
frame_secoes = tk.Frame(aba_mapa, bg=BG)
frame_secoes.pack(expand=True, fill="both", padx=30, pady=10)

VAGAS_POR_SECAO = 10
NUM_SECOES = TOTAL_VAGAS // VAGAS_POR_SECAO
COLS_POR_SECAO = 5   # 5 colunas × 2 linhas = 10 vagas por seção
CELL_W = 80
CELL_H = 64
PAD    = 10

# Dicionário: vaga_num -> canvas widget (para atualizar cor)
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
        row_grid = (i // COLS_POR_SECAO) + 1   # linha 1 ou 2
        col_grid =  i  % COLS_POR_SECAO

        cell = tk.Canvas(frame_sec, width=CELL_W, height=CELL_H,
                         bg=AZUL, highlightthickness=0, cursor="arrow")
        cell.grid(row=row_grid, column=col_grid, padx=PAD, pady=PAD)

        lbl = cell.create_text(CELL_W // 2, CELL_H // 2,
                               text=str(num_vaga),
                               font=("Arial", 14, "bold"),
                               fill=BRAN)

        _vaga_canvas[num_vaga] = cell
        _vaga_label[num_vaga]  = lbl

    for c in range(COLS_POR_SECAO):
        frame_sec.columnconfigure(c, weight=1)


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

tabela_rel_clientes = ttk.Treeview(sub_aba_clientes, columns=("Nome", "CPF", "Placa"), show="headings")
for col in ("Nome", "CPF", "Placa"):
    tabela_rel_clientes.heading(col, text=col)
    tabela_rel_clientes.column(col, width=200, anchor="center")
tabela_rel_clientes.pack(fill="both", expand=True, padx=15, pady=15)

# Sub-aba recebimentos
sub_aba_recebimentos = tk.Frame(sub_notebook)
sub_notebook.add(sub_aba_recebimentos, text="Recebimentos")

tabela_rel_recebimentos = ttk.Treeview(sub_aba_recebimentos,
    columns=("ID", "Cliente", "Placa", "Data", "Entrada", "Saída", "Valor"), show="headings")
colunas_recebimentos = {"ID": 50, "Cliente": 150, "Placa": 100, "Data": 110, "Entrada": 80, "Saída": 80, "Valor": 90}
for col in ("ID", "Cliente", "Placa", "Data", "Entrada", "Saída", "Valor"):
    tabela_rel_recebimentos.heading(col, text=col)
    tabela_rel_recebimentos.column(col, width=colunas_recebimentos[col], anchor="center")
tabela_rel_recebimentos.pack(fill="both", expand=True, padx=15, pady=15)

# Sub-aba recebimentos em aberto
sub_aba_recebimentos_aberto = tk.Frame(sub_notebook)
sub_notebook.add(sub_aba_recebimentos_aberto, text="Recebimentos em aberto")

tabela_rel_recebimentos_abertos = ttk.Treeview(sub_aba_recebimentos_aberto,
    columns=("ID", "Cliente", "Placa", "Data", "Entrada"), show="headings")
colunas_abertos = {"ID": 50, "Cliente": 150, "Placa": 100, "Data": 110, "Entrada": 80}
for col in ("ID", "Cliente", "Placa", "Data", "Entrada"):
    tabela_rel_recebimentos_abertos.heading(col, text=col)
    tabela_rel_recebimentos_abertos.column(col, width=colunas_abertos[col], anchor="center")
tabela_rel_recebimentos_abertos.pack(fill="both", expand=True, padx=15, pady=15)

# Sub-aba top 5 clientes
sub_aba_top = tk.Frame(sub_notebook)
sub_notebook.add(sub_aba_top, text="Top 5 Clientes")

tabela_rel_top_clientes = ttk.Treeview(sub_aba_top,
    columns=("Nome", "CPF", "Placa", "Visitas"), show="headings")
colunas_top = {"Nome": 150, "CPF": 100, "Placa": 100, "Visitas": 80}
for col in ("Nome", "CPF", "Placa", "Visitas"):
    tabela_rel_top_clientes.heading(col, text=col)
    tabela_rel_top_clientes.column(col, width=colunas_top[col], anchor="center")
tabela_rel_top_clientes.pack(fill="both", expand=True, padx=15, pady=15)

# --- Carrega os dados ao iniciar ---
abas.bind("<<NotebookTabChanged>>", ao_trocar_aba)

carregar_movimentacoes()
gerar_relatorio_clientes()
gerar_relatorio_recebimentos()
gerar_relatorio_recebimentos_abertos()
gerar_relatorio_top_clientes()
atualizar_mapa_vagas()

atualizar_hora()

janela.mainloop()