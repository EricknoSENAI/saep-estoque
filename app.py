import hashlib
import os
from datetime import date
from functools import wraps

import mysql.connector
from flask import Flask, flash, redirect, render_template, request, session, url_for

app = Flask(__name__)
app.secret_key = os.getenv("SECRET_KEY", "troque-esta-chave")

DB = dict(
    host="127.0.0.1",
    port=3302,
    user="saep",
    password="saep123",
    database="saep_db",
)

def conectar():
    return mysql.connector.connect(**DB)


def consultar(sql, params=(), um=False):
    con = conectar()
    try:
        cur = con.cursor(dictionary=True)
        cur.execute(sql, params)
        dados = cur.fetchone() if um else cur.fetchall()
        return dados
    finally:
        con.close()


def executar(sql, params=()):
    con = conectar()
    try:
        cur = con.cursor()
        cur.execute(sql, params)
        con.commit()
    finally:
        con.close()


def login_obrigatorio(f):
    @wraps(f)
    def wrapper(*a, **kw):
        if "usuario_id" not in session:
            flash("Faça login para continuar.", "erro")
            return redirect(url_for("login"))
        return f(*a, **kw)
    return wrapper


def ordenar_por_nome(lista):
    """Insertion sort (ordem alfabética, sem diferenciar maiúsculas)."""
    for i in range(1, len(lista)):
        atual = lista[i]
        j = i - 1
        while j >= 0 and lista[j]["nome"].lower() > atual["nome"].lower():
            lista[j + 1] = lista[j]
            j -= 1
        lista[j + 1] = atual
    return lista


# ---------- Autenticação ----------
@app.route("/")
def index():
    return redirect(url_for("principal" if "usuario_id" in session else "login"))


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = request.form.get("email", "").strip()
        senha = request.form.get("senha", "")
        if not email or not senha:
            flash("Informe e-mail e senha.", "erro")
            return redirect(url_for("login"))
        u = consultar("SELECT * FROM usuarios WHERE email=%s", (email,), um=True)
        if not u:
            flash("Falha na autenticação: usuário não encontrado.", "erro")
            return redirect(url_for("login"))
        if u["senha"] != hashlib.sha256(senha.encode()).hexdigest():
            flash("Falha na autenticação: senha incorreta.", "erro")
            return redirect(url_for("login"))
        session["usuario_id"], session["usuario_nome"] = u["id"], u["nome"]
        return redirect(url_for("principal"))
    return render_template("login.html")


@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))


@app.route("/principal")
@login_obrigatorio
def principal():
    baixos = consultar(
        "SELECT nome, estoque_atual, estoque_minimo FROM produtos "
        "WHERE estoque_atual < estoque_minimo ORDER BY nome"
    )
    return render_template("principal.html", baixos=baixos)


# ---------- Cadastro de produto ----------
def validar_produto(f):
    erros, d = [], {}
    d["nome"] = f.get("nome", "").strip()
    d["marca"] = f.get("marca", "").strip()
    d["especificacoes"] = f.get("especificacoes", "").strip()
    d["voltagem"] = f.get("voltagem", "").strip() or None
    if not d["nome"]:
        erros.append("O nome é obrigatório.")
    if not d["marca"]:
        erros.append("A marca é obrigatória.")
    cat = f.get("categoria_id", "")
    if not cat.isdigit() or not consultar("SELECT id FROM categorias WHERE id=%s", (cat,), um=True):
        erros.append("Selecione uma categoria válida.")
    d["categoria_id"] = cat
    for campo, rotulo in (("garantia_meses", "Garantia"), ("estoque_minimo", "Estoque mínimo"),
                          ("estoque_atual", "Estoque atual")):
        v = f.get(campo, "").strip()
        if not v.isdigit():
            erros.append(f"{rotulo} deve ser um número inteiro maior ou igual a 0.")
        d[campo] = v
    return d, erros


@app.route("/produtos")
@login_obrigatorio
def produtos():
    busca = request.args.get("busca", "").strip()
    sql = ("SELECT p.*, c.nome AS categoria FROM produtos p "
           "JOIN categorias c ON c.id=p.categoria_id")
    params = ()
    if busca:
        sql += " WHERE p.nome LIKE %s OR p.marca LIKE %s OR c.nome LIKE %s"
        params = (f"%{busca}%",) * 3
    lista = consultar(sql + " ORDER BY p.nome", params)
    categorias = consultar("SELECT * FROM categorias ORDER BY nome")
    editar = request.args.get("editar")
    p = consultar("SELECT * FROM produtos WHERE id=%s", (editar,), um=True) if editar else None
    return render_template("produtos.html", lista=lista, categorias=categorias, busca=busca, p=p)


@app.route("/produtos/salvar", methods=["POST"])
@login_obrigatorio
def salvar_produto():
    pid = request.form.get("id")
    d, erros = validar_produto(request.form)
    if erros:
        for e in erros:
            flash(e, "erro")
        return redirect(url_for("produtos", editar=pid) if pid else url_for("produtos"))
    campos = (d["nome"], d["marca"], d["categoria_id"], d["especificacoes"], d["voltagem"],
              d["garantia_meses"], d["estoque_minimo"])
    if pid:
        executar("UPDATE produtos SET nome=%s, marca=%s, categoria_id=%s, especificacoes=%s, "
                 "voltagem=%s, garantia_meses=%s, estoque_minimo=%s WHERE id=%s", campos + (pid,))
        flash("Produto atualizado.", "ok")
    else:
        executar("INSERT INTO produtos (nome, marca, categoria_id, especificacoes, voltagem, "
                 "garantia_meses, estoque_minimo, estoque_atual) VALUES (%s,%s,%s,%s,%s,%s,%s,%s)",
                 campos + (d["estoque_atual"],))
        flash("Produto cadastrado.", "ok")
    return redirect(url_for("produtos"))


@app.route("/produtos/<int:pid>/excluir", methods=["POST"])
@login_obrigatorio
def excluir_produto(pid):
    try:
        executar("DELETE FROM produtos WHERE id=%s", (pid,))
        flash("Produto excluído.", "ok")
    except mysql.connector.IntegrityError:
        flash("Não é possível excluir: o produto possui movimentações no histórico.", "erro")
    return redirect(url_for("produtos"))


# ---------- Gestão de estoque ----------
@app.route("/estoque")
@login_obrigatorio
def estoque():
    lista = ordenar_por_nome(consultar("SELECT * FROM produtos"))
    hist = consultar(
        "SELECT m.*, p.nome AS produto, u.nome AS responsavel FROM movimentacoes m "
        "JOIN produtos p ON p.id=m.produto_id JOIN usuarios u ON u.id=m.usuario_id "
        "ORDER BY m.data_movimentacao DESC, m.id DESC LIMIT 30"
    )
    return render_template("estoque.html", lista=lista, hist=hist, hoje=date.today().isoformat())


@app.route("/estoque/movimentar", methods=["POST"])
@login_obrigatorio
def movimentar():
    pid, tipo = request.form.get("produto_id", ""), request.form.get("tipo", "")
    qtd, data = request.form.get("quantidade", ""), request.form.get("data", "")
    obs = request.form.get("observacao", "").strip() or None
    if not pid.isdigit() or tipo not in ("entrada", "saida") or not qtd.isdigit() \
            or int(qtd) <= 0 or not data:
        flash("Selecione o produto, o tipo, uma quantidade maior que 0 e a data.", "erro")
        return redirect(url_for("estoque"))
    try:
        date.fromisoformat(data)
    except ValueError:
        flash("Data inválida.", "erro")
        return redirect(url_for("estoque"))
    qtd = int(qtd)
    con = conectar()
    try:
        cur = con.cursor(dictionary=True)
        cur.execute("SELECT * FROM produtos WHERE id=%s FOR UPDATE", (pid,))
        p = cur.fetchone()
        if not p:
            flash("Produto não encontrado.", "erro")
            return redirect(url_for("estoque"))
        novo = p["estoque_atual"] + qtd if tipo == "entrada" else p["estoque_atual"] - qtd
        if novo < 0:
            flash(f"Saída maior que o estoque disponível ({p['estoque_atual']}).", "erro")
            con.rollback()
            return redirect(url_for("estoque"))
        cur.execute("UPDATE produtos SET estoque_atual=%s WHERE id=%s", (novo, pid))
        cur.execute("INSERT INTO movimentacoes (produto_id, usuario_id, tipo, quantidade, "
                    "data_movimentacao, observacao) VALUES (%s,%s,%s,%s,%s,%s)",
                    (pid, session["usuario_id"], tipo, qtd, data, obs))
        con.commit()
    finally:
        con.close()
    flash("Movimentação registrada.", "ok")
    if tipo == "saida" and novo < p["estoque_minimo"]:
        flash(f"ALERTA: '{p['nome']}' ficou com {novo} un., abaixo do mínimo de "
              f"{p['estoque_minimo']} un.", "alerta")
    return redirect(url_for("estoque"))


if __name__ == "__main__":
    app.run(debug=True)
