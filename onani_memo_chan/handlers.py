import logging
from zoneinfo import ZoneInfo

from telegram import Update
from telegram.constants import ParseMode
from telegram.ext import ContextTypes

from .enums import Action, Step
from .flow import apply_action
from .services import Services
from .session import Session
from .ui import (
    PRIVATE_ONLY_TEXT,
    SESSION_DONE_TEXT,
    SESSION_EXPIRED_TEXT,
    TIMEZONE_PROMPT,
    build_step_view,
    build_timezone_keyboard,
    build_undo_keyboard,
    format_record_confirmation,
    format_stats_message,
    format_timezone_label,
)
from .utils import utc_now

logger = logging.getLogger(__name__)


def _services(context: ContextTypes.DEFAULT_TYPE) -> Services:
    return context.application.bot_data["services"]


def _is_private(update: Update) -> bool:
    chat = update.effective_chat
    return chat is not None and chat.type == "private"


async def _reply_private_only(update: Update) -> None:
    if update.message:
        await update.message.reply_text(PRIVATE_ONLY_TEXT, parse_mode=ParseMode.HTML)


async def _send_timezone_prompt(update: Update, page: int | None = None) -> None:
    if update.message:
        await update.message.reply_text(
            TIMEZONE_PROMPT,
            reply_markup=build_timezone_keyboard(page),
            parse_mode=ParseMode.HTML,
        )


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not _is_private(update):
        await _reply_private_only(update)
        return
    services = _services(context)
    if update.effective_user is None:
        return
    user_id = update.effective_user.id
    timezone = services.users.get_timezone(user_id)
    if timezone is None:
        await _send_timezone_prompt(update)
        return
    help_text = (
        "<b>欢迎回来</b>\n"
        f"• 当前时区：{format_timezone_label(timezone)}\n"
        "• 修改时区：/timezone\n"
        "• 开始记录：/do\n"
        "• 统计：/week /month"
    )
    if update.message:
        await update.message.reply_text(help_text, parse_mode=ParseMode.HTML)


async def timezone(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not _is_private(update):
        await _reply_private_only(update)
        return
    await _send_timezone_prompt(update)


async def do(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not _is_private(update):
        await _reply_private_only(update)
        return
    services = _services(context)
    if update.effective_user is None or update.effective_chat is None:
        return
    user_id = update.effective_user.id
    timezone = services.users.get_timezone(user_id)
    if timezone is None:
        if update.message:
            await update.message.reply_text(
                "请先设置时区后再记录：",
                reply_markup=build_timezone_keyboard(),
                parse_mode=ParseMode.HTML,
            )
        return
    if update.message is None:
        return
    session = services.sessions.create(user_id, update.effective_chat.id)
    view = build_step_view(session)
    message = await update.message.reply_text(
        view.text, reply_markup=view.reply_markup, parse_mode=ParseMode.HTML
    )
    session.message_id = message.message_id


async def week(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await _send_stats(update, context, 7)


async def month(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await _send_stats(update, context, 30)


async def _send_stats(
    update: Update, context: ContextTypes.DEFAULT_TYPE, days: int
) -> None:
    if not _is_private(update):
        await _reply_private_only(update)
        return
    services = _services(context)
    if update.effective_user is None:
        return
    user_id = update.effective_user.id
    summary = services.stats.build_summary(user_id, days)
    if summary.total == 0:
        text = f"<b>统计</b>\n• 最近 {days} 天没有可用记录（撤销/删除的不计入）。"
        if update.message:
            await update.message.reply_text(text, parse_mode=ParseMode.HTML)
        return
    title = f"最近{days}天统计"
    text = format_stats_message(
        title=title,
        total=summary.total,
        avg_week=summary.avg_week,
        avg_month=summary.avg_month,
        top_bucket=summary.top_bucket,
        avg_interval=summary.avg_interval,
        last_ago=summary.last_ago,
    )
    if update.message:
        await update.message.reply_text(text, parse_mode=ParseMode.HTML)


async def callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    if query is None or query.data is None:
        return
    data = query.data
    if data.startswith("tz:"):
        await _handle_timezone_selection(query, context, data)
        return
    if data.startswith("tzp:"):
        await _handle_timezone_page(query, data)
        return
    if data == "tzc":
        await _handle_timezone_cancel(query)
        return
    if data.startswith("x:"):
        await _handle_session_cancel(query, context, data)
        return
    await _handle_session_action(query, context, data)


async def _handle_timezone_selection(
    query, context: ContextTypes.DEFAULT_TYPE, data: str
) -> None:
    await query.answer()
    services = _services(context)
    if query.from_user is None:
        return
    user_id = query.from_user.id
    timezone = data.split(":", 1)[1]
    services.users.upsert_timezone(user_id, timezone, utc_now())
    await query.edit_message_text(
        f"已设置时区：{format_timezone_label(timezone)}",
        parse_mode=ParseMode.HTML,
    )


async def _handle_timezone_page(query, data: str) -> None:
    await query.answer()
    page_raw = data.split(":", 1)[1]
    try:
        page = int(page_raw)
    except ValueError:
        page = None
    await query.edit_message_text(
        TIMEZONE_PROMPT,
        reply_markup=build_timezone_keyboard(page),
        parse_mode=ParseMode.HTML,
    )


async def _handle_timezone_cancel(query) -> None:
    await query.answer()
    await query.edit_message_text(
        "已取消修改时区，保持原设置。", parse_mode=ParseMode.HTML
    )


async def _handle_session_action(
    query, context: ContextTypes.DEFAULT_TYPE, data: str
) -> None:
    services = _services(context)
    parts = data.split(":", 2)
    if len(parts) != 3:
        return
    action_raw, session_id, value = parts
    try:
        action = Action(action_raw)
    except ValueError:
        await query.answer()
        return

    if action == Action.UNDO:
        await _handle_undo(query, services, session_id, value)
        return

    session = services.sessions.get(session_id)
    if session is None:
        await query.answer(SESSION_EXPIRED_TEXT, show_alert=True)
        return
    if session.finalizing:
        await query.answer(SESSION_DONE_TEXT, show_alert=True)
        return
    if _expected_action(session.step) != action:
        await query.answer()
        return

    try:
        transition = apply_action(session, action, value)
    except (ValueError, KeyError):
        await query.answer()
        return

    if transition.next_step is not None:
        view = build_step_view(session)
        await query.answer()
        await query.edit_message_text(
            view.text, reply_markup=view.reply_markup, parse_mode=ParseMode.HTML
        )
        return

    await _finalize_record(query, services, session)


async def _handle_session_cancel(query, context: ContextTypes.DEFAULT_TYPE, data: str) -> None:
    await query.answer()
    parts = data.split(":", 1)
    if len(parts) != 2:
        return
    session_id = parts[1]
    services = _services(context)
    services.sessions.remove(session_id)
    await query.edit_message_text("已取消本次记录，数据未保存。", parse_mode=ParseMode.HTML)


def _expected_action(step: Step) -> Action:
    return {
        Step.RATING: Action.RATING,
        Step.DURATION: Action.DURATION,
        Step.VOLUME: Action.VOLUME,
        Step.VISCOSITY: Action.VISCOSITY,
    }[step]


async def _finalize_record(query, services: Services, session) -> None:
    await query.answer()
    session.finalizing = True
    if not _session_complete(session):
        session.finalizing = False
        await query.edit_message_text("记录信息不完整，请重新 /do。", parse_mode=ParseMode.MARKDOWN)
        return
    timezone = services.users.get_timezone(session.user_id)
    if timezone is None:
        session.finalizing = False
        await query.edit_message_text(
            "请先设置时区后再记录：",
            reply_markup=build_timezone_keyboard(),
            parse_mode=ParseMode.HTML,
        )
        return

    now_utc = utc_now()
    local_dt = now_utc.astimezone(ZoneInfo(timezone))
    try:
        record_id = services.records.insert_record(
            user_id=session.user_id,
            timestamp_utc=now_utc,
            timezone=timezone,
            timestamp_local=local_dt,
            rating=session.rating,
            duration_code=session.duration_code,
            volume_code=session.volume_code,
            viscosity_code=session.viscosity_code,
            created_at_utc=now_utc,
        )
    except Exception:
        session.finalizing = False
        logger.exception("Record insert failed for user_id=%s", session.user_id)
        await query.edit_message_text("记录失败，请稍后再试。", parse_mode=ParseMode.MARKDOWN)
        return

    services.sessions.remove(session.session_id)
    text = format_record_confirmation(session, local_dt)
    await query.edit_message_text(
        text,
        reply_markup=build_undo_keyboard(session.session_id, record_id),
        parse_mode=ParseMode.HTML,
    )


async def _handle_undo(
    query, services: Services, session_id: str, value: str
) -> None:
    await query.answer()
    try:
        record_id = int(value)
    except ValueError:
        return
    if query.from_user is None:
        return
    success = services.records.soft_delete_record(record_id, query.from_user.id)
    if success:
        await query.edit_message_text("已删除本次记录。", parse_mode=ParseMode.HTML)
    else:
        await query.edit_message_text("删除失败或记录不存在。", parse_mode=ParseMode.HTML)


def _session_complete(session: Session) -> bool:
    return all(
        [
            session.rating is not None,
            session.duration_code is not None,
            session.volume_code is not None,
            session.viscosity_code is not None,
        ]
    )


async def cleanup_sessions(context: ContextTypes.DEFAULT_TYPE) -> None:
    services = _services(context)
    expired = services.sessions.cleanup_expired()
    if expired:
        logger.info("Cleaned %s expired sessions.", expired)


async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = None
    if isinstance(update, Update) and update.effective_user:
        user_id = update.effective_user.id
    logger.exception("Unhandled error for user_id=%s", user_id)
