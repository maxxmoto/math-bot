# bot.py
import os
import asyncio
import logging
import random
import math
from aiogram import Bot, Dispatcher, types, F
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.context import FSMContext
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import FSInputFile
from aiogram.filters import Command
from fpdf import FPDF
from fpdf.enums import XPos, YPos

# ---------- НАСТРОЙКИ ----------
TOKEN = "8755532322:AAFnYy-VY4MRh4E3DyzcB5zSaarQvXQjuSA"              # ← замените на свой
TEMP_DIR = "temp_pdf"
os.makedirs(TEMP_DIR, exist_ok=True)

# ---------- ИНИЦИАЛИЗАЦИЯ ----------
bot = Bot(token=TOKEN)
dp = Dispatcher(storage=MemoryStorage())
logging.basicConfig(level=logging.INFO)

# ---------- ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ ----------
def randint(a, b): return random.randint(a, b)
def randchoice(arr): return random.choice(arr)
def shuffle(arr):
    a = arr[:]
    random.shuffle(a)
    return a

# Unicode-индексы
SUPER = str.maketrans("0123456789", "⁰¹²³⁴⁵⁶⁷⁸⁹")
SUB   = str.maketrans("0123456789", "₀₁₂₃₄₅₆₇₈₉")

def super_num(n: int) -> str:
    return str(n).translate(SUPER)

def sub_num(n: int) -> str:
    return str(n).translate(SUB)

# ---------- ГЕНЕРАТОРЫ ЗАДАЧ ----------
# Логарифмы
def gen_log_simple():
    b = randchoice([2,3,4,5,6,7,8,9,10])
    e = randint(1,5)
    return {"text": f"Вычислите: log{sub_num(b)}({b**e})", "answer": str(e)}

def gen_log_fraction():
    b = randchoice([2,3,4,5])
    e = randint(1,4)
    return {"text": f"Вычислите: log{sub_num(b)}(1/{b**e})", "answer": str(-e)}

def gen_log_sum():
    b = randchoice([2,3,5])
    e1, e2 = randint(1,3), randint(1,3)
    return {"text": f"Вычислите: log{sub_num(b)}({b**e1}) + log{sub_num(b)}({b**e2})", "answer": str(e1+e2)}

def gen_log_diff():
    b = randchoice([2,3,5])
    e1, e2 = randint(2,5), randint(1,4)
    if e2 >= e1: e2 = e1 - 1
    return {"text": f"Вычислите: log{sub_num(b)}({b**e1}) - log{sub_num(b)}({b**e2})", "answer": str(e1-e2)}

def gen_log_power():
    b = randchoice([2,3,5,7])
    e, p = randint(1,4), randint(2,4)
    return {"text": f"Вычислите: log{sub_num(b)}({b**e}{super_num(p)})", "answer": str(e*p)}

def gen_log_eq():
    b = randchoice([2,3,5])
    e1, e2 = randint(1,3), randint(1,3)
    return {"text": f"Решите: log{sub_num(b)}(x) = log{sub_num(b)}({b**e1}) + log{sub_num(b)}({b**e2})",
            "answer": f"x = {b**(e1+e2)}"}

LOG_GENS = [gen_log_simple, gen_log_fraction, gen_log_sum, gen_log_diff, gen_log_power, gen_log_eq]

# Тригонометрия
def gen_trig_sin():
    vals = [('0','πn'), ('1','π/2 + 2πn'), ('-1','-π/2 + 2πn'), ('1/2','(-1)ⁿ·π/6 + πn')]
    r, a = randchoice(vals)
    return {"text": f"Решите: sin(x) = {r}", "answer": f"x = {a}, n∈Z"}

def gen_trig_cos():
    vals = [('0','π/2 + πn'), ('1','2πn'), ('-1','π + 2πn'), ('1/2','±π/3 + 2πn')]
    r, a = randchoice(vals)
    return {"text": f"Решите: cos(x) = {r}", "answer": f"x = {a}, n∈Z"}

def gen_trig_sin2x():
    k = randchoice([2,3,4])
    return {"text": f"Решите: sin({k}x) = 1/2",
            "answer": f"x = (-1)ⁿ·π/{6*k} + πn/{k}, n∈Z"}

TRIG_GENS = [gen_trig_sin, gen_trig_cos, gen_trig_sin2x]

# Производные
def gen_deriv_poly():
    d = randint(2,5)
    c = randchoice([1,2,3,4,5])
    c0 = randint(0,8)
    term = f" + {c0}" if c0 else ""
    return {"text": f"Найдите производную: f(x) = {c}x{super_num(d)}{term}",
            "answer": f"f'(x) = {c*d}x{super_num(d-1)}{' + 0' if c0 else ''}"}

def gen_deriv_sin():
    k = randchoice([1,2,3])
    coeff = randchoice([1,2,3])
    inner = "x" if k==1 else f"{k}x"
    prefix = "" if coeff==1 else str(coeff)
    return {"text": f"Найдите производную: f(x) = {prefix}sin({inner})",
            "answer": f"f'(x) = {'' if coeff*k==1 else coeff*k}cos({inner})"}

DERIV_GENS = [gen_deriv_poly, gen_deriv_sin]

# Первообразные
def gen_int_poly():
    n = randint(1,5)
    c = randchoice([1,2,3,4,5,6])
    return {"text": f"Найдите первообразную: f(x) = {c}x{super_num(n)}",
            "answer": f"F(x) = {c}/{n+1} x{super_num(n+1)} + C"}

def gen_int_sin():
    k = randchoice([1,2,3])
    inner = "x" if k==1 else f"{k}x"
    return {"text": f"Найдите первообразную: f(x) = sin({inner})",
            "answer": f"F(x) = -1/{k} cos({inner}) + C"}

INT_GENS = [gen_int_poly, gen_int_sin]

# Геометрия: треугольники
def gen_geom_heron():
    while True:
        a, b, c = randint(4,9), randint(4,9), randint(4,9)
        if a+b>c and a+c>b and b+c>a: break
    p = (a+b+c)/2
    area = math.sqrt(p*(p-a)*(p-b)*(p-c))
    return {"text": f"Стороны треугольника: AB={c}, BC={a}, AC={b}.\nНайдите площадь (формула Герона).",
            "answer": f"{area:.2f}",
            "draw": "heron", "a":a, "b":b, "c":c}

def gen_geom_pythag():
    triples = [(3,4,5),(5,12,13),(6,8,10),(8,15,17),(9,12,15)]
    a, b, c = randchoice(triples)
    return {"text": f"Катеты прямоугольного треугольника равны {a} и {b}.\nНайдите гипотенузу.",
            "answer": str(c),
            "draw": "pythag", "a":a, "b":b}

GEOM_GENS = [gen_geom_heron, gen_geom_pythag]

# Вероятность и комбинаторика
def gen_prob_urn():
    total = randint(10,15)
    white = randint(3, total-3)
    prob = white/total * (white-1)/(total-1)
    return {"text": f"В урне {white} белых и {total-white} чёрных шаров.\nВынимают 2 шара. Вероятность, что оба белые?",
            "answer": f"{prob:.3f}"}

def gen_prob_dice_sum():
    return {"text": "Бросают два кубика. Найдите вероятность, что сумма очков равна 8.",
            "answer": "5/36"}

def gen_comb_choice():
    n = randint(5,9)
    k = randint(2, n-2)
    c = math.comb(n, k)
    return {"text": f"Сколькими способами можно выбрать {k} дежурных из {n} учеников?",
            "answer": str(c)}

PROB_GENS = [gen_prob_urn, gen_prob_dice_sum, gen_comb_choice]

# Прогрессии
def gen_arith_n():
    a1, d, n = randint(1,10), randint(1,5), randint(4,8)
    return {"text": f"Арифм. прогрессия: a{sub_num(1)}={a1}, d={d}.\nНайдите a{sub_num(n)}.",
            "answer": str(a1 + (n-1)*d)}

def gen_arith_sum():
    a1, d, n = randint(1,10), randint(1,5), randint(5,10)
    s = (2*a1 + (n-1)*d) * n // 2
    return {"text": f"Арифм. прогрессия: a{sub_num(1)}={a1}, d={d}.\nНайдите сумму первых {n} членов.",
            "answer": str(s)}

ARITH_GENS = [gen_arith_n, gen_arith_sum]

def gen_geom_n():
    b1, q, n = randint(1,5), randchoice([2,3,4]), randint(4,7)
    return {"text": f"Геом. прогрессия: b{sub_num(1)}={b1}, q={q}.\nНайдите b{sub_num(n)}.",
            "answer": str(b1 * q**(n-1))}

GEOM_PROG_GENS = [gen_geom_n]

# Окружности
def gen_circle_len():
    r = randint(3,8)
    return {"text": f"Найдите длину окружности радиуса {r}.",
            "answer": f"C = 2π·{r} ≈ {2*math.pi*r:.1f}"}

def gen_circle_area():
    r = randint(3,8)
    return {"text": f"Найдите площадь круга радиуса {r}.",
            "answer": f"S = π·{r}² ≈ {math.pi*r*r:.1f}"}

CIRCLE_GENS = [gen_circle_len, gen_circle_area]

# Показательные уравнения
def gen_exp_simple():
    b = randchoice([2,3,5])
    e = randint(2,5)
    return {"text": f"Решите: {b}{super_num('x')} = {b**e}", "answer": str(e)}

EXP_GENS = [gen_exp_simple]

# Объёмы
def gen_vol_cyl():
    r = randint(2,5)
    h = randint(4,10)
    return {"text": f"Объём цилиндра: r={r} см, h={h} см.",
            "answer": f"V = π·{r}²·{h} ≈ {math.pi*r*r*h:.1f} см³"}

VOL_GENS = [gen_vol_cyl]

# Квадратные уравнения (нормальный генератор)
def gen_quadratic():
    a = randint(1,3)
    b = randint(-6,6)
    c = randint(-6,6)
    D = b*b - 4*a*c
    if D < 0:
        return {"text": f"Решите: {a}x² {'+' if b>=0 else ''}{b}x {'+' if c>=0 else ''}{c} = 0",
                "answer": "корней нет"}
    x1 = (-b + math.sqrt(D))/(2*a)
    x2 = (-b - math.sqrt(D))/(2*a)
    return {"text": f"Решите: {a}x² {'+' if b>=0 else ''}{b}x {'+' if c>=0 else ''}{c} = 0",
            "answer": f"x₁={x1:.2f}, x₂={x2:.2f}"}

QUAD_GENS = [gen_quadratic]

# Собираем все темы по классам
GRADE_TOPICS = {
    "9": {
        "Квадратные уравнения": QUAD_GENS,
        "Арифметическая прогрессия": ARITH_GENS,
        "Геометрическая прогрессия": GEOM_PROG_GENS,
        "Геометрия: треугольники": GEOM_GENS,
        "Теория вероятностей": PROB_GENS,
    },
    "10": {
        "Тригонометрия": TRIG_GENS,
        "Логарифмы": LOG_GENS,
        "Показательные уравнения": EXP_GENS,
        "Геометрия: окружности": CIRCLE_GENS,
        "Теория вероятностей": PROB_GENS,
    },
    "11": {
        "Производная": DERIV_GENS,
        "Первообразная": INT_GENS,
        "Логарифмы": LOG_GENS,
        "Тригонометрия": TRIG_GENS,
        "Геометрия: треугольники": GEOM_GENS,
        "Комбинаторика и вероятность": PROB_GENS,
        "Объёмы тел": VOL_GENS,
    }
}

# ---------- ТЕОРИЯ ----------
THEORY = {
    ("9", "Квадратные уравнения"): """
Квадратное уравнение: ax² + bx + c = 0, a ≠ 0
Дискриминант: D = b² – 4ac
Если D > 0: два корня x₁,₂ = (–b ± √D) / (2a)
Если D = 0: один корень x = –b / (2a)
Если D < 0: действительных корней нет
Теорема Виета: x₁ + x₂ = –b/a,  x₁·x₂ = c/a

📘 Пример 1: x² – 5x + 6 = 0
По Виету: x₁ + x₂ = 5, x₁·x₂ = 6 → x₁=2, x₂=3

📘 Пример 2: 2x² – 7x + 3 = 0
D = 49 – 24 = 25, √D = 5
x₁ = (7+5)/4 = 3, x₂ = (7-5)/4 = 0.5

📘 Пример 3: x² + 2x + 5 = 0
D = 4 – 20 = –16 < 0 → корней нет
""",
    ("9", "Арифметическая прогрессия"): """
Арифметическая прогрессия: aₙ = a₁ + (n-1)d
Разность прогрессии d = aₙ₊₁ – aₙ
Сумма n первых членов: Sₙ = (2a₁ + (n-1)d)·n/2 = (a₁ + aₙ)·n/2

📘 Пример 1: a₁=3, d=4. Найти a₇.
a₇ = 3 + 6·4 = 27

📘 Пример 2: a₁=5, d=2. Найти сумму первых 10 членов.
S₁₀ = (2·5 + 9·2)·10/2 = (10+18)·5 = 140

📘 Пример 3: a₁=10, a₅=30. Найдите d.
a₅ = a₁ + 4d → 30 = 10 + 4d → d = 5
""",
    ("9", "Геометрическая прогрессия"): """
Геометрическая прогрессия: bₙ = b₁ · qⁿ⁻¹
Знаменатель q = bₙ₊₁ / bₙ
Сумма n первых членов: Sₙ = b₁(1 – qⁿ)/(1 – q), если q ≠ 1

📘 Пример 1: b₁=2, q=3. Найти b₄.
b₄ = 2 · 3³ = 54

📘 Пример 2: b₁=3, q=2. Найти сумму первых 5 членов.
S₅ = 3(1 – 2⁵)/(1 – 2) = 3(1 – 32)/(–1) = 93

📘 Пример 3: b₁=5, b₃=20. Найдите q.
b₃ = 5·q² = 20 → q² = 4, q = ±2
""",
    ("9", "Геометрия: треугольники"): """
Площадь треугольника: ½·a·h, формула Герона (если даны три стороны)
p = (a+b+c)/2, S = √(p(p-a)(p-b)(p-c))
Теорема Пифагора (для прямоуг. треугольников): c² = a² + b²

📘 Пример 1: стороны 3,4,5. Площадь?
p = (3+4+5)/2 = 6, S = √(6·3·2·1) = √36 = 6

📘 Пример 2: катеты 5 и 12. Гипотенуза?
c² = 25 + 144 = 169 → c = 13

📘 Пример 3: BC=7, AC=8, ∠C=60°. Площадь?
S = ½·7·8·sin60° = 28·√3/2 ≈ 24.25
""",
    ("9", "Теория вероятностей"): """
Вероятность события P(A) = m/n, где m – благоприятные исходы, n – все равновозможные.
Правило умножения: если события независимы, P(A∩B) = P(A)·P(B)
Сочетания: число способов выбрать k элементов из n: C(n,k) = n!/(k!(n-k)!)

📘 Пример 1: В урне 5 белых и 10 чёрных. Вероятность вытащить белый?
P = 5/15 = 1/3

📘 Пример 2: Бросают два кубика. Вероятность суммы 8?
Благоприятные: (2,6),(3,5),(4,4),(5,3),(6,2) – всего 5. Всего исходов 36. P = 5/36

📘 Пример 3: Сколькими способами выбрать 2 дежурных из 10?
C(10,2) = 10·9/2 = 45
""",
    ("10", "Тригонометрия"): """
Основные уравнения:
sin x = a → x = (-1)ⁿ arcsin a + πn, n∈Z
cos x = a → x = ± arccos a + 2πn, n∈Z
tg x = a → x = arctg a + πn, n∈Z
Частные случаи: sin x = 0 → x = πn; sin x = 1 → x = π/2 + 2πn; cos x = 1 → x = 2πn

📘 Пример 1: sin x = 1/2
x = (-1)ⁿ·π/6 + πn, n∈Z

📘 Пример 2: cos x = √2/2
x = ±π/4 + 2πn, n∈Z

📘 Пример 3: sin(2x) = 1/2
2x = (-1)ⁿ·π/6 + πn → x = (-1)ⁿ·π/12 + πn/2, n∈Z
""",
    ("10", "Логарифмы"): """
logₐ(b) = x ⇔ aˣ = b
Свойства: logₐ(xy) = logₐx + logₐy
logₐ(x/y) = logₐx – logₐy
logₐ(xᵖ) = p·logₐx

📘 Пример 1: log₂8 = 3, так как 2³ = 8
📘 Пример 2: log₃(1/9) = –2, так как 3⁻² = 1/9
📘 Пример 3: log₂4 + log₂8 = 2 + 3 = 5
""",
    ("10", "Показательные уравнения"): """
Показательное уравнение: aˣ = b, решается логарифмированием или приведением к одному основанию.
Если aˣ = aᵐ, то x = m

📘 Пример 1: 2ˣ = 16 → x = 4
📘 Пример 2: 5²ˣ = 125 → 5²ˣ = 5³ → 2x = 3 → x = 1.5
📘 Пример 3: 3ˣ⁺¹ = 9ˣ → 3ˣ⁺¹ = 3²ˣ → x+1 = 2x → x = 1
""",
    ("10", "Геометрия: окружности"): """
Длина окружности: C = 2πR
Площадь круга: S = πR²
Центральный угол равен дуге в градусах.

📘 Пример 1: R=5 → C = 2π·5 ≈ 31.4
📘 Пример 2: R=3 → S = π·9 ≈ 28.27
📘 Пример 3: Длина окружности 62.8. Найдите радиус: R = 62.8/(2π) ≈ 10
""",
    ("10", "Теория вероятностей"): """(см. также теорию для 9 класса)
Условная вероятность: P(A|B) = P(A∩B)/P(B)
Формула полной вероятности.

📘 Пример 1: В коробке 3 белых и 7 чёрных, вынимают два шара подряд. Вероятность двух белых?
P = 3/10 · 2/9 = 6/90 = 1/15 ≈ 0.067

📘 Пример 2: Бросают монету дважды. Вероятность хотя бы одного орла?
P(хотя бы один) = 1 – P(оба решки) = 1 – 1/4 = 3/4
""",
    ("11", "Производная"): """
Производная функции f'(x) – скорость изменения функции.
Правила:
(xⁿ)' = n·xⁿ⁻¹
(sin x)' = cos x, (cos x)' = –sin x
(eˣ)' = eˣ, (ln x)' = 1/x
Производная суммы: (u+v)' = u' + v'

📘 Пример 1: f(x) = x³ + 2x² – 5x + 1
f'(x) = 3x² + 4x – 5

📘 Пример 2: f(x) = sin(3x) → f'(x) = 3·cos(3x)
📘 Пример 3: f(x) = e²ˣ + ln(5x) → f'(x) = 2e²ˣ + 1/x
""",
    ("11", "Первообразная"): """
Первообразная F(x) функции f(x): F'(x) = f(x).
Основные формулы:
∫ xⁿ dx = xⁿ⁺¹/(n+1) + C
∫ sin x dx = –cos x + C
∫ eˣ dx = eˣ + C
Определённый интеграл: ∫ₐᵇ f(x)dx = F(b) – F(a)

📘 Пример 1: ∫ 3x² dx = x³ + C
📘 Пример 2: ∫ sin x dx = –cos x + C
📘 Пример 3: ∫₀¹ 2x dx = [x²]₀¹ = 1 – 0 = 1
""",
    ("11", "Логарифмы"): """(см. также логарифмы 10 класса)""",
    ("11", "Тригонометрия"): """(см. также тригонометрию 10 класса)""",
    ("11", "Геометрия: треугольники"): """(см. также геометрию 9 класса)""",
    ("11", "Комбинаторика и вероятность"): """
Перестановки: n!
Размещения: Aₙᵏ = n!/(n–k)!
Сочетания: Cₙᵏ = n!/(k!(n–k)!)
Классическая вероятность: P = благоприятные / все

📘 Пример 1: Сколькими способами можно рассадить 4 человек? 4! = 24
📘 Пример 2: Сколькими способами выбрать 2 детали из 10? C(10,2)=45
📘 Пример 3: Бросают два кубика. Вероятность суммы 7? 6/36 = 1/6
""",
    ("11", "Объёмы тел"): """
Объём призмы: V = Sосн · h
Объём цилиндра: V = πR²h
Объём шара: V = 4/3 πR³

📘 Пример 1: Цилиндр с R=2, h=5 → V = π·4·5 ≈ 62.8
📘 Пример 2: Шар R=3 → V = 4/3 π·27 ≈ 113.1
📘 Пример 3: Призма с основанием 10 см² и высотой 4 см → V = 40 см³
""",
}

# ---------- КЛАСС PDF ----------
class PDF(FPDF):
    def __init__(self):
        super().__init__('P', 'mm', 'A4')
        font_path = os.path.join('fonts', 'DejaVuSans.ttf')
        self.add_font('DejaVu', '', font_path, uni=True)
        self.add_font('DejaVu', 'B', font_path, uni=True)
        self.set_auto_page_break(False)

    def dashed_line(self, x1, y1, x2, y2, dash=2, space=1.5):
        if x1 == x2:
            length = y2 - y1
            steps = int(length / (dash + space))
            for i in range(steps):
                y = y1 + i*(dash+space)
                self.line(x1, y, x2, min(y+dash, y2))
        elif y1 == y2:
            length = x2 - x1
            steps = int(length / (dash + space))
            for i in range(steps):
                x = x1 + i*(dash+space)
                self.line(x, y1, min(x+dash, x2), y2)
        else:
            self.line(x1, y1, x2, y2)

    def draw_triangle_heron(self, x, y, w, h, a, b, c):
        self.set_line_width(0.4)
        pts = [(x+w/2, y+2), (x+3, y+h-5), (x+w-3, y+h-5)]
        self.polygon(pts, style='D')
        self.set_font('DejaVu', '', 7)
        self.text(x+w/2-1, y-1, 'C')
        self.text(x-2, y+h-2, 'A')
        self.text(x+w-2, y+h-2, 'B')
        self.text(x+w/4, y+h/2+2, str(a))
        self.text(x+3*w/4-4, y+h/2+2, str(b))
        self.text(x+w/2-2, y+h-8, str(c))

    def draw_triangle_right(self, x, y, w, h, leg1, leg2):
        self.set_line_width(0.4)
        pts = [(x+3, y+h-5), (x+3, y+3), (x+w-3, y+h-5)]
        self.polygon(pts, style='D')
        self.set_font('DejaVu', '', 7)
        self.text(x+1, y+h-1, 'A')
        self.text(x+w-2, y+h-1, 'B')
        self.text(x+1, y-1, 'C')
        self.text(x+w/2-4, y+h-8, str(leg1))
        self.text(x-2, y+h/2, str(leg2))
        self.text(x+w/2+2, y+h/2, '?')

    def write_theory(self, text):
        for line in text.strip().split('\n'):
            line = line.rstrip()
            if line.startswith('📘'):
                self.ln(2)
                self.set_font('DejaVu', 'B', 9)
                self.cell(0, 5, line)
                self.ln(5)
                self.set_font('DejaVu', '', 8)
            else:
                self.set_font('DejaVu', '', 8)
                self.multi_cell(0, 4.5, line)
                # multi_cell уже делает ln, не дублируем
        self.ln(5)

def add_footer(pdf):
    pdf.ln(5)
    pdf.set_font('DejaVu', 'B', 10)
    pdf.cell(0, 8, 'Готовься к ЕГЭ с ПРОФМАТ!', align='C')
    pdf.ln(6)
    pdf.set_font('DejaVu', '', 7)
    pdf.cell(0, 5, 'Удачи на экзамене!', align='C')

# ---------- ГЕНЕРАЦИЯ PDF (задания) ----------
def generate_pdf(grade, topic, variants, problems, per_row, with_answers):
    gens = GRADE_TOPICS[grade][topic]
    vars_problems = []
    vars_answers = []
    for v in range(variants):
        shuffled = shuffle(gens)
        vp = []
        va = []
        for p in range(problems):
            gen = shuffled[p % len(shuffled)]
            res = gen()
            vp.append(res)
            va.append(res.get('answer', ''))
        vars_problems.append(vp)
        vars_answers.append(va)

    pdf = PDF()
    pdf.set_margin(5)
    card_w = 92 if per_row == 2 else 190
    card_h = 95

    pdf.add_page()
    for idx in range(variants):
        row = idx // per_row
        col = idx % per_row
        x0 = 10 + col * (card_w + 6)
        y0 = 10 + row * (card_h + 8)

        if y0 + card_h > 270:
            pdf.add_page()
            y0 = 10
            row = 0

        # Рамка карточки
        pdf.dashed_line(x0, y0, x0+card_w, y0)
        pdf.dashed_line(x0+card_w, y0, x0+card_w, y0+card_h)
        pdf.dashed_line(x0+card_w, y0+card_h, x0, y0+card_h)
        pdf.dashed_line(x0, y0+card_h, x0, y0)

        # Заголовок
        pdf.set_font('DejaVu', 'B', 9)
        pdf.set_xy(x0, y0+1)
        pdf.cell(card_w, 5, f'Вариант {idx+1}', align='C')
        pdf.set_font('DejaVu', '', 6)
        pdf.set_xy(x0+2, y0+8)
        pdf.cell(card_w-4, 3, 'Фамилия, Имя ___________________')
        pdf.set_xy(x0+2, y0+12)
        pdf.cell(card_w-4, 3, 'Класс _______  Дата ___________')

        y_text = y0 + 18
        for p_idx, prob in enumerate(vars_problems[idx]):
            pdf.set_font('DejaVu', '', 7)
            if 'draw' in prob and prob['draw'] == 'heron':
                pdf.draw_triangle_heron(x0+card_w-30, y_text, 28, 20, prob['a'], prob['b'], prob['c'])
            elif 'draw' in prob and prob['draw'] == 'pythag':
                pdf.draw_triangle_right(x0+card_w-30, y_text, 28, 20, prob['a'], prob['b'])
            pdf.set_xy(x0+2, y_text)
            pdf.multi_cell(card_w-6, 3.5, f'{p_idx+1}. {prob["text"]}')
            y_text = pdf.get_y() + 1

        if col < per_row-1:
            pdf.dashed_line(x0+card_w+3, y0, x0+card_w+3, y0+card_h)

    # Ответы
    if with_answers:
        pdf.add_page()
        pdf.set_font('DejaVu', 'B', 10)
        pdf.cell(0, 8, f'Ответы – {topic}', align='C')
        pdf.ln(10)
        pdf.set_font('DejaVu', '', 7)
        for v in range(variants):
            pdf.cell(0, 5, f'Вариант {v+1}:', new_x=XPos.LMARGIN, new_y=YPos.NEXT)
            for p in range(problems):
                pdf.cell(0, 4, f'{p+1}) {vars_answers[v][p]}', new_x=XPos.LMARGIN, new_y=YPos.NEXT)
            pdf.ln(3)

    path = os.path.join(TEMP_DIR, f'kr_{grade}_{topic}.pdf')
    pdf.output(path)
    return path

# ---------- ГЕНЕРАЦИЯ PDF (теория) ----------
def generate_theory_pdf(grade, topic):
    pdf = PDF()
    pdf.add_page()
    pdf.set_font('DejaVu', 'B', 14)
    pdf.cell(0, 10, f'Теория: {topic}', align='C')
    pdf.ln(6)
    pdf.set_font('DejaVu', '', 8)
    pdf.cell(0, 5, f'{grade} класс', align='C')
    pdf.ln(8)

    theory_text = THEORY.get((grade, topic), "Теория пока не добавлена.")
    pdf.write_theory(theory_text)

    add_footer(pdf)

    path = os.path.join(TEMP_DIR, f'theory_{grade}_{topic}.pdf')
    pdf.output(path)
    return path

# ---------- СОСТОЯНИЯ ----------
class MainMenu(StatesGroup):
    choose = State()

class GenForm(StatesGroup):
    grade = State()
    topic = State()
    variants = State()
    problems = State()
    per_row = State()
    answers = State()

class TheoryForm(StatesGroup):
    grade = State()
    topic = State()

# ---------- ОБРАБОТЧИКИ ----------
@dp.message(Command("start"))
async def start(message: types.Message, state: FSMContext):
    await state.clear()
    kb = [
        [types.KeyboardButton(text="📝 Задания"), types.KeyboardButton(text="📚 Теория")]
    ]
    await message.answer("👋 Выберите раздел:", reply_markup=types.ReplyKeyboardMarkup(keyboard=kb, resize_keyboard=True))
    await state.set_state(MainMenu.choose)

# Задания
@dp.message(MainMenu.choose, F.text == "📝 Задания")
async def tasks_menu(message: types.Message, state: FSMContext):
    await state.clear()
    kb = [[types.KeyboardButton(text="9 класс"), types.KeyboardButton(text="10 класс"), types.KeyboardButton(text="11 класс")]]
    await message.answer("👋 Выберите класс:", reply_markup=types.ReplyKeyboardMarkup(keyboard=kb, resize_keyboard=True))
    await state.set_state(GenForm.grade)

@dp.message(GenForm.grade, F.text.in_(["9 класс", "10 класс", "11 класс"]))
async def set_grade(message: types.Message, state: FSMContext):
    grade = message.text.split()[0]
    await state.update_data(grade=grade)
    topics = list(GRADE_TOPICS[grade].keys())
    kb = [[types.KeyboardButton(text=t)] for t in topics]
    kb.append([types.KeyboardButton(text="⬅️ Назад")])
    await message.answer("📚 Выберите тему:", reply_markup=types.ReplyKeyboardMarkup(keyboard=kb, resize_keyboard=True))
    await state.set_state(GenForm.topic)

@dp.message(GenForm.topic, F.text.in_(sum([list(GRADE_TOPICS[g].keys()) for g in GRADE_TOPICS], [])))
async def set_topic(message: types.Message, state: FSMContext):
    await state.update_data(topic=message.text)
    await message.answer("📋 Сколько вариантов? (введите число от 1 до 8)", reply_markup=types.ReplyKeyboardRemove())
    await state.set_state(GenForm.variants)

@dp.message(GenForm.variants)
async def set_variants(message: types.Message, state: FSMContext):
    if not message.text.isdigit() or not (1 <= int(message.text) <= 8):
        return await message.answer("Введите число от 1 до 8.")
    await state.update_data(variants=int(message.text))
    await message.answer("📝 Сколько заданий в варианте? (1–12)")
    await state.set_state(GenForm.problems)

@dp.message(GenForm.problems)
async def set_problems(message: types.Message, state: FSMContext):
    if not message.text.isdigit() or not (1 <= int(message.text) <= 12):
        return await message.answer("Введите число от 1 до 12.")
    await state.update_data(problems=int(message.text))
    kb = [[types.KeyboardButton(text="2 в ряд"), types.KeyboardButton(text="1 в ряд")]]
    await message.answer("📄 Расположение вариантов:", reply_markup=types.ReplyKeyboardMarkup(keyboard=kb, resize_keyboard=True))
    await state.set_state(GenForm.per_row)

@dp.message(GenForm.per_row, F.text.in_(["2 в ряд", "1 в ряд"]))
async def set_per_row(message: types.Message, state: FSMContext):
    per_row = 2 if message.text == "2 в ряд" else 1
    await state.update_data(per_row=per_row)
    kb = [[types.KeyboardButton(text="Да"), types.KeyboardButton(text="Нет")]]
    await message.answer("✅ Включить ответы?", reply_markup=types.ReplyKeyboardMarkup(keyboard=kb, resize_keyboard=True))
    await state.set_state(GenForm.answers)

@dp.message(GenForm.answers, F.text.in_(["Да", "Нет"]))
async def set_answers(message: types.Message, state: FSMContext):
    with_answers = message.text == "Да"
    data = await state.get_data()
    await state.clear()
    await message.answer("⏳ Генерирую контрольную...")
    try:
        pdf_path = generate_pdf(data['grade'], data['topic'], data['variants'], data['problems'], data['per_row'], with_answers)
        await message.answer_document(FSInputFile(pdf_path), caption="✅ Контрольная готова! Можно печатать.")
        os.remove(pdf_path)
    except Exception as e:
        logging.error(e)
        await message.answer("⚠️ Ошибка генерации.")
    finally:
        await message.answer("Для новой работы нажмите /start", reply_markup=types.ReplyKeyboardRemove())

# Теория
@dp.message(MainMenu.choose, F.text == "📚 Теория")
async def theory_menu(message: types.Message, state: FSMContext):
    await state.clear()
    kb = [[types.KeyboardButton(text="9 класс"), types.KeyboardButton(text="10 класс"), types.KeyboardButton(text="11 класс")]]
    await message.answer("🎓 Выберите класс для теории:", reply_markup=types.ReplyKeyboardMarkup(keyboard=kb, resize_keyboard=True))
    await state.set_state(TheoryForm.grade)

@dp.message(TheoryForm.grade, F.text.in_(["9 класс", "10 класс", "11 класс"]))
async def theory_grade(message: types.Message, state: FSMContext):
    grade = message.text.split()[0]
    await state.update_data(grade=grade)
    topics = list(GRADE_TOPICS[grade].keys())
    kb = [[types.KeyboardButton(text=t)] for t in topics]
    kb.append([types.KeyboardButton(text="⬅️ Назад")])
    await message.answer("📚 Выберите тему:", reply_markup=types.ReplyKeyboardMarkup(keyboard=kb, resize_keyboard=True))
    await state.set_state(TheoryForm.topic)

@dp.message(TheoryForm.topic, F.text.in_(sum([list(GRADE_TOPICS[g].keys()) for g in GRADE_TOPICS], [])))
async def theory_topic(message: types.Message, state: FSMContext):
    topic = message.text
    data = await state.get_data()
    grade = data['grade']
    await state.clear()
    await message.answer("⏳ Готовлю теорию...")
    try:
        pdf_path = generate_theory_pdf(grade, topic)
        await message.answer_document(FSInputFile(pdf_path), caption="✅ Теория готова!")
        os.remove(pdf_path)
    except Exception as e:
        logging.error(e)
        await message.answer("⚠️ Ошибка генерации теории.")
    finally:
        await message.answer("Для возврата нажмите /start", reply_markup=types.ReplyKeyboardRemove())

# Кнопка Назад
@dp.message(F.text == "⬅️ Назад")
async def back_to_menu(message: types.Message, state: FSMContext):
    await state.clear()
    await start(message, state)

# Быстрая команда
@dp.message(Command("quick"))
async def quick_gen(message: types.Message, state: FSMContext):
    try:
        parts = message.text.split()
        if len(parts) != 7:
            raise ValueError
        grade = parts[1]
        topic = parts[2]
        variants = int(parts[3])
        problems = int(parts[4])
        per_row = int(parts[5])
        with_answers = parts[6].lower() == 'да'
        if grade not in GRADE_TOPICS or topic not in GRADE_TOPICS[grade]:
            return await message.answer("Неверный класс или тема.")
        pdf_path = generate_pdf(grade, topic, variants, problems, per_row, with_answers)
        await message.answer_document(FSInputFile(pdf_path), caption="✅ Готово!")
        os.remove(pdf_path)
    except:
        await message.answer("Формат: /quick класс тема варианты задачи в_ряд ответы(да/нет)\nПример: /quick 11 Логарифмы 4 6 2 да")

async def main():
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
