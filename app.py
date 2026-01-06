from flask import Flask, render_template, request, redirect, url_for

app = Flask(__name__)
app.secret_key = "hospital_central_secret_key"



class Consulta:
    def __init__(self, horario, paciente, telefone):
        self.horario = horario
        self.paciente = paciente
        self.telefone = telefone
        self.esquerda = None
        self.direita = None
        self.altura = 1


class AgendaAVL:
    def get_altura(self, no):
        return no.altura if no else 0

    def get_balanco(self, no):
        return self.get_altura(no.esquerda) - self.get_altura(no.direita) if no else 0

    def rotar_direita(self, y):
        x = y.esquerda
        T2 = x.direita
        x.direita = y
        y.esquerda = T2
        y.altura = 1 + max(self.get_altura(y.esquerda), self.get_altura(y.direita))
        x.altura = 1 + max(self.get_altura(x.esquerda), self.get_altura(x.direita))
        return x

    def rotar_esquerda(self, x):
        y = x.direita
        T2 = y.esquerda
        y.esquerda = x
        x.direita = T2
        x.altura = 1 + max(self.get_altura(x.esquerda), self.get_altura(x.direita))
        y.altura = 1 + max(self.get_altura(y.esquerda), self.get_altura(y.direita))
        return y

    def inserir(self, raiz, horario, paciente, telefone):
        if not raiz:
            return Consulta(horario, paciente, telefone)

        if horario < raiz.horario:
            raiz.esquerda = self.inserir(raiz.esquerda, horario, paciente, telefone)
        elif horario > raiz.horario:
            raiz.direita = self.inserir(raiz.direita, horario, paciente, telefone)
        else:
            return raiz

        raiz.altura = 1 + max(self.get_altura(raiz.esquerda), self.get_altura(raiz.direita))
        b = self.get_balanco(raiz)

        if b > 1 and horario < raiz.esquerda.horario: return self.rotar_direita(raiz)
        if b < -1 and horario > raiz.direita.horario: return self.rotar_esquerda(raiz)
        if b > 1 and horario > raiz.esquerda.horario:
            raiz.esquerda = self.rotar_esquerda(raiz.esquerda)
            return self.rotar_direita(raiz)
        if b < -1 and horario < raiz.direita.horario:
            raiz.direita = self.rotar_direita(raiz.direita)
            return self.rotar_esquerda(raiz)
        return raiz

    def remover(self, raiz, horario):
        if not raiz: return raiz
        if horario < raiz.horario:
            raiz.esquerda = self.remover(raiz.esquerda, horario)
        elif horario > raiz.horario:
            raiz.direita = self.remover(raiz.direita, horario)
        else:
            if not raiz.esquerda:
                return raiz.direita
            elif not raiz.direita:
                return raiz.esquerda
            temp = self.get_min_node(raiz.direita)
            raiz.horario, raiz.paciente, raiz.telefone = temp.horario, temp.paciente, temp.telefone
            raiz.direita = self.remover(raiz.direita, temp.horario)

        if not raiz: return raiz
        raiz.altura = 1 + max(self.get_altura(raiz.esquerda), self.get_altura(raiz.direita))
        b = self.get_balanco(raiz)
        if b > 1 and self.get_balanco(raiz.esquerda) >= 0: return self.rotar_direita(raiz)
        if b < -1 and self.get_balanco(raiz.direita) <= 0: return self.rotar_esquerda(raiz)
        if b > 1 and self.get_balanco(raiz.esquerda) < 0:
            raiz.esquerda = self.rotar_esquerda(raiz.esquerda)
            return self.rotar_direita(raiz)
        if b < -1 and self.get_balanco(raiz.direita) > 0:
            raiz.direita = self.rotar_direita(raiz.direita)
            return self.rotar_esquerda(raiz)
        return raiz

    def get_min_node(self, no):
        atual = no
        while atual.esquerda: atual = atual.esquerda
        return atual

    def buscar(self, raiz, horario):
        if not raiz or raiz.horario == horario: return raiz
        if horario < raiz.horario: return self.buscar(raiz.esquerda, horario)
        return self.buscar(raiz.direita, horario)

    def para_lista(self, raiz, lista):
        if raiz:
            self.para_lista(raiz.esquerda, lista)
            lista.append({
                'horario': self.formatar_hora(raiz.horario),
                'raw': raiz.horario,
                'paciente': raiz.paciente,
                'telefone': raiz.telefone
            })
            self.para_lista(raiz.direita, lista)

    def formatar_hora(self, h):
        h_str = str(h).zfill(4)
        return f"{h_str[:2]}:{h_str[2:]}"



agenda = AgendaAVL()
raiz_global = None


@app.route('/')
def index():
    consultas = []
    agenda.para_lista(raiz_global, consultas)
    busca = request.args.get('busca')
    return render_template('index.html', consultas=consultas, busca=busca)


@app.route('/agendar', methods=['POST'])
def agendar():
    global raiz_global
    h = int(request.form['horario'].replace(":", ""))
    p = request.form['paciente']
    t = request.form['telefone']
    raiz_global = agenda.inserir(raiz_global, h, p, t)
    return redirect(url_for('index'))


@app.route('/cancelar/<int:horario>')
def cancelar(horario):
    global raiz_global
    raiz_global = agenda.remover(raiz_global, horario)
    return redirect(url_for('index'))


@app.route('/buscar', methods=['POST'])
def buscar():
    h_input = request.form['horario_busca']
    if not h_input: return redirect(url_for('index'))
    h = int(h_input.replace(":", ""))
    res = agenda.buscar(raiz_global, h)
    msg = f"🔍 Encontrado: {res.paciente} ({agenda.formatar_hora(h)})" if res else "❌ Horário livre."
    return redirect(url_for('index', busca=msg))


if __name__ == '__main__':
    app.run(debug=True)