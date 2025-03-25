from flask import Flask, render_template, request, redirect, url_for, flash, Response
from flask_sqlalchemy import SQLAlchemy
from weasyprint import HTML
from flask import Response
from datetime import datetime
import os
import secrets



# Generate a secure secret key
app = Flask(__name__)
# app.secret_key = 'c9c25ab02aad2b6496181312028bf533'  # Ensure this is unique and secure
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///facturas.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

app.config["SECRET_KEY"] = os.getenv("SECRET_KEY", "c9c25ab02aad2b6496181312028bf533")
app.config["SQLALCHEMY_DATABASE_URI"] = os.getenv("DATABASE_URL", "sqlite:///facturas.db")
db = SQLAlchemy(app)






# Modelo de Factura
class Factura(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    cliente = db.Column(db.String(100), nullable=False)
    articulo = db.Column(db.String(200), nullable=False)
    cantidad = db.Column(db.Integer, nullable=False, default=1)
    precio = db.Column(db.Float, nullable=False)
    notas = db.Column(db.Text)
    total = db.Column(db.Float, nullable=False)
    fecha = db.Column(db.DateTime, default=datetime.utcnow)
    abonos = db.relationship('Abono', backref='factura', lazy=True)

    @property
    def total_abonado(self):
        return sum(abono.monto for abono in self.abonos)

    @property
    def saldo_pendiente(self):
        return self.total - self.total_abonado
    
    # Método para calcular el total automáticamente
    def calcular_total(self):
        self.total = self.cantidad * self.precio

# Modelo de Abono
class Abono(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    factura_id = db.Column(db.Integer, db.ForeignKey('factura.id'), nullable=False)
    monto = db.Column(db.Float, nullable=False)
    fecha_abono = db.Column(db.DateTime, default=datetime.utcnow)



@app.route('/', methods=['GET'])
def nueva_factura():
    facturas = Factura.query.all()  # Query all invoices from the database
    print(facturas)
    return render_template('index.html', facturas=facturas)  # Pass them to the template

# Ruta principal para mostrar y agregar facturas
@app.route('/factura/nueva', methods=['GET', 'POST'])
def crear_factura():
    print(request.method)
    if request.method == 'POST':
        cliente = request.form.get('cliente', '')  # Evita KeyError
        articulo = request.form.get('articulo', '')  
        cantidad = request.form.get('cantidad', '1')  # Valor por defecto 1
        precio = request.form.get('precio', '0.0')
        nota = request.form.get('nota', '')

        try:
            cantidad = int(cantidad)
            precio = float(precio)
            total = cantidad * precio  # Cálculo automático
        except ValueError:
            flash('Error en los valores ingresados.', 'danger')
            return redirect(url_for('crear_factura'))

        nueva_factura = Factura(cliente=cliente, articulo=articulo, cantidad=cantidad, precio=precio, total=total , notas=nota)
        db.session.add(nueva_factura)
        db.session.commit()

        flash('Factura creada con éxito.', 'success')
        return redirect(url_for('crear_factura'))

    return render_template('index.html', facturas=Factura.query.all())



@app.route('/factura/<int:factura_id>/abonar', methods=['POST'])
def abonar(factura_id):
    factura = Factura.query.get_or_404(factura_id)
    abonos = Abono.query.filter_by(factura_id=factura.id).all()
    monto = float(request.form['monto'])

    if monto <= 0 or monto > factura.saldo_pendiente:
        flash('Monto inválido', 'danger')
        return redirect(url_for('ver_factura', factura_id=factura.id))

    nuevo_abono = Abono(factura_id=factura.id, monto=monto)
    db.session.add(nuevo_abono)
    db.session.commit()

    flash(f'Abono de RD${monto:,.2f} registrado con éxito.', 'success')
    
    return render_template('factura.html', factura=factura , abonos=abonos)


@app.route('/factura/<int:id>')
def ver_factura(id):
    factura = Factura.query.get_or_404(id)
    abonos = Abono.query.filter_by(factura_id=id).all()
    print(factura)
    print(abonos)
    return render_template('factura.html', factura=factura , abonos=abonos)


@app.route('/factura/<int:id>/pdf')
def generar_pdf(id):

    # Obtener ruta absoluta del logo
    logo_path = os.path.abspath("static/logo.png")

    factura = Factura.query.get_or_404(id)
    abonos = Abono.query.filter_by(factura_id=id).all()
    print(abonos)
    html = render_template("factura_pdf.html", factura=factura, logo_path=logo_path , abonos=abonos)
    pdf = HTML(string=html).write_pdf()

    numero_factura = f"JTT-{factura.id:05d}"

    
    response = Response(pdf, content_type='application/pdf')
    response.headers['Content-Disposition'] = f'inline; filename=factura_{factura.id}.pdf'
    return response

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=True)

