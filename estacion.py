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

TOTAL_VAGAS = 20

# Migração: garante que a coluna vaga existe em bancos antigos
try:
    cursor.execute("ALTER TABLE movimentacoes ADD COLUMN vaga INTEGER DEFAULT NULL")
    conexao.commit()
except Exception:
    pass  # Coluna já existe

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

abas = ttk.Notebook(janela)
abas.pack(expand=True, fill="both", padx=10, pady=10)

style.configure("Sub.TNotebook", background=BG, borderwidth=0)
style.configure("Sub.TNotebook.Tab", background=BG3, foreground=BRAN, padding=[10, 5], font=FONTB)
style.map("Sub.TNotebook.Tab", background=[("selected", AZUL)], foreground=[("selected", BRAN)])

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


# ===========================================================
# --- FUNÇÕES DO SISTEMA ---
# ===========================================================

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
    placa  = limpar_placa(str(item["values"][2]))

    if not messagebox.askyesno("Confirmar exclusão",
                               f"Deseja excluir o cliente '{nome}'?\n\nCPF: {item['values'][1]}\nPlaca: {item['values'][2]}\n\nAs movimentações vinculadas serão mantidas."):
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
    cursor.execute("SELECT nome, cpf, placa FROM clientes ORDER BY nome")
    for row in cursor.fetchall():
        nome, cpf, placa = row
        cpf_fmt = f"{cpf[:3]}.{cpf[3:6]}.{cpf[6:9]}-{cpf[9:]}" if len(cpf) == 11 else cpf
        tabela_clientes_cad.insert("", "end", values=(nome, cpf_fmt, formatar_placa_exibicao(placa)))


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

    # ← Verifica se a placa pertence a um cliente cadastrado
    cursor.execute("SELECT nome FROM clientes WHERE UPPER(placa) = UPPER(?)", (placa,))
    cliente = cursor.fetchone()
    if not cliente:
        messagebox.showerror("Erro", f"A placa {formatar_placa_exibicao(placa)} não está vinculada a nenhum cliente cadastrado.\n\nCadastre o cliente antes de registrar a entrada.")
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
        messagebox.showinfo("Sucesso", f"Entrada registrada para {formatar_placa_exibicao(placa)} ({cliente[0]}) às {hora_in}.\nVaga alocada: {vaga_escolhida}")
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

# ===========================================================
# --- FUNÇÕES DA SUB-ABA CLIENTES REGISTRADOS ---
# ===========================================================

def carregar_cards_clientes():
    for widget in frame_cards_inner.winfo_children():
        widget.destroy()

    cursor.execute("SELECT id, nome, cpf, placa FROM clientes ORDER BY nome")
    clientes = cursor.fetchall()

    if not clientes:
        tk.Label(frame_cards_inner, text="Nenhum cliente cadastrado.",
                 font=FONT, bg=BG, fg=CINZA).pack(pady=40)
        return

    for idx, (cid, nome, cpf, placa) in enumerate(clientes):
        cpf_fmt   = f"{cpf[:3]}.{cpf[3:6]}.{cpf[6:9]}-{cpf[9:]}" if len(cpf) == 11 else cpf
        placa_fmt = formatar_placa_exibicao(placa)
        _criar_card(frame_cards_inner, cid, nome, cpf_fmt, placa_fmt)

    frame_cards_inner.update_idletasks()
    canvas_cards.configure(scrollregion=canvas_cards.bbox("all"))


def _criar_card(parent, cid, nome, cpf_fmt, placa_fmt):
    card = tk.Frame(parent, bg=BG2, bd=0, relief="flat",
                    highlightbackground=AZUL, highlightthickness=1)
    card.pack(fill="x", padx=20, pady=6)

    # Coluna de ícone/inicial
    frame_icon = tk.Frame(card, bg=AZUL, width=54)
    frame_icon.pack(side="left", fill="y")
    frame_icon.pack_propagate(False)
    inicial = nome[0].upper() if nome else "?"
    tk.Label(frame_icon, text=inicial, font=("Arial", 18, "bold"),
             bg=AZUL, fg=BRAN).place(relx=0.5, rely=0.5, anchor="center")

    # Coluna de dados
    frame_dados = tk.Frame(card, bg=BG2)
    frame_dados.pack(side="left", fill="both", expand=True, padx=14, pady=10)

    tk.Label(frame_dados, text=nome, font=FONTB, bg=BG2, fg=BRAN,
             anchor="w").grid(row=0, column=0, columnspan=4, sticky="w")

    tk.Label(frame_dados, text="CPF:", font=FONT, bg=BG2, fg=CINZA).grid(row=1, column=0, sticky="w", pady=(4,0))
    tk.Label(frame_dados, text=cpf_fmt, font=FONT, bg=BG2, fg=BRAN).grid(row=1, column=1, sticky="w", padx=(4,20), pady=(4,0))

    tk.Label(frame_dados, text="Placa:", font=FONT, bg=BG2, fg=CINZA).grid(row=1, column=2, sticky="w", pady=(4,0))
    tk.Label(frame_dados, text=placa_fmt, font=FONT, bg=BG2, fg=BRAN).grid(row=1, column=3, sticky="w", padx=(4,0), pady=(4,0))

    # Botões
    frame_btns = tk.Frame(card, bg=BG2)
    frame_btns.pack(side="right", padx=12, pady=10)

    tk.Button(frame_btns, text="✏  Editar",
              bg=AZUL, fg=BRAN, font=FONTB, relief="flat", cursor="hand2",
              activebackground=AZUL2, activeforeground=BRAN, padx=10, pady=4,
              command=lambda i=cid, n=nome, c=cpf_fmt, p=placa_fmt: abrir_modal_edicao(i, n, c, p)
              ).pack(side="left", padx=(0, 6))

    tk.Button(frame_btns, text="🗑  Excluir",
              bg=VERM, fg=BRAN, font=FONTB, relief="flat", cursor="hand2",
              activebackground="#E53935", activeforeground=BRAN, padx=10, pady=4,
              command=lambda i=cid, n=nome: excluir_cliente_card(i, n)
              ).pack(side="left")


def excluir_cliente_card(cid, nome):
    if not messagebox.askyesno("Confirmar exclusão",
                               f"Deseja excluir o cliente '{nome}'?\n\nAs movimentações vinculadas serão mantidas."):
        return
    try:
        cursor.execute("DELETE FROM clientes WHERE id = ?", (cid,))
        conexao.commit()
        messagebox.showinfo("Sucesso", f"Cliente '{nome}' excluído com sucesso.")
        carregar_cards_clientes()
        carregar_tabela_clientes_cad()
    except Exception as e:
        messagebox.showerror("Erro", str(e))


def abrir_modal_edicao(cid, nome, cpf_fmt, placa_fmt):
    modal = tk.Toplevel(janela)
    modal.title("Editar Cliente")
    modal.configure(bg=BG)
    modal.resizable(False, False)
    modal.grab_set()

    w, h = 420, 280
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

    frame_form.columnconfigure(1, weight=1)

    def salvar_edicao():
        novo_nome  = entries["Nome"].get().strip()
        novo_cpf   = re.sub(r'\D', '', entries["CPF"].get())
        nova_placa = limpar_placa(entries["Placa"].get())

        if not novo_nome:
            messagebox.showerror("Erro", "Nome não pode ser vazio.", parent=modal)
            return
        if not validar_cpf(novo_cpf):
            messagebox.showerror("Erro", "CPF inválido.", parent=modal)
            return
        if not validar_placa(nova_placa):
            messagebox.showerror("Erro", "Placa inválida.", parent=modal)
            return

        # Verifica se CPF já existe em outro cliente
        cursor.execute("SELECT id FROM clientes WHERE cpf = ? AND id != ?", (novo_cpf, cid))
        if cursor.fetchone():
            messagebox.showerror("Erro", "Este CPF já está cadastrado em outro cliente.", parent=modal)
            return

        try:
            cursor.execute(
                "UPDATE clientes SET nome=?, cpf=?, placa=? WHERE id=?",
                (novo_nome, novo_cpf, nova_placa, cid)
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


def pesquisar_clientes_cadastrados(termo):
    for widget in frame_cards_inner.winfo_children():
        widget.destroy()

    cursor.execute("SELECT id, nome, cpf, placa FROM clientes ORDER BY nome")
    clientes = cursor.fetchall()
    termo = termo.lower().strip()

    encontrados = []
    for cid, nome, cpf, placa in clientes:
        cpf_fmt   = f"{cpf[:3]}.{cpf[3:6]}.{cpf[6:9]}-{cpf[9:]}" if len(cpf) == 11 else cpf
        placa_fmt = formatar_placa_exibicao(placa)
        if termo in nome.lower() or termo in cpf_fmt or termo in placa_fmt.lower():
            encontrados.append((cid, nome, cpf_fmt, placa_fmt))

    if not encontrados:
        tk.Label(frame_cards_inner, text="Nenhum cliente encontrado.",
                 font=FONT, bg=BG, fg=CINZA).pack(pady=40)
    else:
        for cid, nome, cpf_fmt, placa_fmt in encontrados:
            _criar_card(frame_cards_inner, cid, nome, cpf_fmt, placa_fmt)

    frame_cards_inner.update_idletasks()
    canvas_cards.configure(scrollregion=canvas_cards.bbox("all"))


def pesquisar_rel_clientes(termo):
    for item in tabela_rel_clientes.get_children():
        tabela_rel_clientes.delete(item)
    cursor.execute("SELECT nome, cpf, placa FROM clientes ORDER BY nome")
    termo = termo.lower().strip()
    for nome, cpf, placa in cursor.fetchall():
        cpf_fmt = f"{cpf[:3]}.{cpf[3:6]}.{cpf[6:9]}-{cpf[9:]}" if len(cpf) == 11 else cpf
        if termo in nome.lower() or termo in cpf_fmt or termo in formatar_placa_exibicao(placa).lower():
            tabela_rel_clientes.insert("", "end", values=(nome, cpf_fmt, formatar_placa_exibicao(placa)))


def pesquisar_rel_recebimentos(termo):
    for item in tabela_rel_recebimentos.get_children():
        tabela_rel_recebimentos.delete(item)
    cursor.execute("""
        SELECT m.id, COALESCE(c.nome, '—'), m.placa, m.data, m.entrada, m.saida, m.valor
        FROM movimentacoes m
        LEFT JOIN clientes c ON UPPER(m.placa) = UPPER(c.placa)
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
        FROM movimentacoes m
        LEFT JOIN clientes c ON UPPER(m.placa) = UPPER(c.placa)
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
        FROM clientes c
        LEFT JOIN movimentacoes m ON UPPER(c.placa) = UPPER(m.placa)
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

    if aba_selecionada == "Clientes":          # ← adicione este bloco
        carregar_cards_clientes()
    elif aba_selecionada == "Relatórios":
        gerar_relatorio_clientes()
        gerar_relatorio_recebimentos()
        gerar_relatorio_recebimentos_abertos()
        gerar_relatorio_top_clientes()
    elif aba_selecionada == "Mapa de vagas":
        atualizar_mapa_vagas()


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
                     insertbackground=BRAN, borderwidth=0, font=FONT,
                     relief="flat")
    entry.pack(side="left", fill="x", expand=True, pady=6, padx=(0, 10))

    var.trace_add("write", lambda *_: comando_pesquisa(var.get()))
    return var


# ===========================================================
# --- FUNÇÕES DE EXPORTAÇÃO PDF ---
# ===========================================================

def _estilos_pdf():
    styles = getSampleStyleSheet()
    titulo_style = ParagraphStyle(
        'TituloEstaciON',
        parent=styles['Title'],
        fontSize=16,
        textColor=colors.HexColor("#1565C0"),
        spaceAfter=4,
        alignment=TA_CENTER,
    )
    sub_style = ParagraphStyle(
        'SubTituloEstaciON',
        parent=styles['Normal'],
        fontSize=9,
        textColor=colors.grey,
        spaceAfter=14,
        alignment=TA_CENTER,
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
        messagebox.showinfo(
            "PDF Gerado",
            f"Relatório '{titulo_relatorio}' exportado com sucesso!\n\nArquivo: {doc.filename}"
        )
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
    doc = SimpleDocTemplate(caminho, pagesize=A4,
                            leftMargin=2*cm, rightMargin=2*cm,
                            topMargin=2*cm, bottomMargin=2*cm)
    story = []
    story.append(Paragraph("estaciON", titulo_style))
    story.append(Paragraph(
        f"Relatório de Clientes  •  Gerado em {datetime.now().strftime('%d/%m/%Y %H:%M')}",
        sub_style
    ))

    cursor.execute("SELECT nome, cpf, placa FROM clientes ORDER BY nome")
    rows = cursor.fetchall()

    if not rows:
        story.append(Paragraph("Nenhum cliente cadastrado.", getSampleStyleSheet()['Normal']))
    else:
        dados = [["Nome", "CPF", "Placa"]]
        for nome, cpf, placa in rows:
            cpf_fmt = f"{cpf[:3]}.{cpf[3:6]}.{cpf[6:9]}-{cpf[9:]}" if len(cpf) == 11 else cpf
            dados.append([nome, cpf_fmt, formatar_placa_exibicao(placa)])

        tabela = Table(dados, colWidths=[8*cm, 5*cm, 4*cm], repeatRows=1)
        tabela.setStyle(_estilo_tabela_pdf(3))
        story.append(tabela)
        story.append(Spacer(1, 0.5*cm))
        story.append(Paragraph(
            f"Total de clientes: {len(rows)}",
            ParagraphStyle('rodape', fontSize=9, textColor=colors.grey, alignment=TA_CENTER)
        ))

    _salvar_pdf(doc, story, "Relatório Clientes")


def exportar_pdf_recebimentos():
    caminho = _pedir_caminho(f"relatorio_recebimentos_{date.today()}.pdf")
    if not caminho:
        return

    titulo_style, sub_style = _estilos_pdf()
    doc = SimpleDocTemplate(caminho, pagesize=landscape(A4),
                            leftMargin=2*cm, rightMargin=2*cm,
                            topMargin=2*cm, bottomMargin=2*cm)
    story = []
    story.append(Paragraph("estaciON", titulo_style))
    story.append(Paragraph(
        f"Relatório de Recebimentos  •  Gerado em {datetime.now().strftime('%d/%m/%Y %H:%M')}",
        sub_style
    ))

    cursor.execute("""
        SELECT m.id, COALESCE(c.nome, '—'), m.placa, m.data, m.entrada, m.saida, m.valor
        FROM movimentacoes m
        LEFT JOIN clientes c ON UPPER(m.placa) = UPPER(c.placa)
        WHERE m.pago = 1
        ORDER BY m.data DESC
    """)
    rows = cursor.fetchall()

    if not rows:
        story.append(Paragraph("Nenhum recebimento encontrado.", getSampleStyleSheet()['Normal']))
    else:
        dados = [["ID", "Cliente", "Placa", "Data", "Entrada", "Saída", "Valor"]]
        total = 0.0
        for id_, nome, placa, data, entrada, saida, valor in rows:
            total += valor or 0
            dados.append([
                str(id_), nome, formatar_placa_exibicao(placa), data,
                entrada or "—", saida or "—",
                f"R$ {valor:.2f}" if valor else "—"
            ])
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
    doc = SimpleDocTemplate(caminho, pagesize=A4,
                            leftMargin=2*cm, rightMargin=2*cm,
                            topMargin=2*cm, bottomMargin=2*cm)
    story = []
    story.append(Paragraph("estaciON", titulo_style))
    story.append(Paragraph(
        f"Recebimentos em Aberto  •  Gerado em {datetime.now().strftime('%d/%m/%Y %H:%M')}",
        sub_style
    ))

    cursor.execute("""
        SELECT m.id, COALESCE(c.nome, 'Cliente não cadastrado'), m.placa, m.data, m.entrada
        FROM movimentacoes m
        LEFT JOIN clientes c ON UPPER(m.placa) = UPPER(c.placa)
        WHERE m.pago = 0
        ORDER BY m.data DESC
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
        story.append(Paragraph(
            f"Total em aberto: {len(rows)} registro(s)",
            ParagraphStyle('rodape', fontSize=9, textColor=colors.HexColor("#C62828"), alignment=TA_CENTER)
        ))

    _salvar_pdf(doc, story, "Recebimentos em Aberto")


def exportar_pdf_top_clientes():
    caminho = _pedir_caminho(f"relatorio_top_clientes_{date.today()}.pdf")
    if not caminho:
        return

    titulo_style, sub_style = _estilos_pdf()
    doc = SimpleDocTemplate(caminho, pagesize=A4,
                            leftMargin=2*cm, rightMargin=2*cm,
                            topMargin=2*cm, bottomMargin=2*cm)
    story = []
    story.append(Paragraph("estaciON", titulo_style))
    story.append(Paragraph(
        f"Top 5 Clientes  •  Gerado em {datetime.now().strftime('%d/%m/%Y %H:%M')}",
        sub_style
    ))

    cursor.execute("""
        SELECT c.nome, c.cpf, c.placa, COUNT(m.id) AS total_visitas
        FROM clientes c
        LEFT JOIN movimentacoes m ON UPPER(c.placa) = UPPER(m.placa)
        GROUP BY c.id
        ORDER BY total_visitas DESC
        LIMIT 5
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
            ts.add('BACKGROUND', (0, 1), (-1, 1), colors.HexColor("#FFF8E1"))
            ts.add('FONTNAME',   (0, 1), (-1, 1), 'Helvetica-Bold')
        tabela.setStyle(ts)
        story.append(tabela)

    _salvar_pdf(doc, story, "Top 5 Clientes")


# ===========================================================
# --- ABA DE CLIENTES ---
# ===========================================================
aba_clientes_principal = tk.Frame(abas, bg=BG)
abas.add(aba_clientes_principal, text="Clientes ")

style.configure("Sub.TNotebook", background=BG, borderwidth=0)
style.configure("Sub.TNotebook.Tab", background=BG3, foreground=BRAN, padding=[10, 5], font=FONTB)
style.map("Sub.TNotebook.Tab", background=[("selected", AZUL)], foreground=[("selected", BRAN)])
style.layout("Sub.TNotebook", [("Sub.TNotebook.client", {"sticky": "nswe"})])

sub_notebook_clientes = ttk.Notebook(aba_clientes_principal, style="Sub.TNotebook")
sub_notebook_clientes.pack(expand=True, fill="both", padx=0, pady=10)


#--- Sub-aba cadastro de clientes ---
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

frame_botoes_cad = tk.Frame(aba_cadastroCliente, bg=BG)
frame_botoes_cad.grid(row=2, column=0, columnspan=9, pady=(10, 6))

tk.Button(frame_botoes_cad, text="Registrar cliente", command=salvar, bg=AZUL, fg=BRAN, font=FONTB,
          relief="flat", width=18, cursor="hand2", activebackground=AZUL2, activeforeground=BRAN).pack(side="left", padx=10)

# Tabela de clientes cadastrados
frame_tabela_cad = tk.Frame(aba_cadastroCliente, bg=BG)
frame_tabela_cad.grid(row=3, column=0, columnspan=9, sticky="nsew", padx=15, pady=(10, 15))
aba_cadastroCliente.rowconfigure(3, weight=1)

tabela_clientes_cad = ttk.Treeview(frame_tabela_cad,
    columns=("Nome", "CPF", "Placa"), show="headings", selectmode="browse")
for col, w in [("Nome", 250), ("CPF", 160), ("Placa", 120)]:
    tabela_clientes_cad.heading(col, text=col)
    tabela_clientes_cad.column(col, width=w, anchor="center", minwidth=60)

scrollbar_cad = ttk.Scrollbar(frame_tabela_cad, orient="vertical", command=tabela_clientes_cad.yview)
tabela_clientes_cad.configure(yscrollcommand=scrollbar_cad.set)
tabela_clientes_cad.pack(side="left", fill="both", expand=True)
scrollbar_cad.pack(side="right", fill="y")

aba_cadastroCliente.columnconfigure((1, 3, 5), weight=1)

# --- Sub-aba Clientes Cadastrados ---

'''scrollbar_cards = ttk.Scrollbar(aba_clientes_lista, orient="vertical", command=canvas_cards.yview)
canvas_cards.configure(yscrollcommand=scrollbar_cards.set)

scrollbar_cards.pack(side="right", fill="y")
canvas_cards.pack(side="left", fill="both", expand=True)

frame_cards_inner = tk.Frame(canvas_cards, bg=BG)
canvas_cards.create_window((0, 0), window=frame_cards_inner, anchor="nw") '''

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

def _on_resize_cards(event):
    canvas_cards.itemconfig(1, width=event.width)
canvas_cards.bind("<Configure>", _on_resize_cards)

def _scroll_mouse(event):
    canvas_cards.yview_scroll(int(-1 * (event.delta / 120)), "units")
canvas_cards.bind_all("<MouseWheel>", _scroll_mouse)

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

sub_notebook = ttk.Notebook(aba_relatorio, style="Sub.TNotebook")
sub_notebook.pack(expand=True, fill="both", padx=10, pady=10)

# --- Sub-aba Relatório Clientes ---
sub_aba_clientes = tk.Frame(sub_notebook, bg=BG)
sub_notebook.add(sub_aba_clientes, text="Relatório Clientes")

criar_barra_pesquisa(sub_aba_clientes, pesquisar_rel_clientes)

frame_tree_rel_cli = tk.Frame(sub_aba_clientes, bg=BG)
frame_tree_rel_cli.pack(fill="both", expand=True, padx=15, pady=(4, 4))

tabela_rel_clientes = ttk.Treeview(frame_tree_rel_cli, columns=("Nome", "CPF", "Placa"), show="headings")
for col in ("Nome", "CPF", "Placa"):
    tabela_rel_clientes.heading(col, text=col)
    tabela_rel_clientes.column(col, width=200, anchor="center")
scroll_rel_cli = ttk.Scrollbar(frame_tree_rel_cli, orient="vertical", command=tabela_rel_clientes.yview)
tabela_rel_clientes.configure(yscrollcommand=scroll_rel_cli.set)
tabela_rel_clientes.pack(side="left", fill="both", expand=True)
scroll_rel_cli.pack(side="right", fill="y")

tk.Button(sub_aba_clientes, text="⬇  Exportar PDF", command=exportar_pdf_clientes,
          bg= AZUL2, fg=BRAN, font=FONTB, relief="flat", cursor="hand2",
          activebackground=AZUL2, activeforeground=BRAN, padx=16, pady=6
          ).pack(pady=(4, 12))

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
          activebackground=AZUL2, activeforeground=BRAN, padx=16, pady=6
          ).pack(pady=(4, 12))

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
          bg= AZUL2, fg=BRAN, font=FONTB, relief="flat", cursor="hand2",
          activebackground=AZUL2, activeforeground=BRAN, padx=16, pady=6
          ).pack(pady=(4, 12))

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
          activebackground=AZUL2, activeforeground=BRAN, padx=16, pady=6
          ).pack(pady=(4, 12))

# --- Inicialização ---
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

janela.mainloop()