from flask import Flask, render_template, request
from flask_mail import Mail, Message
from flask import session, redirect, url_for
import sqlite3, os
from flask import Flask, render_template, request, redirect, url_for, session, flash
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime
import json
import random
import string
from werkzeug.security import generate_password_hash
from flask import request, redirect, url_for, session, flash

app = Flask(__name__)
app.secret_key = "super_secret_key"
DB_PATH = "database.db"
REVOLUT_USERNAME = "YOUR_REVOLUTME"   # например, om666  → https://revolut.me/om666
PAYPAL_ME_USERNAME = "YOUR_PAYPALME"  # например, utech  → https://paypal.me/utech
VIPPS_PHONE = "48643809"              # твой Vipps-телефон
CURRENCY = "NOK"


def init_db():
    first_time = not os.path.exists(DB_PATH)
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()

    # Таблица пользователей
    c.execute("""CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT UNIQUE,
        password TEXT,
        role TEXT DEFAULT 'user'
    )""")

    # Таблица заказов
    c.execute("""CREATE TABLE IF NOT EXISTS orders (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        items TEXT,
        total REAL,
        payment_method TEXT,
        status TEXT DEFAULT 'Оплачено',
        date TEXT
    )""")

    conn.commit()

    # Создаём суперпользователя при первом запуске
    if first_time:
        try:
            password_hash = generate_password_hash("meliadus23")
            c.execute("INSERT INTO users (username, password, role) VALUES (?, ?, ?)",
                      ("s@sfoods.org", password_hash, "admin"))
            conn.commit()
            print("✅ Админ создан: s@sfoods.org / meliadus23")
        except:
            pass

    conn.close()

init_db()


# ==== Пример списка товаров ====


products = [
    {
        "id": 1,
        "name_ru": "Умная лампочка",
        "name_en": "Smart bulb",
        "description_ru": "RGB лампочка с управлением через приложение.",
        "description_en": "RGB bulb controllable via mobile app.",
        "price": 299,
        "image": "https://picsum.photos/400/300?random=1"
    },
    {
        "id": 2,
        "name_ru": "Wi-Fi розетка",
        "name_en": "Wi-Fi smart plug",
        "description_ru": "Розетка с удалённым управлением.",
        "description_en": "Remote-controlled smart plug.",
        "price": 199,
        "image": "https://picsum.photos/400/300?random=2"
    },
    {
        "id": 3,
        "name_ru": "Датчик движения",
        "name_en": "Motion sensor",
        "description_ru": "Беспроводной датчик движения с уведомлениями.",
        "description_en": "Wireless motion sensor with notifications.",
        "price": 249,
        "image": "https://picsum.photos/400/300?random=3"
    },
    {
        "id": 4,
        "name_ru": "IP-камера",
        "name_en": "IP camera",
        "description_ru": "Камера видеонаблюдения с ночным режимом.",
        "description_en": "Surveillance camera with night vision mode.",
        "price": 499,
        "image": "https://picsum.photos/400/300?random=4"
    },
    {
        "id": 5,
        "name_ru": "Сенсор температуры",
        "name_en": "Temperature sensor",
        "description_ru": "Беспроводной термодатчик для умного дома.",
        "description_en": "Wireless temperature sensor for smart homes.",
        "price": 149,
        "image": "https://picsum.photos/400/300?random=5"
    },
    {
        "id": 6,
        "name_ru": "Умный выключатель",
        "name_en": "Smart switch",
        "description_ru": "Сенсорный выключатель с Wi-Fi управлением.",
        "description_en": "Touch switch with Wi-Fi control.",
        "price": 199,
        "image": "https://picsum.photos/400/300?random=6"
    },
    {
        "id": 7,
        "name_ru": "Сирена безопасности",
        "name_en": "Security siren",
        "description_ru": "Громкая сирена для сигнализации.",
        "description_en": "Loud siren for alarm systems.",
        "price": 299,
        "image": "https://picsum.photos/400/300?random=7"
    },
    {
        "id": 8,
        "name_ru": "LED лента",
        "name_en": "LED strip",
        "description_ru": "Светодиодная лента с пультом.",
        "description_en": "LED strip with remote control.",
        "price": 349,
        "image": "https://picsum.photos/400/300?random=8"
    },
    {
        "id": 9,
        "name_ru": "Смарт-замок",
        "name_en": "Smart lock",
        "description_ru": "Электронный замок с управлением со смартфона.",
        "description_en": "Electronic lock with smartphone control.",
        "price": 899,
        "image": "https://picsum.photos/400/300?random=9"
    },
    {
        "id": 10,
        "name_ru": "Система полива",
        "name_en": "Irrigation system",
        "description_ru": "Автоматическая система полива для сада.",
        "description_en": "Automatic garden irrigation system.",
        "price": 599,
        "image": "https://picsum.photos/400/300?random=10"
    }
]




# Статусы: в БД храним только КОДЫ

# Полный список кодов статусов и подписи для RU/EN
STATUS_CHOICES = [
    ("awaiting_payment",       {"ru": "Ожидает оплаты",         "en": "Awaiting payment"}),
    ("awaiting_confirmation",  {"ru": "Ожидает подтверждения",  "en": "Awaiting confirmation"}),
    ("paid",                   {"ru": "Оплачен",                "en": "Paid"}),
    ("shipped",                {"ru": "Отправлен",              "en": "Shipped"}),
    ("completed",              {"ru": "Завершен",               "en": "Completed"}),
    ("cancelled",              {"ru": "Отменен",                "en": "Cancelled"}),
]
STATUS_DICT = {code: labels for code, labels in STATUS_CHOICES}


STATUS_TEXT_TO_CODE = {
    # RU → code
    "Ожидает оплаты": "awaiting_payment",
    "Ожидает подтверждения": "awaiting_confirmation",
    "Оплачено": "paid",
    "Готовится": "processing",
    "Отправлено": "shipped",
    "Доставлено": "delivered",
    "Отменено": "cancelled",
    # EN → code (на случай старых записей)
    "Awaiting payment": "awaiting_payment",
    "Awaiting confirmation": "awaiting_confirmation",
    "Paid": "paid",
    "Processing": "processing",
    "Shipped": "shipped",
    "Delivered": "delivered",
    "Cancelled": "cancelled",
}

def status_label(lang, code):
    for k, labels in STATUS_CHOICES:
        if k == code:
            return labels.get(lang, code)
    return code


translations = {
    "en": {
        "site_title": "Territory of smart solutions",
        "menu_home": "Home",
        "menu_shop": "Shop",
        "menu_contacts": "Contact Us",
        "menu_login": "Login",
        "menu_account": "Account",
        "footer": "All rights reserved.",
        "read_more": "Read full article",   # в en
        "login_username": "Username",
        "login_username_placeholder": "Enter username",
        "login_password": "Password",
        "login_password_placeholder": "Enter password",
        "login_button": "Login",
        "contacts_name": "Name",
        "contacts_name_placeholder": "Your name",
        "contacts_email": "Email",
        "contacts_email_placeholder": "Your email",
        "contacts_message": "Message",
        "contacts_message_placeholder": "Write your message here...",
        "contacts_button": "Send",
        "shop_text": "Our shop will be here soon.",
        "account_title": "Account",
        "account_all_orders": "All Orders",
        "account_my_orders": "My Orders",
        "account_id": "ID",
        "account_user": "User",
        "account_items": "Items",
        "account_total": "Total",
        "account_payment": "Payment",
        "account_status": "Status",
        "account_date": "Date",
        "account_actions": "Actions",
        "status_paid": "Paid",
        "status_processing": "Processing",
        "status_shipped": "Shipped",
        "status_delivered": "Delivered",
        "status_cancelled": "Cancelled",
        "save_button": "Save",
        "delete_button": "Delete",
        "logout_button": "Logout",
        "no_account": "Don't have an account?",
        "register_button": "Register",
        "register_title": "Create an account",
        "register_username": "Username",
        "register_username_placeholder": "Enter username",
        "register_password": "Password",
        "register_password_placeholder": "Enter password",
        "register_submit": "Sign up",
        "already_have_account": "Already have an account?",
        "error_no_user": "User not found.",
        "error_bad_credentials": "Invalid username or password.",
        "please_login": "Please log in to continue."
    },
    "ru": {
        "site_title": "Территория умных решений",
        "menu_home": "Главная",
        "menu_shop": "Магазин",
        "menu_contacts": "Связаться",
        "menu_login": "Вход",
        "menu_account": "Аккаунт",
        "footer": "Все права защищены.",
        "read_more": "Читать полностью",    # в ru
        "login_username": "Логин",
        "login_username_placeholder": "Введите логин",
        "login_password": "Пароль",
        "login_password_placeholder": "Введите пароль",
        "login_button": "Войти",
        # --- новые для формы ---
        "contacts_name": "Имя",
        "contacts_name_placeholder": "Ваше имя",
        "contacts_email": "Email",
        "contacts_email_placeholder": "Ваш email",
        "contacts_message": "Сообщение",
        "contacts_message_placeholder": "Напишите сообщение...",
        "contacts_button": "Отправить",
        "shop_text": "Скоро здесь будет наш магазин.",
        "account_title": "Личный кабинет",
        "account_all_orders": "Все заказы",
        "account_my_orders": "Мои заказы",
        "account_id": "ID",
        "account_user": "Пользователь",
        "account_items": "Товары",
        "account_total": "Сумма",
        "account_payment": "Оплата",
        "account_status": "Статус",
        "account_date": "Дата",
        "account_actions": "Действия",
        "status_paid": "Оплачено",
        "status_processing": "Готовится",
        "status_shipped": "Отправлено",
        "status_delivered": "Доставлено",
        "status_cancelled": "Отменено",
        "save_button": "Сохранить",
        "delete_button": "Удалить",
        "logout_button": "Выйти",
        "no_account": "Нет аккаунта?",
        "register_button": "Зарегистрироваться",
        "register_title": "Создать аккаунт",
        "register_username": "Логин",
        "register_username_placeholder": "Введите логин",
        "register_password": "Пароль",
        "register_password_placeholder": "Введите пароль",
        "register_submit": "Создать",
        "already_have_account": "Уже есть аккаунт?",
        "error_no_user": "Пользователь не найден.",
        "error_bad_credentials": "Неверный логин или пароль.",
        "please_login": "Пожалуйста, войдите, чтобы продолжить."
    }
}


posts = [
    {
        "id": 1,
        "title_en": "Evening in the fjord",
        "title_ru": "Вечер во фьорде",
        "preview_en": "The wind whispers in the mountains, fjord waters glitter in the moonlight...",
        "preview_ru": "Тихо шепчет ветер в горах, воды фьорда блестят при луне...",
        "image": "https://picsum.photos/800/400?random=1",
        "gallery": [
            "https://picsum.photos/800/400?random=4",
            "https://picsum.photos/800/400?random=5",
            "https://picsum.photos/800/400?random=6"
        ]
    },
    {
        "id": 2,
        "title_en": "Winter silence",
        "title_ru": "Зимняя тишина",
        "preview_en": "Snow hides the houses, only the stars sparkle in the distance...",
        "preview_ru": "В снежной пелене скрылись дома, лишь звёзды мерцают вдали...",
        "image": "https://picsum.photos/800/400?random=2",
        "gallery": [
            "https://picsum.photos/800/400?random=8",
            "https://picsum.photos/800/400?random=5"
        ]
    },
    {
        "id": 3,
        "title_en": "Morning in the mountains",
        "title_ru": "Утро в горах",
        "preview_en": "The mist creeps along the shore, and the sun meets the dawn...",
        "preview_ru": "Туман стелется вдоль берега, и солнце встречает рассвет...",
        "image": "https://picsum.photos/800/400?random=3",
        "gallery": [
            "https://picsum.photos/800/400?random=9"

        ]
    }
]


app.config['MAIL_SERVER'] = 'smtp.gmail.com'  # или другой SMTP сервер
app.config['MAIL_PORT'] = 587
app.config['MAIL_USE_TLS'] = True
app.config['MAIL_USERNAME'] = 'ТВОЯ_ПОЧТА'  # почта, с которой будет отправляться
app.config['MAIL_PASSWORD'] = 'ПАРОЛЬ_ИЛИ_APP_PASSWORD'  # пароль или App Password

mail = Mail(app)

from flask import request

@app.context_processor
def inject_request():
    return dict(request=request)

def render_lang(template, lang, **kwargs):
    cart_count = len(session.get("cart", []))
    return render_template(
        template,
        lang=lang,
        tr=translations[lang],
        posts=posts,
        cart_count=cart_count,
        **kwargs
    )



# Главная
@app.route("/")
def index_en():
    return render_lang("index.html", "en")

@app.route("/ru")
def index_ru():
    return render_lang("index.html", "ru")



# Контакты


@app.route("/contacts", methods=["GET", "POST"])
def contacts_en():
    if request.method == "POST":
        try:
            name = request.form['name']
            email = request.form['email']
            message_text = request.form['message']

            msg = Message(
                subject=f"Contact form from {name}",
                sender=app.config['MAIL_USERNAME'],
                recipients=["s@sfoods.org"]
            )
            msg.body = f"From: {name} <{email}>\n\n{message_text}"
            mail.send(msg)

            return render_lang("contacts.html", "en", success="Your message has been sent!")
        except Exception as e:
            return render_lang("contacts.html", "en", error=f"Error sending message: {e}")

    return render_lang("contacts.html", "en")


@app.route("/ru/contacts", methods=["GET", "POST"])
def contacts_ru():
    if request.method == "POST":
        try:
            name = request.form['name']
            email = request.form['email']
            message_text = request.form['message']

            msg = Message(
                subject=f"Обратная связь от {name}",
                sender=app.config['MAIL_USERNAME'],
                recipients=["s@sfoods.org"]
            )
            msg.body = f"От: {name} <{email}>\n\n{message_text}"
            mail.send(msg)

            return render_lang("contacts.html", "ru", success="Сообщение отправлено!")
        except Exception as e:
            return render_lang("contacts.html", "ru", error=f"Ошибка отправки: {e}")

    return render_lang("contacts.html", "ru")



@app.route("/post/<int:post_id>")
def post_en(post_id):
    post = next((p for p in posts if p["id"] == post_id), None)
    if not post:
        return "Post not found", 404
    return render_template("post.html", lang="en", tr=translations["en"], post=post)

@app.route("/ru/post/<int:post_id>")
def post_ru(post_id):
    post = next((p for p in posts if p["id"] == post_id), None)
    if not post:
        return "Статья не найдена", 404
    return render_template("post.html", lang="ru", tr=translations["ru"], post=post)


# ==== Магазин ====
@app.route("/shop")
def shop_en():
    return render_lang("shop.html", "en", products=products)

@app.route("/ru/shop")
def shop_ru():
    return render_lang("shop.html", "ru", products=products)


# ==== Добавление в корзину ====
@app.route("/add_to_cart/<int:product_id>")
def add_to_cart(product_id):
    cart = session.get("cart", {})
    if isinstance(cart, list):
        cart = {}

    cart[str(product_id)] = cart.get(str(product_id), 0) + 1
    session["cart"] = cart
    session.modified = True

    if request.referrer and "/ru/" in request.referrer:
        return redirect(url_for("shop_ru"))
    return redirect(url_for("shop_en"))



# ==== Просмотр корзины ====
@app.route("/cart")
def view_cart_en():
    cart = session.get("cart", {})
    if isinstance(cart, list):
        cart = {}
    cart_items, total = build_cart_items(cart)
    return render_lang("cart.html", "en", cart_items=cart_items, total=total)

@app.route("/ru/cart")
def view_cart_ru():
    cart = session.get("cart", {})
    if isinstance(cart, list):
        cart = {}
    cart_items, total = build_cart_items(cart)
    return render_lang("cart.html", "ru", cart_items=cart_items, total=total)



@app.route("/remove_from_cart/<int:product_id>")
def remove_from_cart(product_id):
    """Удалить товар из корзины."""
    lang = _lang_from_referrer()
    cart = session.get("cart", {})
    if isinstance(cart, list):
        cart = {}
    cart.pop(str(product_id), None)
    session["cart"] = cart
    session.modified = True
    return redirect(url_for("view_cart_ru" if lang == "ru" else "view_cart_en"))

def build_cart_items(cart_dict):
    """cart_dict = {'3': 2, ...} → (items, total).
       В items кладём name_ru/name_en, чтобы шаблоны брали по lang.
    """
    items, total = [], 0
    for pid, qty in cart_dict.items():
        p = next((x for x in products if x["id"] == int(pid)), None)
        if not p:
            continue
        subtotal = p["price"] * qty
        total += subtotal
        items.append({
            "id": p["id"],
            "name_ru": p.get("name_ru") or p.get("name"),
            "name_en": p.get("name_en") or p.get("name"),
            "price": p["price"],
            "qty": qty,
            "subtotal": subtotal
        })
    return items, total

def summarize_items(items_json, lang):
    """Из JSON массива позиций делает краткую строку для таблицы заказов."""
    try:
        arr = json.loads(items_json)
        lines = []
        for it in arr:
            # поддерживаем старые записи с 'name' и новые с 'name_ru/name_en'
            name = it.get(f"name_{lang}") or it.get("name") or "?"
            qty = it.get("qty", 1)
            lines.append(f"{name} × {qty}")
        return ", ".join(lines)
    except Exception:
        return items_json


# ==== Оформление заказа ====

@app.route("/checkout")
def checkout_en():
    if not session.get("user_id"):
        return redirect(url_for("login_en"))
    cart = session.get("cart", {})
    if isinstance(cart, list):
        cart = {}
    cart_items, total = build_cart_items(cart)
    return render_lang("checkout.html", "en", cart_items=cart_items, total=total)

@app.route("/ru/checkout")
def checkout_ru():
    if not session.get("user_id"):
        return redirect(url_for("login_ru"))
    cart = session.get("cart", {})
    if isinstance(cart, list):
        cart = {}
    cart_items, total = build_cart_items(cart)
    return render_lang("checkout.html", "ru", cart_items=cart_items, total=total)



def build_cart_items(cart_dict):
    items, total = [], 0
    for pid, qty in cart_dict.items():
        product = next((p for p in products if p["id"] == int(pid)), None)
        if not product:
            continue
        subtotal = product["price"] * qty
        total += subtotal
        items.append({**product, "qty": qty, "subtotal": subtotal})
    return items, total

@app.route("/pay/vipps")
def pay_vipps():
    if not session.get("user_id"):
        return redirect(url_for("login_en"))

    items, total = get_cart_items()
    if not items:
        flash("Cart is empty." if session.get("lang") != "ru" else "Корзина пуста.", "warning")
        return redirect(url_for("shop_en"))

    # создаём «ожидает оплаты»
    order_id, _, reference = create_pending_order("Vipps (manual)")

    # язык пытаемся угадать по рефереру
    lang = "ru" if (request.referrer and "/ru/" in request.referrer) else "en"

    return render_lang(
        "pay_vipps.html",
        lang,
        total=total,
        order_id=order_id,
        reference=reference,
        vipps_phone="48643809",
    )

@app.route("/pay/revolut")
def pay_revolut():
    if not session.get("user_id"):
        return redirect(url_for("login_en"))
    order_id, total, ref = create_pending_order("Revolut")
    if not order_id:
        flash("Cart is empty.", "warning")
        return redirect(url_for("shop_en"))
    # revolut.me/<username>/<amount>-<currency>
    rev_url = f"https://revolut.me/{REVOLUT_USERNAME}/{int(total)}-{CURRENCY.lower()}" if REVOLUT_USERNAME else None
    return render_lang("payment_link.html", "en" if not request.path.startswith("/ru") else "ru",
                       method="Revolut", total=total, reference=ref,
                       external_url=rev_url, vipps_phone=None)

@app.route("/pay/paypal")
def pay_paypal():
    if not session.get("user_id"):
        return redirect(url_for("login_en"))
    order_id, total, ref = create_pending_order("PayPal")
    if not order_id:
        flash("Cart is empty.", "warning")
        return redirect(url_for("shop_en"))
    # PayPal.me/<username>/<amount> (валюта — как у аккаунта)
    pp_url = f"https://paypal.me/{PAYPAL_ME_USERNAME}/{int(total)}" if PAYPAL_ME_USERNAME else None
    return render_lang("payment_link.html", "en" if not request.path.startswith("/ru") else "ru",
                       method="PayPal", total=total, reference=ref,
                       external_url=pp_url, vipps_phone=None)


def create_pending_order(payment_method):
    cart = session.get("cart", {})
    if isinstance(cart, list):
        cart = {}  # миграция со старого формата

    items, total = build_cart_items(cart)
    if not items:
        return None, None, None  # нечего платить

    reference = f"ORD-{datetime.now():%Y%m%d%H%M%S}-{session.get('user_id','guest')}"
    # сохраним в БД
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("""INSERT INTO orders (user_id, items, total, payment_method, status, date)
                 VALUES (?, ?, ?, ?, ?, ?)""",
              (session.get("user_id"),
               json.dumps(items, ensure_ascii=False),
               float(total),
               payment_method,
               "awaiting_payment",  # ← было "Ожидает оплаты"
               datetime.now().isoformat(timespec="seconds")))

    conn.commit()
    order_id = c.lastrowid
    conn.close()
    return order_id, total, reference


def summarize_items(items_json):
    try:
        arr = json.loads(items_json)
        lines = [f"{it.get('name','?')} × {it.get('qty',1)}" for it in arr]
        return ", ".join(lines)
    except Exception:
        return items_json  # на всякий случай

def migrate_statuses():
    """Переводим все текстовые статусы в коды, если ещё не переведены."""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    try:
        c.execute("SELECT id, status FROM orders")
        rows = c.fetchall()
        changed = 0
        for oid, st in rows:
            if st in STATUS_TEXT_TO_CODE:          # был рус/англ текст
                code = STATUS_TEXT_TO_CODE[st]
                c.execute("UPDATE orders SET status=? WHERE id=?", (code, oid))
                changed += 1
            elif st in {s[0] for s in STATUS_CHOICES}:
                pass                                # уже код — ок
            else:
                # неизвестное значение — считаем как awaiting_payment
                c.execute("UPDATE orders SET status=? WHERE id=?", ("awaiting_payment", oid))
                changed += 1
        if changed:
            conn.commit()
    finally:
        conn.close()

# после init_db()
init_db()
migrate_statuses()



# регистрация

@app.route("/register", methods=["GET", "POST"])
def register_en():
    if request.method == "POST":
        username = request.form["username"]
        password = generate_password_hash(request.form["password"])
        try:
            conn = sqlite3.connect(DB_PATH)
            c = conn.cursor()
            c.execute("INSERT INTO users (username, password) VALUES (?, ?)", (username, password))
            conn.commit()
            conn.close()
            flash("Registration successful! Please log in.", "success")
            return redirect(url_for("login_en"))
        except:
            flash("User already exists.", "danger")

    return render_lang("register.html", "en")

@app.route("/ru/register", methods=["GET", "POST"])
def register_ru():
    if request.method == "POST":
        username = request.form["username"]
        password = generate_password_hash(request.form["password"])
        try:
            conn = sqlite3.connect(DB_PATH)
            c = conn.cursor()
            c.execute("INSERT INTO users (username, password) VALUES (?, ?)", (username, password))
            conn.commit()
            conn.close()
            flash("Регистрация успешна! Теперь войдите.", "success")
            return redirect(url_for("login_ru"))
        except:
            flash("Такой пользователь уже существует.", "danger")

    return render_lang("register.html", "ru")


# аккаунт

def summarize_items(items_json):
    try:
        arr = json.loads(items_json)
        lines = [f"{it.get('name','?')} × {it.get('qty',1)}" for it in arr]
        return ", ".join(lines)
    except Exception:
        return items_json

@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("index_en"))

def get_orders_for_admin(lang):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("""
        SELECT orders.id AS order_id,
               users.username,
               orders.items,
               orders.total,
               orders.payment_method,
               orders.status,
               orders.date
        FROM orders
        JOIN users ON orders.user_id = users.id
        ORDER BY orders.id DESC
    """)
    rows = c.fetchall()
    conn.close()

    orders = []
    for r in rows:
        status_code = r[5]
        orders.append({
            "id": r[0],
            "username": r[1],
            "items_text": summarize_items(r[2]),
            "total": r[3],
            "payment": r[4],
            "status_code": status_code,
            "status_label": status_choices_dict[status_code][lang] if status_code in status_choices_dict else status_code,
            "date": r[6]
        })
    return orders


def get_orders_for_user(user_id, lang):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("""
        SELECT id, items, total, payment_method, status, date
        FROM orders
        WHERE user_id = ?
        ORDER BY id DESC
    """, (user_id,))
    rows = c.fetchall()
    conn.close()

    orders = []
    for r in rows:
        status_code = r[4]
        orders.append({
            "id": r[0],
            "items_text": summarize_items(r[1]),
            "total": r[2],
            "payment": r[3],
            "status_code": status_code,
            "status_label": status_choices_dict[status_code][lang] if status_code in status_choices_dict else status_code,
            "date": r[5]
        })
    return orders


# --- Личный кабинет (EN) ---
@app.route("/account")
def account_en():
    return render_account("en")

# --- Личный кабинет (RU) ---
@app.route("/ru/account")
def account_ru():
    return render_account("ru")


def render_account(lang):
    if "user_id" not in session:
        return redirect(url_for("login_en" if lang == "en" else "login_ru"))

    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()

    status_choices = [
        ("pending", {"ru": "Ожидает оплаты", "en": "Pending payment"}),
        ("paid", {"ru": "Оплачено", "en": "Paid"}),
        ("shipped", {"ru": "Отправлено", "en": "Shipped"}),
        ("completed", {"ru": "Завершено", "en": "Completed"}),
        ("cancelled", {"ru": "Отменено", "en": "Cancelled"})
    ]

    orders = []

    if session.get("role") == "admin":
        c.execute("""
            SELECT orders.id, users.username, orders.items, orders.total,
                   orders.payment_method, orders.status, orders.date
            FROM orders
            JOIN users ON orders.user_id = users.id
            ORDER BY orders.id DESC
        """)
        rows = c.fetchall()

        for r in rows:
            orders.append({
                "id": r[0],
                "username": r[1],
                "items_text": summarize_items(r[2]),
                "total": r[3],
                "payment": r[4],
                "status_code": r[5],
                "status_label": dict((code, lbls[lang]) for code, lbls in status_choices).get(r[5], r[5]),
                "date": r[6],
            })

        conn.close()
        return render_lang("account.html", lang, orders=orders, role="admin", status_choices=status_choices)

    else:
        c.execute("""
            SELECT id, items, total, payment_method, status, date
            FROM orders
            WHERE user_id=?
            ORDER BY id DESC
        """, (session["user_id"],))
        rows = c.fetchall()

        for r in rows:
            orders.append({
                "id": r[0],
                "items_text": summarize_items(r[1]),
                "total": r[2],
                "payment": r[3],
                "status_label": dict((code, lbls[lang]) for code, lbls in status_choices).get(r[4], r[4]),
                "date": r[5],
            })

        conn.close()
        return render_lang("account.html", lang, orders=orders, role="user")

def summarize_items(items_json, lang="en"):
    try:
        items = json.loads(items_json)
    except:
        return items_json  # если не JSON, вернуть как есть

    result = []
    for item in items:
        product = next((p for p in products if p["id"] == item["id"]), None)
        if product:
            name = product.get(f"name_{lang}", product.get("name", "?"))
        else:
            name = "?"
        result.append(f"{name} × {item.get('qty', 1)}")
    return ", ".join(result)


def _lang_from_referrer():
    ref = request.referrer or ""
    return "ru" if "/ru/" in ref else "en"

@app.route("/update_cart/<int:product_id>", methods=["POST"])
def update_cart(product_id):
    """Обновить количество товара в корзине (0 = удалить)."""
    lang = _lang_from_referrer()
    try:
        qty = int(request.form.get("qty", 1))
    except ValueError:
        qty = 1

    cart = session.get("cart", {})
    # миграция со старого формата (list) на dict
    if isinstance(cart, list):
        cart = {}

    key = str(product_id)
    if qty <= 0:
        cart.pop(key, None)
    else:
        cart[key] = qty

    session["cart"] = cart
    session.modified = True

    return redirect(url_for("view_cart_ru" if lang == "ru" else "view_cart_en"))


@app.route("/update_order/<int:order_id>", methods=["POST"])
def update_order(order_id):
    if session.get("role") != "admin":
        return redirect(url_for("account_en"))

    new_code = request.form["status_code"]  # ожидаем код
    if new_code not in {k for k, _ in STATUS_CHOICES}:
        flash("Invalid status", "error")
        return redirect(url_for("account_en"))

    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("UPDATE orders SET status=? WHERE id=?", (new_code, order_id))
    conn.commit()
    conn.close()
    return redirect(request.referrer or url_for("account_en"))


@app.route("/delete_order/<int:order_id>")
def delete_order(order_id):
    if session.get("role") != "admin":
        return redirect(url_for("account_en"))

    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("DELETE FROM orders WHERE id=?", (order_id,))
    conn.commit()
    conn.close()
    # назад туда, откуда пришли (EN/RU корректно)
    return redirect(request.referrer or url_for("account_en"))


# логин

@app.route("/login", methods=["GET","POST"])
def login_en():
    if request.method == "POST":
        return process_login("en")
    return render_lang("login.html", "en")

@app.route("/ru/login", methods=["GET","POST"])
def login_ru():
    if request.method == "POST":
        return process_login("ru")
    return render_lang("login.html", "ru")

# работа с пользователями users

@app.route("/admin/users")
def admin_users():
    if session.get("role") != "admin":
        flash("Access denied", "error")
        return redirect(url_for("login_en"))

    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT id, username, role, password FROM users ORDER BY id")
    users = c.fetchall()
    conn.close()

    lang = "ru" if (request.referrer and "/ru/" in request.referrer) else "en"
    return render_lang("admin_users.html", lang, users=users)



@app.route("/admin/delete_user/<int:user_id>")
def delete_user(user_id):
    if session.get("role") != "admin":
        flash("Access denied", "error")
        return redirect(url_for("login_en"))

    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("DELETE FROM users WHERE id=?", (user_id,))
    conn.commit()
    conn.close()

    flash("User deleted.", "success")
    return redirect(url_for("admin_users"))


@app.route("/admin/reset_password/<int:user_id>")
def reset_password(user_id):
    if session.get("role") != "admin":
        flash("Access denied", "error")
        return redirect(url_for("login_en"))

    # Генерация нового пароля
    new_password = ''.join(random.choices(string.ascii_letters + string.digits, k=10))
    hashed = generate_password_hash(new_password)

    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("UPDATE users SET password=? WHERE id=?", (hashed, user_id))
    conn.commit()
    conn.close()

    flash(f"New password for user ID {user_id}: {new_password}", "success")
    return redirect(url_for("admin_users"))

@app.route("/order/paid/<int:order_id>")
def order_paid(order_id):
    lang = "ru" if (request.referrer and "/ru/" in (request.referrer or "")) else "en"
    if not session.get("user_id"):
        return redirect(url_for("login_ru" if lang=="ru" else "login_en"))

    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    if session.get("role") == "admin":
        c.execute("UPDATE orders SET status=? WHERE id=?", ("awaiting_confirmation", order_id))
    else:
        c.execute("UPDATE orders SET status=? WHERE id=? AND user_id=?",
                  ("awaiting_confirmation", order_id, session["user_id"]))
    conn.commit()
    conn.close()

    session["cart"] = {}
    session.modified = True

    flash("Спасибо! Мы скоро проверим оплату." if lang=="ru"
         else "Thanks! We'll verify your payment shortly.", "success")
    return redirect(url_for("account_ru" if lang=="ru" else "account_en"))

def _build_cart_items():
    cart = session.get("cart", {})
    if isinstance(cart, list):
        cart = {}
    items, total = [], 0
    for pid, qty in cart.items():
        p = next((x for x in products if x["id"] == int(pid)), None)
        if not p:
            continue
        subtotal = p["price"] * qty
        total += subtotal
        items.append({
            "id": p["id"],
            "name": p["name"],
            "price": p["price"],
            "qty": qty,
            "subtotal": subtotal
        })
    return items, total


def process_login(lang):
    username = request.form.get("username", "").strip()
    password = request.form.get("password", "").strip()

    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT id, password, role FROM users WHERE username=?", (username,))
    user = c.fetchone()
    conn.close()

    if not user:
        flash(translations[lang]["error_no_user"], "error")
        return redirect(url_for("login_ru" if lang=="ru" else "login_en"))

    if not check_password_hash(user[1], password):
        flash(translations[lang]["error_bad_credentials"], "error")
        return redirect(url_for("login_ru" if lang=="ru" else "login_en"))

    # успех
    session["user_id"] = user[0]
    session["role"] = user[2]
    session["username"] = username
    return redirect(url_for("account_ru" if lang=="ru" else "account_en"))

def build_cart_items(cart_dict):
    items, total = [], 0
    for pid, qty in cart_dict.items():
        product = next((p for p in products if p["id"] == int(pid)), None)
        if not product:
            continue
        subtotal = product["price"] * qty
        total += subtotal
        items.append({**product, "qty": qty, "subtotal": subtotal})
    return items, total

def get_cart_items():
    """Возвращает (items, total) из session['cart'] c миграцией со старого формата."""
    cart = session.get("cart", {})
    if isinstance(cart, list):  # на всякий
        cart = {}
    return build_cart_items(cart)


if __name__ == "__main__":
    app.run(debug=True)
