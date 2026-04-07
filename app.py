import os
import pymysql
from datetime import date, datetime
from io import BytesIO

from flask import Flask, render_template, make_response, url_for, request, redirect, flash
from flask_sqlalchemy import SQLAlchemy
from flask_admin import Admin
from flask_admin.contrib.sqla import ModelView
from markupsafe import Markup
from xhtml2pdf import pisa
from sqlalchemy import func, CheckConstraint
from werkzeug.utils import secure_filename


from wtforms import DateField, DateTimeField, DecimalField, StringField
from wtforms.validators import DataRequired, Length, Regexp, NumberRange

pymysql.install_as_MySQLdb()

base_dir = os.path.abspath(os.path.dirname(__file__))
app = Flask(__name__)

app.config['UPLOAD_FOLDER'] = os.path.join(base_dir, 'static', 'uploads')
app.config['SECRET_KEY'] = 'ms_enterprise_angola_2026'
app.config['SQLALCHEMY_DATABASE_URI'] = 'mysql+pymysql://root:@localhost/workshopbd'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)

sessao_orador = db.Table('sessao_orador',
                         db.Column('id_sessao', db.Integer, db.ForeignKey('sessao.id_sessao'), primary_key=True),
                         db.Column('id_orador', db.Integer, db.ForeignKey('orador.id_orador'), primary_key=True)
                         )


class Evento(db.Model):
    __tablename__ = 'Evento'
    id_Evento = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(100), nullable=False)
    moderador = db.Column(db.String(100), nullable=False)
    datainicio = db.Column(db.DateTime)
    datafim = db.Column(db.DateTime)
    localevento = db.Column(db.String(100), nullable=False, default='Angola')
    capacidade = db.Column(db.Integer)
    # AJUSTE: Preço >= 0 e Data Fim > Data Início no BD
    precoinscricao = db.Column(db.Numeric(10, 2), CheckConstraint('precoinscricao >= 0'), default=0.00)

    __table_args__ = (
        CheckConstraint('datafim > datainicio', name='check_datas_evento'),
    )

    def __repr__(self): return self.nome


class Participante(db.Model):
    __tablename__ = 'Participante'
    id_participante = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(100), unique=True)
    # AJUSTE: Constraint de telefone para garantir formato exato no BD
    telefone = db.Column(db.String(20), CheckConstraint("telefone REGEXP '^\\\\+244 [0-9]{9}$'"))
    datanasc = db.Column(db.Date)
    genero = db.Column(db.Enum('M', 'F'))
    instituicao = db.Column(db.String(100))
    curso = db.Column(db.String(100))

    def __repr__(self): return self.nome


class Orador(db.Model):
    __tablename__ = 'orador'
    id_orador = db.Column(db.Integer, primary_key=True, autoincrement=True)
    nome = db.Column(db.String(100), nullable=False)
    datanasc = db.Column(db.Date)
    genero = db.Column(db.Enum('M', 'F'))
    # AJUSTE: Validação de telefone
    telefone = db.Column(db.String(20), unique=True, nullable=False)
    email = db.Column(db.String(100), nullable=False, unique=True)
    endereco = db.Column(db.String(100))
    especialidade = db.Column(db.String(100))
    bio = db.Column(db.Text, nullable=False)


class Sessao(db.Model):
    __tablename__ = 'sessao'
    id_sessao = db.Column(db.Integer, primary_key=True)
    descricao = db.Column(db.String(100))
    datahora = db.Column(db.DateTime)
    sala = db.Column(db.String(100))
    id_Evento = db.Column(db.Integer, db.ForeignKey('Evento.id_Evento'))
    oradores = db.relationship('Orador', secondary=sessao_orador, backref='sessoes')


class Inscricao(db.Model):
    __tablename__ = 'inscricao'
    id_inscricao = db.Column(db.Integer, primary_key=True)
    comprovativo = db.Column(db.String(200), nullable=True)
    id_Evento = db.Column(db.Integer, db.ForeignKey('Evento.id_Evento'))
    id_participante = db.Column(db.Integer, db.ForeignKey('Participante.id_participante'))
    datainscricao = db.Column(db.Date, default=db.func.current_date())
    tipo_inscricao = db.Column(db.Enum('Gratuita', 'Paga'), nullable=False)
    status_pagamento = db.Column(db.Enum('Pendente', 'Confirmado', 'Cancelado', 'Isento'), default='Pendente')
    # AJUSTE: Valor pago >= 0
    valor_pago = db.Column(db.Numeric(10, 2), CheckConstraint('valor_pago >= 0'), default=0.00)
    participante_rel = db.relationship('Participante', backref='inscricoes_rel')



@app.route('/')
def home():
    eventos = Evento.query.all()
    return render_template('index.html', eventos=eventos)


@app.route('/evento/<int:evento_id>/inscrever', methods=['GET', 'POST'])
def inscrever_publico(evento_id):
    evento = Evento.query.get_or_404(evento_id)
    if request.method == 'POST':
        try:
            digitos = request.form.get('telefone_digitos', '')
            if len(digitos) != 9:
                flash("O telefone deve ter exatamente 9 dígitos!", "danger")
                return render_template('inscricao.html', evento=evento)

            novo_p = Participante(
                nome=request.form.get('nome'),
                datanasc=request.form.get('datanasc'),
                email=request.form.get('email'),
                telefone=f"+244 {digitos}",
                genero=request.form.get('genero'),
                instituicao=request.form.get('instituicao'),
                curso=request.form.get('curso')
            )
            db.session.add(novo_p)
            db.session.flush()

            tipo_def = 'Gratuita' if evento.precoinscricao == 0 else 'Paga'
            nova_i = Inscricao(
                id_Evento=evento.id_Evento,
                id_participante=novo_p.id_participante,
                datainscricao=date.today(),
                tipo_inscricao=tipo_def,
                status_pagamento='Isento' if tipo_def == 'Gratuita' else 'Pendente',
                valor_pago=0.00
            )
            db.session.add(nova_i)
            db.session.commit()

            if evento.precoinscricao > 0:
                return redirect(url_for('exibir_pagamento',
                                        participante_id=novo_p.id_participante,
                                        evento_id=evento.id_Evento))
            else:

                flash("Inscrição gratuita confirmada!", "success")
                return redirect(url_for('home'))
        except Exception as e:
            db.session.rollback()
            return f"Erro: {str(e)}"
    return render_template('inscricao.html', evento=evento)


@app.route('/imprimir_relatorio/<int:evento_id>')
def imprimir_relatorio(evento_id):
    evento = Evento.query.get_or_404(evento_id)
    sessoes = Sessao.query.filter_by(id_Evento=evento_id).all()
    inscricoes = Inscricao.query.filter_by(id_Evento=evento_id).all()
    total_pago = db.session.query(func.sum(Inscricao.valor_pago)).filter(Inscricao.id_Evento == evento_id).scalar() or 0

    html = render_template('relatorio.html',
                           evento=evento,
                           sessoes=sessoes,
                           inscricoes=inscricoes,
                           total_pago=total_pago,
                           data_atual=datetime.now().strftime('%d/%m/%Y %H:%M'))

    pdf_out = BytesIO()
    pisa.CreatePDF(html, dest=pdf_out)
    response = make_response(pdf_out.getvalue())
    response.headers['Content-Type'] = 'application/pdf'
    response.headers['Content-Disposition'] = f'inline; filename=relatorio_{evento_id}.pdf'
    return response


@app.route('/pagamento/<int:participante_id>/<int:evento_id>')
def exibir_pagamento(participante_id, evento_id):
    participante = Participante.query.get_or_404(participante_id)
    evento = Evento.query.get_or_404(evento_id)
    return render_template('pagamento.html', participante=participante, evento=evento)


@app.route('/enviar_comprovativo/<int:id_participante>', methods=['POST'])
def enviar_comprovativo(id_participante):
    if 'foto' not in request.files:
        flash("Nenhum ficheiro selecionado", "danger")
        return redirect(request.url)

    file = request.files['foto']
    if file.filename == '':
        flash("Nenhum ficheiro selecionado", "danger")
        return redirect(request.url)

    if file:
        filename = secure_filename(file.filename)

        filename = f"{id_participante}_{datetime.now().strftime('%Y%m%d%H%M%S')}_{filename}"

        file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))

        inscricao = Inscricao.query.filter_by(id_participante=id_participante).first()
        if inscricao:
            inscricao.comprovativo = filename
            # O Admin depois altera o status de Pendente para Confirmado manualmente
            db.session.commit()
            flash("Comprovativo enviado! Aguarde a validação do Admin.", "success")

        return redirect(url_for('home'))



class MasterAdmin(ModelView):
    column_display_pk = True
    form_overrides = {
        'datanasc': DateField,
        'datainscricao': DateField,
        'datahora': DateTimeField,
        'valor_pago': DecimalField
    }
    form_args = {
        'datanasc': {'format': '%Y-%m-%d'},
        'datainscricao': {'format': '%Y-%m-%d'},
        'datahora': {'format': '%Y-%m-%dT%H:%M'},
        'valor_pago': {'validators': [NumberRange(min=0)]},
        'telefone': {
            'validators': [DataRequired(), Regexp(r'^\+244\s\d{9}$', message="Use o formato +244 9XXXXXXXX")],
            'render_kw': {"placeholder": "+244 9XXXXXXXX"}
        }
    }
    form_widget_args = {
        'datanasc': {'type': 'date'},
        'datainscricao': {'type': 'date'},
        'datahora': {'type': 'datetime-local'}
    }


class EventoAdmin(MasterAdmin):
    column_list = ('id_Evento', 'nome', 'moderador', 'datainicio', 'datafim', 'localevento', 'capacidade',
                   'precoinscricao', 'relatorio')
    form_overrides = {
        'datainicio': DateTimeField,
        'datafim': DateTimeField,
        'precoinscricao': DecimalField
    }
    form_args = {
        'datainicio': {'format': '%Y-%m-%dT%H:%M', 'validators': [DataRequired()]},
        'datafim': {'format': '%Y-%m-%dT%H:%M', 'validators': [DataRequired()]},
        'precoinscricao': {'validators': [NumberRange(min=0)]}
    }
    form_widget_args = {
        'datainicio': {'type': 'datetime-local'},
        'datafim': {'type': 'datetime-local'}
    }


    def on_model_change(self, form, model, is_created):
        if model.datainicio >= model.datafim:
            raise ValueError("A data de início deve ser anterior à data de término!")

    def _rel_btn(view, context, model, name):
        url = url_for('imprimir_relatorio', evento_id=model.id_Evento)
        return Markup(f'<a class="btn btn-sm btn-primary" href="{url}" target="_blank">🖨️ PDF</a>')

    column_formatters = {'relatorio': _rel_btn}


class OradorModelView(MasterAdmin):
    form_args = {
        **MasterAdmin.form_args,
        'sessoes': {'validators': []},
        'bio': {'validators': [DataRequired()]}
    }
class SessaoAdmin(MasterAdmin):
        form_args = {
            **MasterAdmin.form_args,
            'oradores': {'validators': []},
        }

admin = Admin(app, name='MS GESTÃO DE EVENTOS')
admin.add_view(EventoAdmin(Evento, db.session, name="Eventos"))
admin.add_view(MasterAdmin(Participante, db.session, name="Participantes"))
admin.add_view(OradorModelView(Orador, db.session, name="Oradores"))
admin.add_view(SessaoAdmin(Sessao, db.session, name="Sessões"))
admin.add_view(MasterAdmin(Inscricao, db.session, name="Financeiro"))

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=True, port=5000)