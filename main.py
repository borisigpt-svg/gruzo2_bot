# ===== GRUZO2 HQ+++ main.py (single process / mutex / logs / soft-stop / tcp-stop) =====
import atexit
import asyncio
import contextlib
import datetime
import importlib
import json
import logging
import os
import random
import sys
from logging.handlers import TimedRotatingFileHandler
from pathlib import Path

from aiogram import Bot, Dispatcher, F, Router
from aiogram.exceptions import TelegramBadRequest, TelegramConflictError, TelegramNetworkError
from aiogram.filters import Command, CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import CallbackQuery, Message
from aiogram.utils.keyboard import InlineKeyboardBuilder
from dotenv import load_dotenv

# Load .env before reading config from os.getenv
load_dotenv(Path(__file__).resolve().parent / ".env", override=True)

_BOT_DIR = os.path.dirname(os.path.abspath(__file__))


def _setup_app_logging():
    log_dir = os.path.join(_BOT_DIR, "logs")
    os.makedirs(log_dir, exist_ok=True)
    app_log = os.path.join(log_dir, "app.log")

    level = os.getenv("LOG_LEVEL", "INFO").upper()

    handler = TimedRotatingFileHandler(app_log, when="midnight", backupCount=7, encoding="utf-8")
    fmt = logging.Formatter("%(asctime)s | %(levelname)s | %(name)s | %(message)s")
    handler.setFormatter(fmt)

    root = logging.getLogger()
    root.setLevel(level)
    # очистим дефолтные handlers, чтобы не было дублей
    root.handlers = []
    root.addHandler(handler)

_setup_app_logging()


# --- HQ+++ constants ---
_MUTEX_NAME = r"Local\GRUZO2_BOT_LOCK"

_LAUNCHER_LOG = os.path.join(_BOT_DIR, "launcher.log")

_STOP_FILE = os.path.join(_BOT_DIR, "stop.request")
_STOP_TCP_HOST = "127.0.0.1"
_STOP_TCP_PORT = 17602  # фиксированный порт под автозагрузку

_exit_code: int = 0
_stop_reason: str = ""  # tcp | file | unknown

def _set_stop_reason(reason: str) -> None:
    global _stop_reason
    # фиксируем ПЕРВУЮ причину (чтобы tcp не перетёр file и наоборот)
    if _stop_reason:
        return
    try:
        _stop_reason = str(reason or "")
    except Exception:
        _stop_reason = ""


def _launcher_log(line: str) -> None:
    ts = datetime.datetime.now().strftime("%d.%m.%Y %H:%M:%S")
    try:
        with open(_LAUNCHER_LOG, "a", encoding="utf-8") as f:
            f.write(f"[{ts}] {line}\n")
    except Exception:
        pass


def _set_exit_code(code: int) -> None:
    global _exit_code
    try:
        _exit_code = int(code)
    except Exception:
        _exit_code = 1


def _acquire_mutex_or_exit() -> None:
    """Windows single-instance lock (no extra processes needed)."""
    global _mutex_handle
    if os.name != "nt":
        return

    import ctypes

    kernel32 = ctypes.windll.kernel32
    ERROR_ALREADY_EXISTS = 183

    h = kernel32.CreateMutexW(None, True, _MUTEX_NAME)
    if not h:
        _launcher_log("LAUNCHER ERROR: CreateMutexW failed")
        return

    if kernel32.GetLastError() == ERROR_ALREADY_EXISTS:
        try:
            kernel32.CloseHandle(h)
        except Exception:
            pass
        _launcher_log("Already running. Exit.")
        raise SystemExit(0)

    _mutex_handle = h

    def _release_mutex() -> None:
        global _mutex_handle
        if os.name != "nt" or not _mutex_handle:
            return
        try:
            kernel32.ReleaseMutex(_mutex_handle)
        except Exception:
            pass
        try:
            kernel32.CloseHandle(_mutex_handle)
        except Exception:
            pass
        _mutex_handle = None

    atexit.register(_release_mutex)


def _install_exit_hooks() -> None:
    """Ensure STOP(code=...) is written even on unexpected exits."""
    _orig_excepthook = sys.excepthook

    def _excepthook(exctype, value, tb):
        try:
            _launcher_log(f"UNHANDLED EXCEPTION: {exctype.__name__}: {value}")
        except Exception:
            pass
        _set_exit_code(1)
        try:
            _orig_excepthook(exctype, value, tb)
        except Exception:
            pass

    sys.excepthook = _excepthook  # type: ignore

    def _on_exit():
        _launcher_log(f"STOP (code={_exit_code}) reason={_stop_reason or 'unknown'}")

    atexit.register(_on_exit)

async def _watch_stop_file(stop_event: asyncio.Event) -> None:
    """Fallback stop: stop.request file."""
    while not stop_event.is_set():
        try:
            if os.path.exists(_STOP_FILE):
                try:
                    os.remove(_STOP_FILE)
                except Exception:
                    pass


                _set_stop_reason("file")
                _launcher_log("SOFT_STOP requested (file)")
                stop_event.set()
                return
        except Exception:
            pass


        await asyncio.sleep(0.5)



async def _handle_stop_client(
    reader: asyncio.StreamReader,
    writer: asyncio.StreamWriter,
    stop_event: asyncio.Event,
) -> None:
    """TCP STOP: returns OK quickly (for ACK on client)."""
    try:
        data = b""
        try:
            data = await asyncio.wait_for(reader.read(128), timeout=0.3)
        except Exception:
            data = b""

        msg = data.decode("utf-8", errors="ignore").strip().upper()

        if msg in ("", "STOP", "QUIT", "EXIT"):
            _set_stop_reason("tcp")
            _launcher_log("SOFT_STOP requested (tcp)")  # ДО ACK
            stop_event.set()

            try:
                writer.write(b"OK\n")
                await writer.drain()
                _launcher_log("TCP_STOP ACK sent (OK)")  # строго ПОСЛЕ drain()
            except Exception:
                pass
        else:
            try:
                writer.write(b"ERR\n")
                await writer.drain()
            except Exception:
                pass

    finally:
        try:
            writer.close()
            await writer.wait_closed()
        except Exception:
            pass

async def _start_stop_server(stop_event: asyncio.Event):
    """Start local TCP stop server; return server or None."""
    try:
        server = await asyncio.start_server(
            lambda r, w: _handle_stop_client(r, w, stop_event),
            host=_STOP_TCP_HOST,
            port=_STOP_TCP_PORT,
        )
        _launcher_log(f"STOP server listening on {_STOP_TCP_HOST}:{_STOP_TCP_PORT}")
        return server
    except Exception as e:
        _launcher_log(f"STOP server disabled (tcp bind failed): {e}")
        return None


async def _sleep_or_stop(stop_event: asyncio.Event, seconds: int) -> bool:
    """Wait for seconds or stop_event."""
    try:
        await asyncio.wait_for(stop_event.wait(), timeout=seconds)
        return True
    except asyncio.TimeoutError:
        return stop_event.is_set()

async def _backoff_or_stop(stop_event: asyncio.Event, attempt: int, base: float = 1.0, cap: float = 60.0) -> bool:
    """
    attempt: 0,1,2...
    Возвращает True если stop_event сработал во время ожидания.
    """
    # exp backoff + jitter
    delay = min(cap, base * (2 ** attempt))
    delay = delay * (0.7 + random.random() * 0.6)  # jitter 0.7..1.3
    return await _sleep_or_stop(stop_event, int(delay))


# --- HQ+++ init (single process, logs) ---
_acquire_mutex_or_exit()
_install_exit_hooks()
_launcher_log("START")

# Project modules (loaded after env + after mutex init)
_data = importlib.import_module("data")
ROUTES = _data.ROUTES
TARIFFS = _data.TARIFFS
SCHEDULE = _data.SCHEDULE
GEO = _data.GEO
CONTACTS = _data.CONTACTS

try:
    _admin_store = importlib.import_module("admin_store")
    load_admin_chat_id = _admin_store.load_admin_chat_id
    save_admin_chat_id = _admin_store.save_admin_chat_id
except Exception:
    def load_admin_chat_id() -> int:
        return 0

    def save_admin_chat_id(chat_id: int) -> None:
        pass

texts = importlib.import_module("texts")


ORDERS_FILE = Path(__file__).with_name("orders.json")

def load_orders() -> dict:
    try:
        if ORDERS_FILE.exists():
            return json.loads(ORDERS_FILE.read_text(encoding="utf-8"))
    except Exception:
        pass
    return {}

def save_orders(orders: dict) -> None:
    try:
        tmp = ORDERS_FILE.with_suffix(".json.tmp")
        tmp.write_text(json.dumps(orders, ensure_ascii=False, indent=2), encoding="utf-8")
        tmp.replace(ORDERS_FILE)
    except Exception:
        pass

ADMIN_CHAT_ID = int(os.getenv("ADMIN_CHAT_ID", "0"))
if ADMIN_CHAT_ID == 0:
    ADMIN_CHAT_ID = load_admin_chat_id()
logging.info("BOOT: ADMIN_CHAT_ID=%s", ADMIN_CHAT_ID)

ORDERS = load_orders()
logging.info("BOOT: ORDERS loaded=%s", len(ORDERS))

BOT_TOKEN = os.getenv("BOT_TOKEN")
ADMIN_USERNAME = os.getenv("ADMIN_USERNAME", "Boris36912")

# --- PATCH: BORIS is the only owner-admin ---
BORIS_ID = int(os.getenv("BORIS_ID", "0") or "0")
if BORIS_ID <= 0:
    raise RuntimeError("BORIS_ID is not set in .env")

def is_owner(user_id: int) -> bool:
    return user_id == BORIS_ID
# --- END PATCH ---


STATUS_LABELS = {
    "ok": "✅ Принято",
    "way": "🚚 В пути",
    "done": "📦 Доставлено",
    "cancel": "❌ Отменено",
}



def kb_admin_status(order_id: str):
    kb = InlineKeyboardBuilder()
    kb.button(text=STATUS_LABELS["ok"], callback_data=f"st:{order_id}:ok")
    kb.button(text=STATUS_LABELS["way"], callback_data=f"st:{order_id}:way")
    kb.button(text=STATUS_LABELS["done"], callback_data=f"st:{order_id}:done")
    kb.button(text=STATUS_LABELS["cancel"], callback_data=f"st:{order_id}:cancel")
    kb.adjust(2, 2)
    return kb.as_markup()

def kb_main():
    kb = InlineKeyboardBuilder()
    kb.button(text="📦 Оформить заявку", callback_data="new")
    kb.button(text="💰 Тарифы", callback_data="tariffs")
    kb.button(text="🗺️ Маршруты", callback_data="routes")
    kb.button(text="🕒 График", callback_data="schedule")
    kb.button(text="📍 География", callback_data="geo")
    kb.button(text="☎️ Контакты", callback_data="contacts")
    kb.button(text="🔎 Статус заявки", callback_data="status")
    kb.adjust(1, 2, 2, 2)
    return kb.as_markup()

class NewOrder(StatesGroup):
    route = State()
    weight = State()
    name = State()
    phone = State()
    desc = State()

router = Router()

async def safe_cb_answer(c: CallbackQuery, text: str = "", *, show_alert: bool = False) -> None:
    # Если кнопка нажата на старой карточке (после рестарта) — Telegram ругается "query is too old".
    # Это не проблема, просто молча игнорируем.
    with contextlib.suppress(TelegramBadRequest):
        await c.answer(text, show_alert=show_alert)

def price_for(route: str, weight: float):
    if route not in TARIFFS:
        return None
    base = TARIFFS[route]
    for (wmin, wmax), p in base.items():
        if wmin <= weight < wmax:
            return p
    # если выше всех диапазонов — берём последний
    last = sorted(base.items(), key=lambda x: x[0][0])[-1]
    return last[1]


@router.message(CommandStart())
async def start(m: Message):
    await m.answer(texts.HELLO, reply_markup=kb_main())


@router.message(Command("help"))
async def help_cmd(m: Message):
    await m.answer(texts.HELP, reply_markup=kb_main())


@router.message(Command("claim_admin"))
async def claim_admin(m: Message):
    # Только Борис может назначать админ-чат
    if not is_owner(m.from_user.id):
        await m.answer("⛔ Нет доступа.")
        return

    save_admin_chat_id(m.chat.id)
    await m.answer(f"✅ Админ-чат установлен: {m.chat.id}")
    global ADMIN_CHAT_ID
    ADMIN_CHAT_ID = m.chat.id

@router.callback_query(F.data == "tariffs")
async def on_tariffs(c: CallbackQuery):
    lines = ["💰 *Тарифы*"]
    for route, bands in TARIFFS.items():
        lines.append(f"\n*{route}*")
        for (wmin, wmax), price in sorted(bands.items(), key=lambda x: x[0][0]):
            lines.append(f"• {wmin}-{wmax} кг — {price} ₽")
    await c.message.answer("\n".join(lines), parse_mode="Markdown")
    await safe_cb_answer(c)


@router.callback_query(F.data == "routes")
async def on_routes(c: CallbackQuery):
    lines = ["🗺️ *Маршруты:*"]
    for r in ROUTES:
        lines.append(f"• {r}")
    await c.message.answer("\n".join(lines), parse_mode="Markdown")
    await safe_cb_answer(c)


@router.callback_query(F.data == "schedule")
async def on_schedule(c: CallbackQuery):
    lines = ["🕒 *График:*"]
    for k, v in SCHEDULE.items():
        lines.append(f"• *{k}*: {v}")
    await c.message.answer("\n".join(lines), parse_mode="Markdown")
    await safe_cb_answer(c)


@router.callback_query(F.data == "geo")
async def on_geo(c: CallbackQuery):
    lines = ["📍 *География:*"]
    for g in GEO:
        lines.append(f"• {g}")
    await c.message.answer("\n".join(lines), parse_mode="Markdown")
    await safe_cb_answer(c)


@router.callback_query(F.data == "contacts")
async def on_contacts(c: CallbackQuery):
    lines = ["☎️ *Контакты:*"]
    for k, v in CONTACTS.items():
        lines.append(f"• *{k}*: {v}")
    await c.message.answer("\n".join(lines), parse_mode="Markdown")
    await safe_cb_answer(c)


@router.callback_query(F.data == "new")
async def on_new(c: CallbackQuery, state: FSMContext):
    await state.set_state(NewOrder.route)
    await c.message.answer("Выберите маршрут (как в списке):\n" + "\n".join([f"• {r}" for r in ROUTES]))
    await safe_cb_answer(c)


@router.message(NewOrder.route)
async def st_route(m: Message, state: FSMContext):
    route = (m.text or "").strip()
    if route not in ROUTES:
        await m.answer("Маршрут не найден. Введите точно как в списке.")
        return
    await state.update_data(route=route)
    await state.set_state(NewOrder.weight)
    await m.answer("Вес (кг), например 2.5")


@router.message(NewOrder.weight)
async def st_weight(m: Message, state: FSMContext):
    try:
        w = float((m.text or "0").replace(",", "."))
    except Exception:
        await m.answer("Введите число, например 2.5")
        return
    if w <= 0:
        await m.answer("Вес должен быть > 0")
        return

    await state.update_data(weight=w)
    await state.set_state(NewOrder.name)
    await m.answer("Имя отправителя/получателя?")


@router.message(NewOrder.name)
async def st_name(m: Message, state: FSMContext):
    await state.update_data(name=(m.text or "").strip())
    await state.set_state(NewOrder.phone)
    await m.answer("Телефон для связи?")


@router.message(NewOrder.phone)
async def st_phone(m: Message, state: FSMContext):
    await state.update_data(phone=(m.text or "").strip())
    await state.set_state(NewOrder.desc)
    await m.answer("Что отправляем? (письмо/посылка/описание)")

@router.message(NewOrder.desc)
async def st_desc(m: Message, state: FSMContext):
    data = await state.get_data()

    route = data.get("route")
    weight = data.get("weight")
    name = data.get("name")
    phone = data.get("phone")
    desc = (m.text or "").strip()

    price = price_for(route, weight)
    order_id = f"{m.from_user.id}-{int(datetime.datetime.now().timestamp())}"

    ORDERS[order_id] = {
        "route": route,
        "weight": weight,
        "name": name,
        "phone": phone,
        "desc": desc,
        "user_id": m.from_user.id,
        "status": "ok",
        "created": datetime.datetime.now().isoformat(),
    }
    save_orders(ORDERS)

    txt = (
        "✅ Заявка принята\n"
        f"ID: {order_id}\n"
        f"Маршрут: {route}\n"
        f"Вес: {weight} кг\n"
        f"Имя: {name}\n"
        f"Телефон: {phone}\n"
        f"Описание: {desc}\n"
    )
    if price is not None:
        txt += f"💰 Расчёт: {price} ₽ (по весу)\n"
    else:
        txt += "💰 Расчёт: уточним у оператора\n"

    await state.clear()
    await m.answer(txt, reply_markup=kb_main())

    if ADMIN_CHAT_ID:
        admin_txt = (
            "🆕 Новая заявка\n"
            f"ID: {order_id}\n"
            f"От: @{m.from_user.username or m.from_user.id}\n"
            f"Маршрут: {route}\n"
            f"Вес: {weight} кг\n"
            f"Имя: {name}\n"
            f"Телефон: {phone}\n"
            f"Описание: {desc}\n"
        )
        await m.bot.send_message(
            ADMIN_CHAT_ID,
            admin_txt,
            reply_markup=kb_admin_status(order_id),
        )

@router.callback_query(F.data == "status")
async def on_status(c: CallbackQuery, state: FSMContext):
    await state.set_state("ask_status")
    await c.message.answer("Введите ID заявки (как в сообщении после оформления)")
    await safe_cb_answer(c)


@router.message(F.text, lambda m: m and m.text and len(m.text) > 0)
async def any_text(m: Message, state: FSMContext):
    st = await state.get_state()
    if st != "ask_status":
        return

    order_id = (m.text or "").strip()
    order = ORDERS.get(order_id)
    if not order:
        await m.answer("Заявка не найдена. Проверь ID.")
        return

    label = STATUS_LABELS.get(order.get("status", "ok"), "✅ Принято")
    await state.clear()
    await m.answer(f"Статус заявки `{order_id}`: {label}", parse_mode="Markdown", reply_markup=kb_main())


async def main():
    if not BOT_TOKEN:
        raise RuntimeError("BOT_TOKEN is empty. Set it in .env")

    stop_event = asyncio.Event()

    try:
        if os.path.exists(_STOP_FILE):
            os.remove(_STOP_FILE)
    except Exception:
        pass

    watcher_task = asyncio.create_task(_watch_stop_file(stop_event))
    stop_server = await _start_stop_server(stop_event)

    try:
        while True:


            try:
                async with Bot(token=BOT_TOKEN) as bot:
                    dp = Dispatcher()
                    dp.include_router(router)

                    polling_task = asyncio.create_task(dp.start_polling(bot))
                    stop_task = asyncio.create_task(stop_event.wait())

                    done, _ = await asyncio.wait(
                        {polling_task, stop_task},
                        return_when=asyncio.FIRST_COMPLETED,
                    )

                    if stop_task in done:
                        _launcher_log(f"SOFT_STOP requested ({_stop_reason or 'unknown'})")
                        _set_exit_code(0)
                        

                        # максимально мягко: просим dp остановить polling и ждём
                        try:
                            if hasattr(dp, "stop_polling"):
                                dp.stop_polling()
                        except Exception:
                            pass

                        try:
                            await asyncio.wait_for(polling_task, timeout=20)
                            return
                        except asyncio.TimeoutError:
                            pass

                        polling_task.cancel()
                        with contextlib.suppress(Exception):
                            await polling_task

                        return

                    await polling_task

            except (KeyboardInterrupt, SystemExit):
                _set_exit_code(0)
                return

            except TelegramConflictError as e:
                logging.warning("TelegramConflictError (двойной запуск?): %s", e)
                if await _sleep_or_stop(stop_event, 10):
                    _set_exit_code(0)
                    return

            except TelegramNetworkError as e:
                logging.warning("Сеть/Telegram отвалилась (%s). Переподключение через 5 сек...", e)
                if await _sleep_or_stop(stop_event, 5):
                    _set_exit_code(0)
                    return

            except asyncio.CancelledError:
                _set_exit_code(0)
                return

            except Exception as e:
                logging.exception("Fatal error (%s). Restart in 5s.", e)
                if await _sleep_or_stop(stop_event, 5):
                    _set_exit_code(0)
                    return

    finally:
        if stop_server is not None:
            try:
                stop_server.close()
                await stop_server.wait_closed()
            except Exception:
                pass

        watcher_task.cancel()
        with contextlib.suppress(Exception):
            await watcher_task
@router.callback_query(lambda c: c.data and c.data.startswith("st:"))
async def on_admin_status(c: CallbackQuery):
    # Только Борис может менять статусы
    if not c.from_user or not is_owner(c.from_user.id):
        await safe_cb_answer(c, "⛔ Нет доступа.", show_alert=True)
        return

    parts = (c.data or "").split(":")
    if len(parts) != 3:
        await safe_cb_answer(c, "Ошибка данных", show_alert=True)
        return

    _, order_id, code = parts
    order = ORDERS.get(order_id)
    if not order:
        await safe_cb_answer(c, "Заявка не найдена (возможно уже закрыта).", show_alert=True)
        return

    # Обновляем статус + сохраняем на диск
    order["status"] = code
    save_orders(ORDERS)

    user_id = order.get("user_id")
    label = STATUS_LABELS.get(code, "✅ Принято")

    # Быстро отвечаем на callback (может упасть, если query "устарел")
    with contextlib.suppress(Exception):
        await safe_cb_answer(c, "Отправлено клиенту ✅")

    # Уведомляем клиента
    with contextlib.suppress(Exception):
        if user_id:
            await c.bot.send_message(user_id, f"Статус вашей заявки {order_id}: {label}")

    # Закрываем заявку и убираем кнопки, чтобы не жали повторно
    if code in {"done", "cancel"}:
        ORDERS.pop(order_id, None)
        save_orders(ORDERS)


    try:
        if c.message:
            await c.message.edit_reply_markup(reply_markup=None)
    except Exception:
        logging.exception("Failed to remove inline keyboard for order %s", order_id)

if __name__ == "__main__":
    asyncio.run(main())



