import logging
from contextlib import suppress
from datetime import UTC, date, datetime
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
    build_profile_edit_keyboard,
    build_profile_keyboard,
    build_step_view,
    build_timezone_keyboard,
    build_undo_keyboard,
    format_profile_message,
    format_record_confirmation,
    format_stats_message,
    format_timezone_label,
)
from .utils import utc_now

logger = logging.getLogger(__name__)

PROFILE_EDIT_KEY = "profile_edit_field"
PROFILE_EDIT_HEIGHT = "height_cm"
PROFILE_EDIT_WEIGHT = "weight_kg"
PROFILE_EDIT_BIRTHDAY = "birthday"
PROFILE_EDIT_NICKNAME = "nickname"


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
        "• 我的信息：/me\n"
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


async def me(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not _is_private(update):
        await _reply_private_only(update)
        return
    await _reply_profile(update, context, build_profile_keyboard())


async def profile_input(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not _is_private(update):
        return
    if update.message is None or update.message.text is None:
        return
    if update.effective_user is None:
        return
    user_data = context.user_data
    if user_data is None:
        return
    field = user_data.get(PROFILE_EDIT_KEY)
    if field is None:
        return
    text = update.message.text.strip()
    if not text:
        return
    if text.lower() == "q!":
        user_data.pop(PROFILE_EDIT_KEY, None)
        await update.message.reply_text("已取消修改。")
        await _reply_profile(update, context, build_profile_keyboard())
        return
    if text.startswith("/"):
        return
    services = _services(context)
    user_id = update.effective_user.id
    profile = services.users.get_profile(user_id)
    if profile is None:
        user_data.pop(PROFILE_EDIT_KEY, None)
        await update.message.reply_text(
            "请先设置时区后再修改资料：",
            reply_markup=build_timezone_keyboard(),
            parse_mode=ParseMode.HTML,
        )
        return
    now_utc = utc_now()
    if field == PROFILE_EDIT_HEIGHT:
        height_cm = _parse_height(text)
        if height_cm is None:
            await update.message.reply_text("身高请输入 50-250 的整数（cm），例如 175。发送 q! 取消。")
            return
        services.users.update_height_cm(user_id, height_cm, now_utc)
        user_data.pop(PROFILE_EDIT_KEY, None)
        await update.message.reply_text("已更新身高。")
        await _reply_profile(update, context, build_profile_keyboard())
        return
    if field == PROFILE_EDIT_WEIGHT:
        weight_kg = _parse_weight(text)
        if weight_kg is None:
            await update.message.reply_text("体重请输入 20-200 的数字（kg），例如 70.5。发送 q! 取消。")
            return
        services.users.update_weight_kg(user_id, weight_kg, now_utc)
        user_data.pop(PROFILE_EDIT_KEY, None)
        await update.message.reply_text("已更新体重。")
        await _reply_profile(update, context, build_profile_keyboard())
        return
    if field == PROFILE_EDIT_BIRTHDAY:
        birthday = _parse_birthday(text)
        if birthday is None:
            await update.message.reply_text("生日请输入 YYYY-MM-DD，且不能是未来日期。发送 q! 取消。")
            return
        services.users.update_birthday(user_id, birthday, now_utc)
        user_data.pop(PROFILE_EDIT_KEY, None)
        await update.message.reply_text("已更新生日。")
        await _reply_profile(update, context, build_profile_keyboard())
        return
    if field == PROFILE_EDIT_NICKNAME:
        nickname = _parse_nickname(text)
        if nickname is None:
            await update.message.reply_text("昵称不能为空且不超过 32 个字符。发送 q! 取消。")
            return
        services.users.update_nickname(user_id, nickname, now_utc)
        user_data.pop(PROFILE_EDIT_KEY, None)
        await update.message.reply_text("已更新昵称。")
        await _reply_profile(update, context, build_profile_keyboard())
        return


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
    if data.startswith("me:"):
        await _handle_profile_action(query, context, data)
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
    nickname = _build_display_name(query.from_user)
    services.users.upsert_timezone(user_id, timezone, utc_now(), nickname)
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


async def _handle_profile_action(
    query, context: ContextTypes.DEFAULT_TYPE, data: str
) -> None:
    await query.answer()
    user_data = context.user_data
    if user_data is None:
        return
    action = data.split(":", 1)[1]
    if action == "edit":
        user_data.pop(PROFILE_EDIT_KEY, None)
        await _edit_profile(query, context, build_profile_edit_keyboard())
        return
    if action == "back":
        user_data.pop(PROFILE_EDIT_KEY, None)
        await _edit_profile(query, context, build_profile_keyboard())
        return
    if query.from_user is None:
        return
    if action == "nickname":
        user_data[PROFILE_EDIT_KEY] = PROFILE_EDIT_NICKNAME
        await _prompt_profile_input(query, "请输入昵称（最多 64 个字符），发送 q! 取消。")
        return
    if action == "height":
        user_data[PROFILE_EDIT_KEY] = PROFILE_EDIT_HEIGHT
        await _prompt_profile_input(query, "请输入身高（cm），例如 175。发送 q! 取消。")
        return
    if action == "weight":
        user_data[PROFILE_EDIT_KEY] = PROFILE_EDIT_WEIGHT
        await _prompt_profile_input(query, "请输入体重（kg），例如 70.5。发送 q! 取消。")
        return
    if action == "birthday":
        user_data[PROFILE_EDIT_KEY] = PROFILE_EDIT_BIRTHDAY
        await _prompt_profile_input(
            query, "请输入生日（YYYY-MM-DD），例如 1995-08-17。发送 q! 取消。"
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


async def _prompt_profile_input(query, text: str) -> None:
    if query.message:
        await query.message.reply_text(text)


async def _reply_profile(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    reply_markup,
) -> None:
    if update.effective_user is None or update.message is None:
        return
    services = _services(context)
    text = _build_profile_message(services, update.effective_user)
    if text is None:
        await update.message.reply_text(
            TIMEZONE_PROMPT,
            reply_markup=build_timezone_keyboard(),
            parse_mode=ParseMode.HTML,
        )
        return
    await update.message.reply_text(
        text, reply_markup=reply_markup, parse_mode=ParseMode.HTML
    )


async def _edit_profile(
    query,
    context: ContextTypes.DEFAULT_TYPE,
    reply_markup,
) -> None:
    services = _services(context)
    if query.from_user is None:
        return
    text = _build_profile_message(services, query.from_user)
    if text is None:
        await query.edit_message_text(
            TIMEZONE_PROMPT,
            reply_markup=build_timezone_keyboard(),
            parse_mode=ParseMode.HTML,
        )
        return
    await query.edit_message_text(
        text, reply_markup=reply_markup, parse_mode=ParseMode.HTML
    )


def _build_profile_message(services: Services, user) -> str | None:
    profile = services.users.get_profile(user.id)
    if profile is None:
        return None
    nickname = profile.nickname
    if not nickname:
        nickname = _build_display_name(user)
        services.users.update_nickname(user.id, nickname, utc_now())
    total_records = services.records.count_all_records(user.id)
    last_record = services.records.get_last_record_time(user.id)
    timezone = profile.timezone
    return format_profile_message(
        nickname=nickname,
        height=_format_height(profile.height_cm),
        weight=_format_weight(profile.weight_kg),
        birthday=_format_birthday(profile.birthday),
        total_records=total_records,
        last_record=_format_datetime(last_record, timezone),
        started_at=_format_datetime(profile.created_at_utc, timezone),
    )


def _build_display_name(user) -> str:
    parts = [user.first_name, user.last_name]
    name = " ".join(part for part in parts if part)
    if name:
        return name
    if user.username:
        return user.username
    return str(user.id)


def _format_height(height_cm: int | None) -> str:
    if height_cm is None:
        return "未设置"
    return f"{height_cm} cm"


def _format_weight(weight_kg: float | int | None) -> str:
    if weight_kg is None:
        return "未设置"
    weight_value = float(weight_kg)
    if weight_value.is_integer():
        return f"{int(weight_value)} kg"
    return f"{weight_value:.1f} kg"


def _format_birthday(birthday: str | None) -> str:
    if not birthday:
        return "未设置"
    return birthday


def _format_datetime(dt: datetime | None, timezone: str | None) -> str:
    if dt is None:
        return "暂无"
    if timezone:
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=UTC)
        with suppress(Exception):
            dt = dt.astimezone(ZoneInfo(timezone))
    return dt.strftime("%Y-%m-%d %H:%M")


def _parse_height(text: str) -> int | None:
    raw = text.strip().lower().replace("cm", "").replace(" ", "")
    if not raw.isdigit():
        return None
    value = int(raw)
    if value < 50 or value > 250:
        return None
    return value


def _parse_weight(text: str) -> float | None:
    raw = text.strip().lower().replace("kg", "").replace(" ", "")
    try:
        value = float(raw)
    except ValueError:
        return None
    if value < 20 or value > 200:
        return None
    return round(value, 1)


def _parse_birthday(text: str) -> str | None:
    raw = text.strip()
    try:
        value = datetime.strptime(raw, "%Y-%m-%d").date()
    except ValueError:
        return None
    if value > date.today() or value < date(1900, 1, 1):
        return None
    return value.isoformat()


def _parse_nickname(text: str) -> str | None:
    value = text.strip()
    if not value:
        return None
    if len(value) > 32:
        return None
    return value


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
