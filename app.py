import os
from flask import Flask, render_template, request, redirect, url_for, flash, send_from_directory
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
from werkzeug.utils import secure_filename

app = Flask(__name__)
app.secret_key = 'warehouse-secret-key'

# =========================
# ЗАГРУЗКА ФОТО
# =========================

UPLOAD_FOLDER = os.path.join(
    os.path.dirname(os.path.abspath(__file__)),
    'static',
    'uploads'
)

ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'webp'}

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# =========================
# БАЗА ДАННЫХ
# =========================

database_url = os.environ.get('DATABASE_URL')

if database_url and database_url.startswith('postgres://'):
    database_url = database_url.replace(
        'postgres://',
        'postgresql://',
        1
    )

if database_url:
    app.config['SQLALCHEMY_DATABASE_URI'] = database_url
else:
    db_path = os.path.join(
        os.path.dirname(os.path.abspath(__file__)),
        'warehouse.db'
    )
    app.config['SQLALCHEMY_DATABASE_URI'] = f'sqlite:///{db_path}'

app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)

# =========================
# ФУНКЦИИ
# =========================

def allowed_file(filename):
    return (
        '.' in filename and
        filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS
    )

# =========================
# МОДЕЛИ
# =========================

class Category(db.Model):
    id = db.Column(db.Integer, primary_key=True)

    name = db.Column(
        db.String(100),
        unique=True,
        nullable=False
    )

    products = db.relationship(
        'Product',
        backref='category',
        lazy=True,
        cascade='all, delete-orphan'
    )


class Product(db.Model):
    id = db.Column(db.Integer, primary_key=True)

    name = db.Column(
        db.String(200),
        nullable=False
    )

    category_id = db.Column(
        db.Integer,
        db.ForeignKey('category.id')
    )

    quantity = db.Column(
        db.Integer,
        default=0
    )

    size = db.Column(db.String(50))

    color = db.Column(db.String(50))

    image = db.Column(db.String(200))

    # НОВОЕ
    cost_price = db.Column(db.Float, default=0)

    sale_price = db.Column(db.Float, default=0)

    created_at = db.Column(
        db.DateTime,
        default=datetime.now
    )

    operations = db.relationship(
        'Operation',
        backref='product',
        lazy=True,
        cascade='all, delete-orphan'
    )


class Operation(db.Model):
    id = db.Column(db.Integer, primary_key=True)

    product_id = db.Column(
        db.Integer,
        db.ForeignKey('product.id'),
        nullable=False
    )

    operation_type = db.Column(
        db.String(20),
        nullable=False
    )

    quantity = db.Column(
        db.Integer,
        nullable=False
    )

    note = db.Column(db.Text)

    supplier_name = db.Column(db.String(100))

    # ПРИБЫЛЬ
    profit = db.Column(db.Float, default=0)

    created_at = db.Column(
        db.DateTime,
        default=datetime.now
    )

# =========================
# СОЗДАНИЕ БАЗЫ
# =========================

with app.app_context():
    db.create_all()

    if Category.query.count() == 0:

        categories = [
            'Кроссовки',
            'Кеды',
            'Ботинки',
            'Сапоги',
            'Туфли',
            'Футболки',
            'Джинсы',
            'Куртки',
            'Худи',
            'Шапки'
        ]

        for cat_name in categories:
            db.session.add(Category(name=cat_name))

        db.session.commit()

# =========================
# ГЛАВНАЯ
# =========================

@app.route('/')
def index():

    total_products = Product.query.count()

    total_items = db.session.query(
        db.func.sum(Product.quantity)
    ).scalar() or 0

    low_stock = Product.query.filter(
        Product.quantity == 0
    ).all()

    recent_operations = Operation.query.order_by(
        Operation.created_at.desc()
    ).limit(5).all()

    total_profit = db.session.query(
        db.func.sum(Operation.profit)
    ).scalar() or 0

    return render_template(
        'index.html',
        total_products=total_products,
        total_items=total_items,
        low_stock=low_stock,
        recent_operations=recent_operations,
        total_profit=total_profit
    )

# =========================
# ТОВАРЫ
# =========================

@app.route('/products')
def products():

    search = request.args.get('search', '')

    category_id = request.args.get('category', '')

    query = Product.query

    if search:
        query = query.filter(Product.name.contains(search))

    if category_id:
        query = query.filter(
            Product.category_id == category_id
        )

    products = query.order_by(Product.name).all()

    categories = Category.query.order_by(
        Category.name
    ).all()

    return render_template(
        'products.html',
        products=products,
        categories=categories,
        search=search,
        selected_category=category_id
    )

# =========================
# ДОБАВИТЬ ТОВАР
# =========================

@app.route('/products/add', methods=['GET', 'POST'])
def add_product():

    if request.method == 'POST':

        name = request.form['name']

        category_id = request.form.get(
            'category_id'
        ) or None

        size = request.form.get('size', '')

        color = request.form.get('color', '')

        cost_price = float(
            request.form.get('cost_price', 0)
        )

        sale_price = float(
            request.form.get('sale_price', 0)
        )

        if Product.query.filter_by(name=name).first():

            flash(
                'Товар с таким названием уже есть',
                'error'
            )

            categories = Category.query.order_by(
                Category.name
            ).all()

            return render_template(
                'product_form.html',
                categories=categories,
                action='add'
            )

        image_filename = None

        if 'image' in request.files:

            file = request.files['image']

            if (
                file and
                file.filename and
                allowed_file(file.filename)
            ):

                filename = secure_filename(file.filename)

                unique_name = (
                    f"{datetime.now().strftime('%Y%m%d_%H%M%S')}_{filename}"
                )

                file.save(
                    os.path.join(
                        app.config['UPLOAD_FOLDER'],
                        unique_name
                    )
                )

                image_filename = unique_name

        product = Product(
            name=name,
            category_id=category_id,
            size=size,
            color=color,
            image=image_filename,
            cost_price=cost_price,
            sale_price=sale_price
        )

        db.session.add(product)

        db.session.commit()

        flash('Товар добавлен', 'success')

        return redirect(url_for('products'))

    categories = Category.query.order_by(
        Category.name
    ).all()

    return render_template(
        'product_form.html',
        categories=categories,
        action='add'
    )

# =========================
# РЕДАКТИРОВАТЬ ТОВАР
# =========================

@app.route('/products/edit/<int:product_id>', methods=['GET', 'POST'])
def edit_product(product_id):

    product = Product.query.get_or_404(product_id)

    if request.method == 'POST':

        name = request.form['name']
        category_id = request.form.get(
            'category_id'
        ) or None
        size = request.form.get('size', '')
        color = request.form.get('color', '')
        cost_price = float(
            request.form.get('cost_price', 0)
        )
        sale_price = float(
            request.form.get('sale_price', 0)
        )

        existing = Product.query.filter_by(name=name).first()
        if existing and existing.id != product_id:
            flash(
                'Товар с таким названием уже есть',
                'error'
            )
            categories = Category.query.order_by(
                Category.name
            ).all()
            return render_template(
                'product_form.html',
                product=product,
                categories=categories,
                action='edit'
            )

        if 'image' in request.files:
            file = request.files['image']
            if (
                file and
                file.filename and
                allowed_file(file.filename)
            ):
                filename = secure_filename(file.filename)
                unique_name = (
                    f"{datetime.now().strftime('%Y%m%d_%H%M%S')}_{filename}"
                )
                file.save(
                    os.path.join(
                        app.config['UPLOAD_FOLDER'],
                        unique_name
                    )
                )
                product.image = unique_name

        product.name = name
        product.category_id = category_id
        product.size = size
        product.color = color
        product.cost_price = cost_price
        product.sale_price = sale_price

        db.session.commit()

        flash('Товар обновлен', 'success')

        return redirect(url_for('products'))

    categories = Category.query.order_by(
        Category.name
    ).all()

    return render_template(
        'product_form.html',
        product=product,
        categories=categories,
        action='edit'
    )


# =========================
# ПРОДАЖИ
# =========================

@app.route('/sales', methods=['GET', 'POST'])
def sales():

    if request.method == 'POST':

        product_id = int(
            request.form['product_id']
        )

        quantity = int(
            request.form['quantity']
        )

        supplier_name = request.form.get(
            'supplier_name',
            ''
        )

        product = Product.query.get_or_404(
            product_id
        )

        if product.quantity < quantity:

            flash(
                f'Недостаточно товара. В наличии: {product.quantity} шт',
                'error'
            )

            products = Product.query.order_by(
                Product.name
            ).all()

            return render_template(
                'sales.html',
                products=products
            )

        product.quantity -= quantity

        # ПРИБЫЛЬ
        profit = (
            product.sale_price -
            product.cost_price
        ) * quantity

        operation = Operation(
            product_id=product_id,
            operation_type='sale',
            quantity=quantity,
            supplier_name=supplier_name,
            profit=profit
        )

        db.session.add(operation)

        db.session.commit()

        flash(
            f'Продажа: -{quantity} шт | Прибыль: {profit}',
            'success'
        )

        return redirect(url_for('sales'))

    products = Product.query.order_by(
        Product.name
    ).all()

    return render_template(
        'sales.html',
        products=products
    )

# =========================
# ПОСТУПЛЕНИЕ ТОВАРА
# =========================

@app.route('/stock/add', methods=['GET', 'POST'])
def stock_add():

    if request.method == 'POST':

        product_id = int(
            request.form['product_id']
        )

        quantity = int(
            request.form['quantity']
        )

        supplier_name = request.form.get(
            'supplier_name',
            ''
        )

        product = Product.query.get_or_404(
            product_id
        )

        product.quantity += quantity

        operation = Operation(
            product_id=product_id,
            operation_type='stock_add',
            quantity=quantity,
            supplier_name=supplier_name
        )

        db.session.add(operation)

        db.session.commit()

        flash(
            f'Поступление товара: +{quantity} шт',
            'success'
        )

        return redirect(url_for('stock_add'))

    products = Product.query.order_by(
        Product.name
    ).all()

    return render_template(
        'purchase.html',
        products=products
    )

# =========================
# ИСТОРИЯ
# =========================

@app.route('/history')
def history():

    operations = Operation.query.order_by(
        Operation.created_at.desc()
    ).all()

    return render_template(
        'history.html',
        operations=operations
    )

# =========================
# УДАЛЕНИЕ ТОВАРА
# =========================

@app.route('/products/delete/<int:product_id>', methods=['POST'])
def delete_product(product_id):

    product = Product.query.get_or_404(product_id)

    db.session.delete(product)

    db.session.commit()

    flash('Товар удален', 'success')

    return redirect(url_for('products'))

# =========================
# КАТЕГОРИИ
# =========================

@app.route('/categories', methods=['GET', 'POST'])
def categories():

    if request.method == 'POST':

        name = request.form['name']

        if Category.query.filter_by(name=name).first():

            flash(
                'Такая категория уже есть',
                'error'
            )

        else:

            category = Category(name=name)

            db.session.add(category)

            db.session.commit()

            flash(
                'Категория добавлена',
                'success'
            )

        return redirect(url_for('categories'))

    categories = Category.query.order_by(
        Category.name
    ).all()

    return render_template(
        'categories.html',
        categories=categories
    )

# =========================
# УДАЛЕНИЕ КАТЕГОРИИ
# =========================

@app.route('/categories/delete/<int:category_id>', methods=['POST'])
def delete_category(category_id):

    category = Category.query.get_or_404(category_id)

    db.session.delete(category)

    db.session.commit()

    flash('Категория удалена', 'success')

    return redirect(url_for('categories'))


# =========================
# ФОТО
# =========================

@app.route('/static/uploads/<filename>')
def uploaded_file(filename):

    return send_from_directory(
        app.config['UPLOAD_FOLDER'],
        filename
    )

# =========================
# ЗАПУСК
# =========================

if __name__ == '__main__':

    port = int(os.environ.get('PORT', 5000))

    app.run(
        host='0.0.0.0',
        port=port,
        debug=True
    )