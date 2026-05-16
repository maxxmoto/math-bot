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


# ---------- АВТОСКАЧИВАНИЕ ШРИФТА ----------
FONTS_DIR = "fonts"
FONT_PATH = "fonts/DejaVuSans.ttf"
if not os.path.exists(FONT_PATH):
    os.makedirs(FONTS_DIR, exist_ok=True)
    print("Скачиваю шрифт DejaVuSans.ttf...")
    url = "https://github.com/dejavu-fonts/dejavu-fonts/raw/master/ttf/DejaVuSans.ttf"
    urllib.request.urlretrieve(url, FONT_PATH)
    print("Шрифт скачан.")



# ---------- НАСТРОЙКИ ----------
TOKEN = "8755532322:AAFnYy-VY4MRh4E3DyzcB5zSaarQvXQjuSA"              # ← замените на токен
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

# ---------- UNICODE-ИНДЕКСЫ ----------
SUPER = str.maketrans("0123456789", "⁰¹²³⁴⁵⁶⁷⁸⁹")
SUB   = str.maketrans("0123456789", "₀₁₂₃₄₅₆₇₈₉")

def super_num(n: int) -> str:
    return str(n).translate(SUPER)

def sub_num(n: int) -> str:
    return str(n).translate(SUB)

def sub_s(s: str) -> str:
    return s.translate(SUB)

# ---------- ГЕНЕРАТОРЫ ЗАДАЧ (возвращают plain text) ----------
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

# Геометрия – текст без чертежа в тексте, но чертёж будет в PDF отдельно
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

# ---------- КЛАСС PDF ----------
class PDF(FPDF):
    def __init__(self):
        super().__init__('P', 'mm', 'A4')
        # Добавляем шрифт с кириллицей (файл должен быть в папке fonts)
        font_path = os.path.join('fonts', 'DejaVuSans.ttf')
        if not os.path.exists(font_path):
            raise FileNotFoundError(f"Шрифт не найден: {font_path}. Скачайте DejaVuSans.ttf и положите в папку fonts.")
        self.add_font('DejaVu', '', font_path, uni=True)
        self.add_font('DejaVu', 'B', font_path, uni=True)  # жирный там же (можно тот же)
        self.set_auto_page_break(False)

    def dashed_line(self, x1, y1, x2, y2, dash=2, space=1.5):
        """Рисует пунктирную линию."""
        if x1 == x2:  # вертикальная
            length = y2 - y1
            steps = int(length / (dash + space))
            for i in range(steps):
                y = y1 + i*(dash+space)
                self.line(x1, y, x2, min(y+dash, y2))
        elif y1 == y2:  # горизонтальная
            length = x2 - x1
            steps = int(length / (dash + space))
            for i in range(steps):
                x = x1 + i*(dash+space)
                self.line(x, y1, min(x+dash, x2), y2)
        else:
            # упрощённо – рисуем обычную линию
            self.line(x1, y1, x2, y2)

    def draw_triangle_heron(self, x, y, w, h, a, b, c):
        """Рисует треугольник с подписанными сторонами (без соблюдения пропорций)."""
        self.set_line_width(0.4)
        self.set_draw_color(0)
        # Просто равнобедренный треугольник
        pts = [(x+w/2, y+2), (x+3, y+h-5), (x+w-3, y+h-5)]
        self.polygon(pts, style='D')
        # Подписи вершин
        self.set_font('DejaVu', '', 7)
        self.text(x+w/2-1, y-1, 'C')
        self.text(x-2, y+h-2, 'A')
        self.text(x+w-2, y+h-2, 'B')
        # Подписи сторон
        self.text(x+w/4, y+h/2+2, str(a))
        self.text(x+3*w/4-4, y+h/2+2, str(b))
        self.text(x+w/2-2, y+h-8, str(c))

    def draw_triangle_right(self, x, y, w, h, leg1, leg2):
        """Прямоугольный треугольник с катетами."""
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

# ---------- ФОРМИРОВАНИЕ PDF ----------
def generate_pdf(grade: str, topic: str, variants: int, problems: int, per_row: int, with_answers: bool):
    gens = GRADE_TOPICS[grade][topic]
    # Генерируем задачи
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
    card_w = (190 if per_row == 1 else 92)  # ширина карточки
    card_h = 95                              # высота карточки
    cols = per_row
    rows = (variants + cols - 1) // cols if cols > 0 else 1

    pdf.add_page()
    for idx in range(variants):
        row = idx // cols
        col = idx % cols
        x0 = 10 + col * (card_w + 6)
        y0 = 10 + row * (card_h + 8)

        if y0 + card_h > 280:
            pdf.add_page()
            y0 = 10
            row = 0  # сброс для новой страницы, но упростим

        # Рамка карточки пунктиром
        pdf.dashed_line(x0, y0, x0+card_w, y0)
        pdf.dashed_line(x0+card_w, y0, x0+card_w, y0+card_h)
        pdf.dashed_line(x0+card_w, y0+card_h, x0, y0+card_h)
        pdf.dashed_line(x0, y0+card_h, x0, y0)

        # Заголовок варианта
        pdf.set_font('DejaVu', 'B', 9)
        pdf.set_xy(x0, y0 + 1)
        pdf.cell(card_w, 5, f'Вариант {idx+1}', align='C')
        # Поля ФИО, класс, дата
        pdf.set_font('DejaVu', '', 6)
        pdf.set_xy(x0+2, y0+8)
        pdf.cell(card_w-4, 3, 'Фамилия, Имя ___________________')
        pdf.set_xy(x0+2, y0+12)
        pdf.cell(card_w-4, 3, 'Класс _______  Дата ___________')
        # Задачи
        y_text = y0 + 18
        for p_idx, prob in enumerate(vars_problems[idx]):
            pdf.set_font('DejaVu', '', 7)
            pdf.set_xy(x0+2, y_text)
            # Если есть чертёж, рисуем его перед текстом
            if 'draw' in prob and prob['draw'] == 'heron':
                pdf.draw_triangle_heron(x0+card_w-30, y_text, 28, 20, prob['a'], prob['b'], prob['c'])
            elif 'draw' in prob and prob['draw'] == 'pythag':
                pdf.draw_triangle_right(x0+card_w-30, y_text, 28, 20, prob['a'], prob['b'])
            # Текст задачи
            pdf.multi_cell(card_w-6, 3.5, f'{p_idx+1}. {prob["text"]}')
            y_text = pdf.get_y() + 1

        # Линии разреза между карточками
        if col < cols-1:
            pdf.dashed_line(x0+card_w+3, y0, x0+card_w+3, y0+card_h)
        if row < rows-1:
            pdf.dashed_line(x0, y0+card_h+3, x0+card_w, y0+card_h+3)

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

# ---------- СОСТОЯНИЯ ДИАЛОГА ----------
class GenForm(StatesGroup):
    grade = State()
    topic = State()
    variants = State()
    problems = State()
    per_row = State()
    answers = State()

# ---------- ОБРАБОТЧИКИ ----------
@dp.message(Command("start"))
async def start(message: types.Message, state: FSMContext):
    await state.clear()
    kb = [[types.KeyboardButton(text="9 класс"), types.KeyboardButton(text="10 класс"), types.KeyboardButton(text="11 класс")]]
    await message.answer("👋 Выберите класс:", reply_markup=types.ReplyKeyboardMarkup(keyboard=kb, resize_keyboard=True))
    await state.set_state(GenForm.grade)

@dp.message(GenForm.grade, F.text.in_(["9 класс", "10 класс", "11 класс"]))
async def set_grade(message: types.Message, state: FSMContext):
    grade = message.text.split()[0]   # теперь "9", "10", "11"
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
    await message.answer("📄 Расположение вариантов на листе:", reply_markup=types.ReplyKeyboardMarkup(keyboard=kb, resize_keyboard=True))
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
        await message.answer("Для новой работы нажмите /start", reply_markup=types.ReplyKeyboardRemove())

@dp.message(F.text == "⬅️ Назад")
async def back(message: types.Message, state: FSMContext):
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
