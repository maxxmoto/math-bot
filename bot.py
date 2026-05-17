# bot.py
import os
import asyncio
import logging
import random
import math
import urllib.request
from aiogram import Bot, Dispatcher, types, F
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.context import FSMContext
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import FSInputFile, ReplyKeyboardMarkup, KeyboardButton
from aiogram.filters import Command
from fpdf import FPDF
from fpdf.enums import XPos, YPos

# ---------- АВТОСКАЧИВАНИЕ ШРИФТА ----------
FONTS_DIR = "fonts"
FONT_PATH = os.path.join(FONTS_DIR, "DejaVuSans.ttf")
if not os.path.exists(FONT_PATH):
    os.makedirs(FONTS_DIR, exist_ok=True)
    print("Скачиваю шрифт DejaVuSans.ttf...")
    url = "https://github.com/dejavu-fonts/dejavu-fonts/raw/master/ttf/DejaVuSans.ttf"
    urllib.request.urlretrieve(url, FONT_PATH)
    print("Шрифт скачан.")

# ---------- НАСТРОЙКИ ----------
TOKEN = "8755532322:AAFnYy-VY4MRh4E3DyzcB5zSaarQvXQjuSA"          # ← замените на реальный токен
TEMP_DIR = "temp_pdf"
MATH_DIR = "."                   # папка с теорией
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

# ---------- UNICODE-ИНДЕКСЫ ----------
SUPER = str.maketrans("0123456789", "⁰¹²³⁴⁵⁶⁷⁸⁹")
SUB   = str.maketrans("0123456789", "₀₁₂₃₄₅₆₇₈₉")

def super_num(n: int) -> str:
    return str(n).translate(SUPER)

def sub_num(n: int) -> str:
    return str(n).translate(SUB)

def sub_s(s: str) -> str:
    return s.translate(SUB)

# ---------- ГЕНЕРАТОРЫ ЗАДАЧ (старые) ----------
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

GRADE_TOPICS = {
    "9": {
        "Квадратные уравнения": [
            lambda: {"text": f"Решите: x{super_num(2)} + {randint(-5,5)}x + {randint(-5,5)} = 0", "answer": "x₁,₂ = ..."}
        ],
        "Арифметическая прогрессия": ARITH_GENS,
        "Геометрическая прогрессия": GEOM_PROG_GENS,
        "Геометрия: треугольники": GEOM_GENS,
        "Теория вероятностей": PROB_GENS,
    },
    "10": {
        "Тригонометрия": TRIG_GENS,
        "Логарифмы": LOG_GENS,
        "Показательные уравнения": [
            lambda: {"text": f"Решите: {randchoice([2,3,5])}{super_num('x')} = {randchoice([4,8,9,16])}", "answer": "x = ..."}
        ],
        "Геометрия: окружности": [
            lambda: {"text": f"Найдите длину окружности радиуса {randint(3,8)}.", "answer": "2πr ≈ ..."}
        ],
        "Теория вероятностей": PROB_GENS,
    },
    "11": {
        "Производная": DERIV_GENS,
        "Первообразная": INT_GENS,
        "Логарифмы": LOG_GENS,
        "Тригонометрия": TRIG_GENS,
        "Геометрия: треугольники": GEOM_GENS,
        "Комбинаторика и вероятность": PROB_GENS,
        "Объёмы тел": [
            lambda: {"text": f"Объём цилиндра: r={randint(2,5)} см, h={randint(4,10)} см.", "answer": f"V = πr²h ≈ ..."}
        ]
    }
}

# ---------- БАНК ЗАДАЧ ЕГЭ (прототипы) ----------
PROBLEM_BANK = {
    1: [
        {"text": "В треугольнике ABC угол A равен 42°, угол C равен 108°. Найдите угол B. Ответ дайте в градусах.", "answer": "30"},
        {"text": "В треугольнике ABC известно, что AC = BC, AB = 12, cos A = 0,8. Найдите высоту CH.", "answer": "9.6"},
        {"text": "Площадь треугольника равна 36, а радиус вписанной окружности равен 3. Найдите периметр треугольника.", "answer": "24"},
        {"text": "В треугольнике ABC сторона AB = 10, BC = 12, sin B = 0,6. Найдите площадь треугольника.", "answer": "36"},
        {"text": "Около окружности радиусом 2 описан прямоугольный треугольник, гипотенуза которого равна 5. Найдите площадь этого треугольника.", "answer": "6"},
        {"text": "В параллелограмме ABCD стороны AB = 6, AD = 8, sin угла A равен 0,5. Найдите площадь параллелограмма.", "answer": "24"},
    ],
    2: [
        {"text": "Даны векторы a⃗(2;−3) и b⃗(−4;5). Найдите скалярное произведение a⃗ · b⃗.", "answer": "-23"},
        {"text": "Найдите длину вектора c⃗ = a⃗ + 2b⃗, если a⃗(1;2), b⃗(−1;3).", "answer": "√65"},
        {"text": "Даны точки A(1;2) и B(7;10). Найдите квадрат длины отрезка AB.", "answer": "100"},
        {"text": "Векторы a⃗(−2;x) и b⃗(6;−9) коллинеарны. Найдите x.", "answer": "3"},
        {"text": "Найдите косинус угла между векторами a⃗(3;4) и b⃗(5;−12).", "answer": "-33/65"},
    ],
    3: [
        {"text": "Объём цилиндра равен 45π, а площадь боковой поверхности равна 30π. Найдите высоту цилиндра.", "answer": "6"},
        {"text": "Шар вписан в цилиндр, высота которого равна 10. Найдите объём шара, делённый на π.", "answer": "500/3"},
        {"text": "В прямоугольном параллелепипеде рёбра равны 3, 4 и 12. Найдите квадрат диагонали.", "answer": "169"},
        {"text": "Конус и цилиндр имеют общее основание и общую высоту. Объём цилиндра равен 60. Найдите объём конуса.", "answer": "20"},
        {"text": "В правильной треугольной призме сторона основания равна 6, а боковое ребро равно 8. Найдите объём призмы.", "answer": "72√3"},
        {"text": "Площадь поверхности шара равна 100π. Найдите его радиус.", "answer": "5"},
    ],
    4: [
        {"text": "В коробке 12 шоколадных конфет и 8 карамелек. Наугад берут одну конфету. Какова вероятность того, что она шоколадная?", "answer": "0.6"},
        {"text": "Игральный кубик бросают дважды. Найдите вероятность того, что сумма выпавших очков равна 7.", "answer": "0.1667"},
        {"text": "В лотерее 1000 билетов, из них 20 выигрышных. Найдите вероятность проигрыша при покупке одного билета.", "answer": "0.98"},
        {"text": "Вероятность того, что батарейка бракованная, равна 0,03. Покупатель берёт две батарейки. Найдите вероятность того, что обе исправны.", "answer": "0.9409"},
        {"text": "В группе 25 студентов: 10 знают английский язык, 12 — немецкий, 5 — оба языка. Найдите вероятность того, что случайно выбранный студент знает хотя бы один из этих языков.", "answer": "0.68"},
    ],
    5: [
        {"text": "Стрелок попадает в мишень с вероятностью 0,7. Найдите вероятность того, что при трёх выстрелах он попадёт ровно два раза.", "answer": "0.441"},
        {"text": "Два станка работают независимо. Вероятность отказа первого равна 0,1, второго — 0,2. Найдите вероятность того, что оба станка откажут.", "answer": "0.02"},
        {"text": "В магазине три продавца. Вероятность того, что первый занят, равна 0,4, второй — 0,5, третий — 0,3. Найдите вероятность того, что все трое свободны одновременно (события независимы).", "answer": "0.21"},
        {"text": "Вероятность перегорания лампы в течение года равна 0,2. Найдите вероятность того, что из трёх ламп ни одна не перегорит в течение года.", "answer": "0.512"},
    ],
    6: [
        {"text": "Решите уравнение: log₂(x−1) + log₂(x+1) = 3. Если уравнение имеет более одного корня, в ответе запишите их сумму.", "answer": "5"},
        {"text": "Решите уравнение: 2^(x+1) + 2^(x−1) = 20.", "answer": "3"},
        {"text": "Решите уравнение: √(2x+5) = x+1. Если корней несколько, запишите больший из них.", "answer": "2"},
        {"text": "Решите уравнение: sin(πx/6) = 0,5. В ответе укажите наименьший положительный корень.", "answer": "1"},
        {"text": "Решите уравнение: lg(x²−17) = lg(5x−11).", "answer": "6"},
        {"text": "Решите уравнение: 9^x − 4·3^x + 3 = 0.", "answer": "0;1"},
    ],
    7: [
        {"text": "Найдите значение выражения: (√5−√2)² + 2√10.", "answer": "7"},
        {"text": "Вычислите: log₃54 − log₃2.", "answer": "3"},
        {"text": "Найдите sin 2α, если sin α = 0,6 и α ∈ (π/2; π).", "answer": "-0.96"},
        {"text": "Найдите значение выражения: (5^(log₅7))².", "answer": "49"},
        {"text": "Вычислите: 8^(2/3) + 27^(1/3).", "answer": "7"},
        {"text": "Найдите tg α, если cos α = −0,6 и sin α > 0.", "answer": "-4/3"},
    ],
    8: [
        {"text": "Найдите угловой коэффициент касательной к графику функции y = x³ − 2x² + 4 в точке x₀ = 1.", "answer": "-1"},
        {"text": "Материальная точка движется по закону s(t) = 2t³ − 3t² + 5 (м). Найдите её скорость в момент времени t = 2 с.", "answer": "12"},
        {"text": "На рисунке изображён график функции y = f(x) и касательная к нему в точке x₀ = 2. Касательная проходит через точки (2; 3) и (5; 9). Найдите f'(2).", "answer": "2"},
        {"text": "Найдите точку минимума функции y = x³ − 6x² + 9x + 2.", "answer": "3"},
        {"text": "Найдите наибольшее значение функции y = x³ − 3x² + 2 на отрезке [−1; 1].", "answer": "2"},
    ],
    9: [
        {"text": "Температура нагревательного прибора меняется по закону T(t) = 200 − 150e^(−0,3t), где t — время в минутах. Найдите начальную температуру прибора (при t = 0).", "answer": "50"},
        {"text": "Высота над землёй подброшенного вверх мяча меняется по закону h(t) = 12t − 5t² (м). Сколько секунд мяч будет находиться на высоте не менее 4 метров?", "answer": "1.6"},
        {"text": "Стоимость проезда в такси вычисляется по формуле C = 120 + 30t, где t — время поездки в минутах. Сколько рублей стоит поездка длительностью 15 минут?", "answer": "570"},
        {"text": "Мощность постоянного тока (в ваттах) вычисляется по формуле P = I²R, где I — сила тока в амперах, R — сопротивление в омах. Найдите мощность, если I = 4 А, R = 12 Ом.", "answer": "192"},
        {"text": "Период колебаний математического маятника приближённо вычисляется по формуле T = 2π√(l/g). Найдите длину нити маятника, если T = 2 с, g = 10 м/с², π ≈ 3,14.", "answer": "1.014"},
    ],
    10: [
        {"text": "Из пункта А в пункт В выехал автомобиль со скоростью 60 км/ч. Через 2 часа вслед за ним выехал второй автомобиль со скоростью 80 км/ч. Через сколько часов после своего выезда второй автомобиль догонит первый?", "answer": "6"},
        {"text": "Два насоса, работая вместе, наполняют бассейн за 8 часов. Первый насос, работая отдельно, наполняет бассейн за 12 часов. За сколько часов наполнит бассейн второй насос, работая один?", "answer": "24"},
        {"text": "Смешали 3 литра 10-процентного водного раствора соли и 2 литра 25-процентного раствора. Какова концентрация получившегося раствора? Ответ дайте в процентах.", "answer": "16"},
        {"text": "Поезд длиной 250 метров проезжает мимо столба за 12,5 секунд. Найдите скорость поезда в километрах в час.", "answer": "72"},
        {"text": "Катер прошёл 24 км по течению реки и 24 км против течения, затратив на весь путь 5 часов. Скорость течения реки равна 2 км/ч. Найдите собственную скорость катера (в км/ч).", "answer": "10"},
    ],
    11: [
        {"text": "На рисунке изображён график линейной функции, проходящей через точки (0;4) и (6;−2). Найдите значение этой функции при x = 3.", "answer": "1"},
        {"text": "График функции y = kx + b проходит через точки (−2;1) и (3;11). Найдите коэффициент k.", "answer": "2"},
        {"text": "На рисунке изображена парабола y = ax² + bx + c с вершиной в точке (2;3) и проходящая через точку (0;7). Найдите коэффициент a.", "answer": "1"},
        {"text": "График функции y = √x сдвинут вправо на 3 единицы и вверх на 2 единицы. Найдите значение полученной функции в точке x = 7.", "answer": "4"},
    ],
    12: [
        {"text": "Найдите точку минимума функции y = x³ − 3x² − 9x + 5.", "answer": "3"},
        {"text": "Найдите наибольшее значение функции y = −2x² + 8x − 3 на отрезке [0; 4].", "answer": "5"},
        {"text": "Найдите наименьшее значение функции y = x² − 4x + 7 на отрезке [0; 5].", "answer": "3"},
        {"text": "Найдите точку максимума функции y = −x³ + 3x² + 9x − 4 на отрезке [−2; 4].", "answer": "3"},
        {"text": "По графику производной f'(x) на интервале (−5;5) определено, что она имеет ровно три точки пересечения с осью Ox. Сколько целых точек экстремума имеет функция f(x) на этом интервале?", "answer": "3"},
    ],
    13: [
        {"text": "а) Решите уравнение 2sin²x + 3cos x = 0.\nб) Найдите все корни этого уравнения, принадлежащие отрезку [−π; π].", "answer": "±2π/3+2πk; -2π/3;2π/3"},
        {"text": "а) Решите уравнение 4ˣ − 3·2ˣ⁺¹ + 8 = 0.\nб) Укажите корни, принадлежащие отрезку [1;4].", "answer": "1;2; 1;2"},
    ],
    14: [
        {"text": "В правильной треугольной призме ABCA₁B₁C₁ сторона основания равна 4, боковое ребро равно 3. Найдите расстояние от вершины A₁ до прямой BC₁.", "answer": "√34"},
        {"text": "В кубе ABCDA₁B₁C₁D₁ с ребром 2 найдите расстояние от точки B до плоскости A₁C₁D.", "answer": "2√3/3"},
    ],
    15: [
        {"text": "Решите неравенство: log₂(x−1) ≤ 3 − log₂(x+1).", "answer": "(1;3]"},
        {"text": "Решите неравенство: (x² − 4)/(x+3) ≥ 0.", "answer": "(-∞;-3)∪[-2;2]"},
    ],
    16: [
        {"text": "Вкладчик положил в банк 200 000 рублей под 10% годовых. Проценты начисляются ежегодно и прибавляются к сумме вклада. Какую сумму он получит через 3 года? Ответ дайте в рублях.", "answer": "266200"},
        {"text": "Кредит в размере 1 000 000 рублей взят на 2 года под 20% годовых. Выплата происходит равными платежами ежегодно. Найдите размер ежегодного платежа.", "answer": "720000"},
        {"text": "Вкладчик разделил 500 000 рублей на две части и положил их в разные банки: первую часть под 8% годовых, вторую — под 12%. Через год общая сумма на обоих счетах составила 548 000 рублей. Какая сумма была положена под 12%?", "answer": "200000"},
        {"text": "Банк выдал кредит 600 000 рублей на 3 года под 15% годовых. Погашение происходит равными платежами ежегодно. Определите размер ежегодного платежа.", "answer": "270000"},
    ],
    17: [
        {"text": "В треугольнике ABC известно, что AB = 10, BC = 12, sin B = 0,8. Найдите длину медианы, проведённой к стороне AC.", "answer": "√73"},
        {"text": "Окружность радиуса 5 касается сторон угла с вершиной A. Расстояние от точки A до центра окружности равно 13. Найдите длину хорды, соединяющей точки касания.", "answer": "120/13"},
        {"text": "В трапеции ABCD с основаниями AD и BC, AD = 10, BC = 6, AB = CD = 5. Найдите площадь трапеции.", "answer": "24"},
    ],
    18: [
        {"text": "Найдите все значения a, при которых уравнение x² + (a+2)x + a + 5 = 0 имеет два различных корня, больших −1.", "answer": "(-5;-4)∪(-4;-3)"},
        {"text": "При каких значениях a неравенство ax² + 4x + a > 0 выполняется при всех действительных x?", "answer": "(2;+∞)"},
        {"text": "Найдите все значения a, при которых уравнение |x−2| + |x+3| = a имеет ровно два различных решения.", "answer": "(5;+∞)"},
        {"text": "При каких a система уравнений x²+y²=4, y=ax+1 имеет ровно два решения?", "answer": "(-√3/2; √3/2)"},
        {"text": "Найдите все a, при которых функция f(x)=x³−3a²x+2 убывает на отрезке [0;2].", "answer": "[2;+∞)"},
        {"text": "При каких значениях a уравнение sin x + a cos x = 2 имеет решения?", "answer": "[-√3;√3]"},
    ],
    19: [
        {"text": "Найдите все натуральные числа n, при которых число n² + 5n + 6 является простым.", "answer": "1"},
        {"text": "Найдите все трёхзначные числа, которые в 12 раз больше суммы своих цифр.", "answer": "108;180;270;360;450;540;630;720;810;900"},
        {"text": "Произведение двух последовательных натуральных чисел на 11 больше их суммы. Найдите эти числа.", "answer": "4;5"},
        {"text": "Найдите все пары целых чисел (x; y), для которых x² − y² = 21.", "answer": "(5;2),(5;-2),(-5;2),(-5;-2),(11;10),(11;-10),(-11;10),(-11;-10)"},
    ]
}

# ---------- КЛАСС PDF ----------
class PDF(FPDF):
    def __init__(self):
        super().__init__('P', 'mm', 'A4')
        font_path = os.path.join('fonts', 'DejaVuSans.ttf')
        if not os.path.exists(font_path):
            raise FileNotFoundError(f"Шрифт не найден: {font_path}.")
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

    def draw_grid(self, x, y, w, h, cols, rows):
        self.set_line_width(0.1)
        self.set_draw_color(180)
        for i in range(cols+1):
            self.line(x + i*w/cols, y, x + i*w/cols, y+h)
        for j in range(rows+1):
            self.line(x, y + j*h/rows, x+w, y + j*h/rows)

    # Заглушки для рисунков (можно оставить пустыми или убрать вызовы)
    def draw_triangle_heron(self, x, y, w, h, a, b, c):
        pass
    def draw_triangle_right(self, x, y, w, h, a, b):
        pass

# ---------- ГЕНЕРАЦИЯ PDF КОНТРОЛЬНОЙ ----------
def generate_pdf(grade: str, topic: str, variants: int, problems: int, per_row: int, with_answers: bool):
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
    card_w = (190 if per_row == 1 else 92)
    card_h = 95
    cols = per_row
    rows = (variants + cols - 1) // cols if cols else 1

    pdf.add_page()
    for idx in range(variants):
        row = idx // cols
        col = idx % cols
        x0 = 10 + col * (card_w + 6)
        y0 = 10 + row * (card_h + 8)
        if y0 + card_h > 280:
            pdf.add_page()
            y0 = 10
        pdf.dashed_line(x0, y0, x0+card_w, y0)
        pdf.dashed_line(x0+card_w, y0, x0+card_w, y0+card_h)
        pdf.dashed_line(x0+card_w, y0+card_h, x0, y0+card_h)
        pdf.dashed_line(x0, y0+card_h, x0, y0)
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
            pdf.set_xy(x0+2, y_text)
            if 'draw' in prob and prob['draw'] == 'heron':
                pdf.draw_triangle_heron(x0+card_w-30, y_text, 28, 20, prob['a'], prob['b'], prob['c'])
            elif 'draw' in prob and prob['draw'] == 'pythag':
                pdf.draw_triangle_right(x0+card_w-30, y_text, 28, 20, prob['a'], prob['b'])
            pdf.multi_cell(card_w-6, 3.5, f'{p_idx+1}. {prob["text"]}')
            y_text = pdf.get_y() + 1
        if col < cols-1:
            pdf.dashed_line(x0+card_w+3, y0, x0+card_w+3, y0+card_h)
        if row < rows-1:
            pdf.dashed_line(x0, y0+card_h+3, x0+card_w, y0+card_h+3)

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

# ---------- ГЕНЕРАЦИЯ PDF ВАРИАНТОВ ЕГЭ ----------
def generate_ege_variants_pdf(num_variants):
    pdf = PDF()
    pdf.set_margin(10)
    # Титул
    pdf.add_page()
    pdf.set_font('DejaVu', 'B', 16)
    pdf.cell(0, 10, 'Создано сообществом ПРОФМАТ', align='C', new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    pdf.ln(5)
    pdf.set_font('DejaVu', 'B', 14)
    pdf.cell(0, 8, 'ЕДИНЫЙ ГОСУДАРСТВЕННЫЙ ЭКЗАМЕН', align='C', new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    pdf.set_font('DejaVu', 'B', 12)
    pdf.cell(0, 8, 'ПО МАТЕМАТИКЕ (профильный уровень)', align='C', new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    pdf.ln(10)
    pdf.set_font('DejaVu', '', 10)
    pdf.cell(0, 6, f'Количество вариантов: {num_variants}', align='C', new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    pdf.ln(15)
    pdf.set_font('DejaVu', '', 8)
    pdf.multi_cell(0, 4, 'Ответы к заданиям 1–12 записываются в бланк ответов №1. Задания 13–19 требуют полного решения (бланк ответов №2).')
    # Инструкция и справочные
    pdf.add_page()
    pdf.set_font('DejaVu', 'B', 10)
    pdf.cell(0, 6, 'Инструкция по выполнению работы', new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    pdf.set_font('DejaVu', '', 8)
    pdf.multi_cell(0, 4, 'На выполнение работы отводится 3 часа 55 минут. Работа состоит из двух частей, включающих 19 заданий. Часть 1 содержит 12 заданий с кратким ответом. Часть 2 содержит 7 заданий с развёрнутым ответом.')
    pdf.ln(3)
    pdf.set_font('DejaVu', 'B', 10)
    pdf.cell(0, 6, 'Справочные материалы', new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    pdf.set_font('DejaVu', '', 8)
    pdf.cell(0, 4, 'Алгебра:', new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    pdf.multi_cell(0, 3.5, 'a⁰=1 (a≠0); a⁻ⁿ=1/aⁿ; aᵐ/ⁿ=ⁿ√aᵐ; logₐ1=0; logₐa=1; logₐ(xy)=logₐx+logₐy; logₐ(x/y)=logₐx-logₐy; logₐxᵏ=k logₐx; (a±b)²=a²±2ab+b²; a²-b²=(a-b)(a+b)')
    pdf.ln(2)
    pdf.cell(0, 4, 'Тригонометрия:', new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    pdf.multi_cell(0, 3.5, 'sin²α+cos²α=1; tgα=sinα/cosα; ctgα=cosα/sinα; sin(α±β)=sinα cosβ ± cosα sinβ; cos(α±β)=cosα cosβ ∓ sinα sinβ; sin2α=2sinα cosα; cos2α=cos²α-sin²α=2cos²α-1=1-2sin²α')
    pdf.ln(2)
    pdf.cell(0, 4, 'Таблица значений:', new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    col_w = 18
    row_h = 5
    angles = ['0°','30°','45°','60°','90°','180°','270°','360°']
    sin_vals = ['0','1/2','√2/2','√3/2','1','0','-1','0']
    cos_vals = ['1','√3/2','√2/2','1/2','0','-1','0','1']
    tg_vals = ['0','√3/3','1','√3','—','0','—','0']
    pdf.set_font('DejaVu', 'B', 7)
    pdf.cell(col_w, row_h, 'α', border=1, align='C')
    for a in angles: pdf.cell(col_w, row_h, a, border=1, align='C')
    pdf.ln()
    pdf.set_font('DejaVu', '', 7)
    pdf.cell(col_w, row_h, 'sin', border=1, align='C')
    for v in sin_vals: pdf.cell(col_w, row_h, v, border=1, align='C')
    pdf.ln()
    pdf.cell(col_w, row_h, 'cos', border=1, align='C')
    for v in cos_vals: pdf.cell(col_w, row_h, v, border=1, align='C')
    pdf.ln()
    pdf.cell(col_w, row_h, 'tg', border=1, align='C')
    for v in tg_vals: pdf.cell(col_w, row_h, v, border=1, align='C')
    pdf.ln(5)

    all_tasks = []
    for var_idx in range(num_variants):
        tasks = []
        for num in range(1, 20):
            tasks.append(random.choice(PROBLEM_BANK[num]))
        all_tasks.append(tasks)

        pdf.add_page()
        pdf.set_font('DejaVu', 'B', 10)
        pdf.cell(0, 6, f'Вариант {var_idx+1}', align='C', new_x=XPos.LMARGIN, new_y=YPos.NEXT)
        pdf.ln(3)
        pdf.set_font('DejaVu', 'B', 9)
        pdf.cell(0, 5, 'Часть 1', new_x=XPos.LMARGIN, new_y=YPos.NEXT)
        pdf.set_font('DejaVu', '', 8)
        for i in range(12):
            task = tasks[i]
            pdf.cell(8, 4, f'{i+1}.', new_x=XPos.RIGHT, new_y=YPos.TOP)
            pdf.multi_cell(170, 4, task['text'])
            pdf.ln(1)
        pdf.ln(2)
        pdf.set_font('DejaVu', 'B', 9)
        pdf.cell(0, 5, 'Часть 2', new_x=XPos.LMARGIN, new_y=YPos.NEXT)
        pdf.set_font('DejaVu', '', 8)
        for i in range(12, 19):
            task = tasks[i]
            pdf.cell(8, 4, f'{i+1}.', new_x=XPos.RIGHT, new_y=YPos.TOP)
            pdf.multi_cell(170, 4, task['text'])
            pdf.ln(1)

        # Бланк ответов №1
        pdf.add_page()
        pdf.set_font('DejaVu', 'B', 9)
        pdf.cell(0, 6, 'Бланк ответов №1', align='C', new_x=XPos.LMARGIN, new_y=YPos.NEXT)
        pdf.ln(3)
        pdf.set_font('DejaVu', '', 7)
        pdf.cell(20, 5, 'Регион:', border=1)
        pdf.cell(50, 5, '____________', border=1)
        pdf.ln()
        pdf.cell(20, 5, 'Предмет:', border=1)
        pdf.cell(50, 5, 'Математика (профиль)', border=1)
        pdf.ln()
        pdf.cell(20, 5, 'Вариант:', border=1)
        pdf.cell(50, 5, f'{var_idx+1}', border=1)
        pdf.ln(5)
        pdf.set_font('DejaVu', 'B', 8)
        pdf.cell(10, 6, '№', border=1, align='C')
        pdf.cell(80, 6, 'Ответ', border=1, align='C')
        pdf.ln()
        pdf.set_font('DejaVu', '', 8)
        for i in range(1, 13):
            pdf.cell(10, 8, str(i), border=1, align='C')
            pdf.cell(80, 8, '', border=1)
            pdf.ln()

        # Бланки ответов №2
        for b in [1, 2]:
            pdf.add_page()
            pdf.set_font('DejaVu', 'B', 9)
            pdf.cell(0, 6, f'Бланк ответов №2 (лист {b})', align='C', new_x=XPos.LMARGIN, new_y=YPos.NEXT)
            pdf.ln(3)
            pdf.draw_grid(10, pdf.get_y(), 190, 250, 25, 40)
            pdf.set_y(pdf.get_y() + 255)
            pdf.set_font('DejaVu', '', 6)
            pdf.cell(0, 4, 'Для записи решений заданий 13–19', align='C')

        # Черновик
        pdf.add_page()
        pdf.set_font('DejaVu', 'B', 9)
        pdf.cell(0, 6, 'Черновик (часть 1)', align='C', new_x=XPos.LMARGIN, new_y=YPos.NEXT)
        pdf.ln(3)
        pdf.draw_grid(10, pdf.get_y(), 190, 260, 20, 36)

    # Страница с ответами
    pdf.add_page()
    pdf.set_font('DejaVu', 'B', 12)
    pdf.cell(0, 10, 'Ответы к вариантам', align='C', new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    pdf.ln(5)
    for var_idx, tasks in enumerate(all_tasks):
        pdf.set_font('DejaVu', 'B', 9)
        pdf.cell(0, 6, f'Вариант {var_idx+1}', new_x=XPos.LMARGIN, new_y=YPos.NEXT)
        pdf.set_font('DejaVu', '', 8)
        for i in range(19):
            task = tasks[i]
            pdf.cell(10, 5, f'{i+1}.', new_x=XPos.RIGHT, new_y=YPos.TOP)
            pdf.cell(0, 5, task['answer'], new_x=XPos.LMARGIN, new_y=YPos.NEXT)
        pdf.ln(3)

    path = os.path.join(TEMP_DIR, 'ege_variants.pdf')
    pdf.output(path)
    return path

# ---------- СОСТОЯНИЯ ДИАЛОГА ----------
class GenForm(StatesGroup):
    grade = State()
    topic = State()
    variants = State()
    problems = State()
    per_row = State()
    answers = State()

class EGEForm(StatesGroup):
    num_variants = State()

class TheoryForm(StatesGroup):
    task_num = State()

# ---------- КЛАВИАТУРЫ ----------
def main_kb():
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="9 класс"), KeyboardButton(text="10 класс"), KeyboardButton(text="11 класс")],
            [KeyboardButton(text="🎲 Вариант ЕГЭ")],
            [KeyboardButton(text="📖 Теория ЕГЭ")]
        ],
        resize_keyboard=True
    )

def back_kb():
    return ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text="⬅️ Назад")]],
        resize_keyboard=True
    )

# ---------- ОБРАБОТЧИКИ ----------
@dp.message(Command("start"))
async def start(message: types.Message, state: FSMContext):
    await state.clear()
    await message.answer("👋 Выберите действие:", reply_markup=main_kb())
    await state.set_state(GenForm.grade)

@dp.message(GenForm.grade, F.text.in_(["9 класс", "10 класс", "11 класс"]))
async def set_grade(message: types.Message, state: FSMContext):
    grade = message.text.split()[0]   # "9", "10", "11"
    await state.update_data(grade=grade)
    topics = list(GRADE_TOPICS[grade].keys())
    kb = [[KeyboardButton(text=t)] for t in topics]
    kb.append([KeyboardButton(text="⬅️ Назад")])
    await message.answer("📚 Выберите тему:", reply_markup=ReplyKeyboardMarkup(keyboard=kb, resize_keyboard=True))
    await state.set_state(GenForm.topic)

@dp.message(GenForm.grade, F.text == "🎲 Вариант ЕГЭ")
async def ege_start(message: types.Message, state: FSMContext):
    await state.clear()
    await message.answer("📋 Сколько вариантов сгенерировать? (введите число от 1 до 4)\nИли нажмите «⬅️ Назад»", reply_markup=back_kb())
    await state.set_state(EGEForm.num_variants)

@dp.message(GenForm.grade, F.text == "📖 Теория ЕГЭ")
async def theory_start(message: types.Message, state: FSMContext):
    await state.clear()
    kb = [[KeyboardButton(text=str(i)) for i in range(1, 7)],
          [KeyboardButton(text=str(i)) for i in range(7, 13)],
          [KeyboardButton(text="⬅️ Назад")]]
    await message.answer("Выберите номер задания для теории (1–12):", reply_markup=ReplyKeyboardMarkup(keyboard=kb, resize_keyboard=True))
    await state.set_state(TheoryForm.task_num)

@dp.message(TheoryForm.task_num, F.text == "⬅️ Назад")
async def theory_back(message: types.Message, state: FSMContext):
    await state.clear()
    await start(message, state)

@dp.message(TheoryForm.task_num)
async def theory_send(message: types.Message, state: FSMContext):
    if not message.text.isdigit() or not (1 <= int(message.text) <= 12):
        return await message.answer("Введите число от 1 до 12 или нажмите «⬅️ Назад».")
    task_num = int(message.text)
    file_path = os.path.join(MATH_DIR, f"Задание {task_num}.pdf")
    if not os.path.exists(file_path):
        await message.answer(f"❌ Файл с теорией для задания {task_num} не найден. Проверьте папку math.")
    else:
        await message.answer_document(FSInputFile(file_path), caption=f"📘 Теория по заданию {task_num}")
    await message.answer("Выберите действие:", reply_markup=main_kb())
    await state.set_state(GenForm.grade)

@dp.message(EGEForm.num_variants, F.text == "⬅️ Назад")
async def ege_back(message: types.Message, state: FSMContext):
    await state.clear()
    await start(message, state)

@dp.message(EGEForm.num_variants)
async def ege_num_variants(message: types.Message, state: FSMContext):
    if not message.text.isdigit() or not (1 <= int(message.text) <= 4):
        return await message.answer("Введите число от 1 до 4.")
    num = int(message.text)
    await state.clear()
    msg = await message.answer("⏳ Генерирую варианты ЕГЭ...")
    try:
        pdf_path = generate_ege_variants_pdf(num)
        await message.answer_document(FSInputFile(pdf_path), caption="✅ Ваши варианты ЕГЭ готовы! Ответы — в конце файла.")
        os.remove(pdf_path)
    except Exception as e:
        logging.error(e)
        await message.answer("⚠️ Ошибка генерации. Попробуйте снова.")
    finally:
        await message.answer("Выберите действие:", reply_markup=main_kb())
        await state.set_state(GenForm.grade)

# Обработчики тем и параметров контрольной
@dp.message(GenForm.topic, F.text.in_(sum([list(GRADE_TOPICS[g].keys()) for g in GRADE_TOPICS], [])))
async def set_topic(message: types.Message, state: FSMContext):
    await state.update_data(topic=message.text)
    await message.answer("📋 Сколько вариантов? (введите число от 1 до 8)\nИли нажмите «⬅️ Назад»", reply_markup=back_kb())
    await state.set_state(GenForm.variants)

@dp.message(GenForm.topic, F.text == "⬅️ Назад")
async def topic_back(message: types.Message, state: FSMContext):
    await state.clear()
    await start(message, state)

@dp.message(GenForm.variants, F.text == "⬅️ Назад")
async def variants_back(message: types.Message, state: FSMContext):
    data = await state.get_data()
    grade = data.get('grade')
    if grade:
        topics = list(GRADE_TOPICS[grade].keys())
        kb = [[KeyboardButton(text=t)] for t in topics]
        kb.append([KeyboardButton(text="⬅️ Назад")])
        await message.answer("📚 Выберите тему:", reply_markup=ReplyKeyboardMarkup(keyboard=kb, resize_keyboard=True))
        await state.set_state(GenForm.topic)
    else:
        await state.clear()
        await start(message, state)

@dp.message(GenForm.variants)
async def set_variants(message: types.Message, state: FSMContext):
    if not message.text.isdigit() or not (1 <= int(message.text) <= 8):
        return await message.answer("Введите число от 1 до 8.")
    await state.update_data(variants=int(message.text))
    await message.answer("📝 Сколько заданий в варианте? (1–12)\nИли нажмите «⬅️ Назад»", reply_markup=back_kb())
    await state.set_state(GenForm.problems)

@dp.message(GenForm.problems, F.text == "⬅️ Назад")
async def problems_back(message: types.Message, state: FSMContext):
    await message.answer("📋 Сколько вариантов? (введите число от 1 до 8)", reply_markup=back_kb())
    await state.set_state(GenForm.variants)

@dp.message(GenForm.problems)
async def set_problems(message: types.Message, state: FSMContext):
    if not message.text.isdigit() or not (1 <= int(message.text) <= 12):
        return await message.answer("Введите число от 1 до 12.")
    await state.update_data(problems=int(message.text))
    kb = [[KeyboardButton(text="2 в ряд"), KeyboardButton(text="1 в ряд")], [KeyboardButton(text="⬅️ Назад")]]
    await message.answer("📄 Расположение вариантов на листе:", reply_markup=ReplyKeyboardMarkup(keyboard=kb, resize_keyboard=True))
    await state.set_state(GenForm.per_row)

@dp.message(GenForm.per_row, F.text == "⬅️ Назад")
async def per_row_back(message: types.Message, state: FSMContext):
    await message.answer("📝 Сколько заданий в варианте? (1–12)", reply_markup=back_kb())
    await state.set_state(GenForm.problems)

@dp.message(GenForm.per_row, F.text.in_(["2 в ряд", "1 в ряд"]))
async def set_per_row(message: types.Message, state: FSMContext):
    per_row = 2 if message.text == "2 в ряд" else 1
    await state.update_data(per_row=per_row)
    kb = [[KeyboardButton(text="Да"), KeyboardButton(text="Нет")], [KeyboardButton(text="⬅️ Назад")]]
    await message.answer("✅ Включить ответы?", reply_markup=ReplyKeyboardMarkup(keyboard=kb, resize_keyboard=True))
    await state.set_state(GenForm.answers)

@dp.message(GenForm.answers, F.text == "⬅️ Назад")
async def answers_back(message: types.Message, state: FSMContext):
    kb = [[KeyboardButton(text="2 в ряд"), KeyboardButton(text="1 в ряд")], [KeyboardButton(text="⬅️ Назад")]]
    await message.answer("📄 Расположение вариантов на листе:", reply_markup=ReplyKeyboardMarkup(keyboard=kb, resize_keyboard=True))
    await state.set_state(GenForm.per_row)

@dp.message(GenForm.answers, F.text.in_(["Да", "Нет"]))
async def set_answers(message: types.Message, state: FSMContext):
    with_answers = message.text == "Да"
    data = await state.get_data()
    await state.clear()
    msg = await message.answer("⏳ Генерирую контрольную...")
    try:
        pdf_path = generate_pdf(
            data['grade'], data['topic'], data['variants'],
            data['problems'], data['per_row'], with_answers
        )
        await message.answer_document(FSInputFile(pdf_path), caption="✅ Ваша контрольная готова! Можно сразу печатать.")
        os.remove(pdf_path)
    except Exception as e:
        logging.error(e)
        await message.answer("⚠️ Ошибка генерации. Попробуйте снова.")
    finally:
        await message.answer("Выберите действие:", reply_markup=main_kb())
        await state.set_state(GenForm.grade)

@dp.message(F.text == "⬅️ Назад")
async def general_back(message: types.Message, state: FSMContext):
    await state.clear()
    await start(message, state)

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
