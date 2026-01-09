from collections.abc import Iterable
from dataclasses import dataclass
from datetime import datetime, timedelta

from telegram import InlineKeyboardButton, InlineKeyboardMarkup

from .enums import DurationCode, Step, ViscosityCode, VolumeCode
from .session import Session
from .timezones import DEFAULT_TIMEZONE_PAGE, TIMEZONE_LABEL_BY_IANA, TIMEZONE_PAGES
from .utils import format_timedelta

TIMEZONE_PROMPT = "<b>选择时区</b>\n在下方按钮中选择或取消。"
PRIVATE_ONLY_TEXT = "仅支持在私聊中使用，请切换到与机器人的私聊窗口。"
SESSION_EXPIRED_TEXT = "当前记录会话已过期，请重新发送 /do 开始新的记录。"
SESSION_DONE_TEXT = "这次记录已完成。"


@dataclass(frozen=True)
class StepView:
    text: str
    reply_markup: InlineKeyboardMarkup


DURATION_LABELS = {
    DurationCode.LE5: "5 分钟内",
    DurationCode.LE10: "10 分钟内",
    DurationCode.LE30: "30 分钟内",
    DurationCode.LE60: "60 分钟内",
    DurationCode.GT60: "60 分钟以上",
}

VOLUME_LABELS = {
    VolumeCode.LOW: "少",
    VolumeCode.MID: "一般",
    VolumeCode.HIGH: "多",
}

VISCOSITY_LABELS = {
    ViscosityCode.V1: "很稀",
    ViscosityCode.V2: "偏稀",
    ViscosityCode.V3: "适中",
    ViscosityCode.V4: "偏稠",
    ViscosityCode.V5: "很稠",
}

RATING_LABELS = {
    1: "太垃了",
    2: "不爽",
    3: "一般",
    4: "爽",
    5: "冲爆",
}


def format_timezone_label(iana: str) -> str:
    label = TIMEZONE_LABEL_BY_IANA.get(iana, iana)
    return f"{label} ({iana})"


def build_timezone_keyboard(page: int | None = None) -> InlineKeyboardMarkup:
    page_index = (page or DEFAULT_TIMEZONE_PAGE) - 1
    page_index = max(0, min(page_index, len(TIMEZONE_PAGES) - 1))
    rows: list[list[InlineKeyboardButton]] = []
    options = TIMEZONE_PAGES[page_index]
    for i in range(0, len(options), 2):
        chunk = options[i : i + 2]
        rows.append(
            [
                InlineKeyboardButton(option.label, callback_data=f"tz:{option.iana}")
                for option in chunk
            ]
        )

    nav_buttons: list[InlineKeyboardButton] = []
    if page_index > 0:
        nav_buttons.append(
            InlineKeyboardButton("上一页", callback_data=f"tzp:{page_index}")
        )
    if page_index < len(TIMEZONE_PAGES) - 1:
        nav_buttons.append(
            InlineKeyboardButton("下一页", callback_data=f"tzp:{page_index + 2}")
        )
    nav_buttons.append(InlineKeyboardButton("取消", callback_data="tzc"))
    rows.append(nav_buttons)
    return InlineKeyboardMarkup(rows)


def selection_summary(session: Session) -> str:
    parts: list[str] = []
    if session.rating is not None:
        parts.append(f"体验感={RATING_LABELS[session.rating]}")
    if session.duration_code is not None:
        parts.append(f"时长={DURATION_LABELS[session.duration_code]}")
    if session.volume_code is not None:
        parts.append(f"量={VOLUME_LABELS[session.volume_code]}")
    if session.viscosity_code is not None:
        parts.append(f"稠度={VISCOSITY_LABELS[session.viscosity_code]}")
    return "；".join(parts)


def build_rating_keyboard(session_id: str) -> InlineKeyboardMarkup:
    row = [
        InlineKeyboardButton(RATING_LABELS[value], callback_data=f"r:{session_id}:{value}")
        for value in range(1, 6)
    ]
    cancel = [InlineKeyboardButton("取消记录", callback_data=f"x:{session_id}")]
    return InlineKeyboardMarkup([row, cancel])


def build_duration_keyboard(session_id: str) -> InlineKeyboardMarkup:
    row = [
        InlineKeyboardButton(
            "<=5m", callback_data=f"d:{session_id}:{DurationCode.LE5.value}"
        ),
        InlineKeyboardButton(
            "<=10m", callback_data=f"d:{session_id}:{DurationCode.LE10.value}"
        ),
        InlineKeyboardButton(
            "<=30m", callback_data=f"d:{session_id}:{DurationCode.LE30.value}"
        ),
        InlineKeyboardButton(
            "<=60m", callback_data=f"d:{session_id}:{DurationCode.LE60.value}"
        ),
        InlineKeyboardButton(
            ">60m", callback_data=f"d:{session_id}:{DurationCode.GT60.value}"
        ),
    ]
    cancel = [InlineKeyboardButton("取消记录", callback_data=f"x:{session_id}")]
    return InlineKeyboardMarkup([row, cancel])


def build_volume_keyboard(session_id: str) -> InlineKeyboardMarkup:
    row = [
        InlineKeyboardButton(
            VOLUME_LABELS[VolumeCode.LOW],
            callback_data=f"v:{session_id}:{VolumeCode.LOW.value}",
        ),
        InlineKeyboardButton(
            VOLUME_LABELS[VolumeCode.MID],
            callback_data=f"v:{session_id}:{VolumeCode.MID.value}",
        ),
        InlineKeyboardButton(
            VOLUME_LABELS[VolumeCode.HIGH],
            callback_data=f"v:{session_id}:{VolumeCode.HIGH.value}",
        ),
    ]
    cancel = [InlineKeyboardButton("取消记录", callback_data=f"x:{session_id}")]
    return InlineKeyboardMarkup([row, cancel])


def build_viscosity_keyboard(session_id: str) -> InlineKeyboardMarkup:
    row = [
        InlineKeyboardButton(
            VISCOSITY_LABELS[ViscosityCode.V1],
            callback_data=f"c:{session_id}:{ViscosityCode.V1.value}",
        ),
        InlineKeyboardButton(
            VISCOSITY_LABELS[ViscosityCode.V2],
            callback_data=f"c:{session_id}:{ViscosityCode.V2.value}",
        ),
        InlineKeyboardButton(
            VISCOSITY_LABELS[ViscosityCode.V3],
            callback_data=f"c:{session_id}:{ViscosityCode.V3.value}",
        ),
        InlineKeyboardButton(
            VISCOSITY_LABELS[ViscosityCode.V4],
            callback_data=f"c:{session_id}:{ViscosityCode.V4.value}",
        ),
        InlineKeyboardButton(
            VISCOSITY_LABELS[ViscosityCode.V5],
            callback_data=f"c:{session_id}:{ViscosityCode.V5.value}",
        ),
    ]
    cancel = [InlineKeyboardButton("取消记录", callback_data=f"x:{session_id}")]
    return InlineKeyboardMarkup([row, cancel])


def build_undo_keyboard(session_id: str, record_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        [[InlineKeyboardButton("撤销这次", callback_data=f"u:{session_id}:{record_id}")]]
    )


def build_profile_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        [[InlineKeyboardButton("修改", callback_data="me:edit")]]
    )


def build_profile_edit_keyboard() -> InlineKeyboardMarkup:
    rows = [
        [
            InlineKeyboardButton("修改昵称", callback_data="me:nickname"),
            InlineKeyboardButton("修改生日", callback_data="me:birthday"),
         ],
        [
            InlineKeyboardButton("修改身高", callback_data="me:height"),
            InlineKeyboardButton("修改体重", callback_data="me:weight"),
        ],
        [InlineKeyboardButton("返回", callback_data="me:back")],
    ]
    return InlineKeyboardMarkup(rows)


def format_profile_message(
    nickname: str,
    height: str,
    weight: str,
    birthday: str,
    total_records: int,
    last_record: str,
    started_at: str,
) -> str:
    lines = [
        "<b>我的信息</b>",
        f"• 昵称：{nickname}",
        f"• 身高：{height}",
        f"• 体重：{weight}",
        f"• 生日：{birthday}",
        f"• 总记录次数：{total_records}",
        f"• 最后一次利用：{last_record}",
        f"• 开始利用时间：{started_at}",
    ]
    return "\n".join(lines)


def build_step_view(session: Session) -> StepView:
    if session.step == Step.RATING:
        return StepView("<b>体验感</b>\n主人冲爽了吗：", build_rating_keyboard(session.session_id))
    if session.step == Step.DURATION:
        text = f"<b>时长</b>\n已选：{selection_summary(session)}\n主人冲了多长时间："
        return StepView(text, build_duration_keyboard(session.session_id))
    if session.step == Step.VOLUME:
        text = f"<b>量</b>\n已选：{selection_summary(session)}\n主人🐍的多吗："
        return StepView(text, build_volume_keyboard(session.session_id))
    text = f"<b>稠度</b>\n已选：{selection_summary(session)}\n主人的精液是："
    return StepView(text, build_viscosity_keyboard(session.session_id))


def format_record_confirmation(session: Session, timestamp_local: datetime) -> str:
    rating = session.rating
    duration_code = session.duration_code
    volume_code = session.volume_code
    viscosity_code = session.viscosity_code
    if (
        rating is None
        or duration_code is None
        or volume_code is None
        or viscosity_code is None
    ):
        raise ValueError("Session is incomplete for confirmation rendering.")
    local_str = timestamp_local.strftime("%Y-%m-%d %H:%M")
    lines = [
        "<b>记录成功</b>",
        f"• 体验感：{RATING_LABELS[rating]}",
        f"• 时长：{DURATION_LABELS[duration_code]}",
        f"• 量：{VOLUME_LABELS[volume_code]}",
        f"• 稠度：{VISCOSITY_LABELS[viscosity_code]}",
        f"• 本地时间：{local_str}",
    ]
    return "\n".join(lines)


def format_stats_message(
    title: str,
    total: int,
    avg_week: float | None,
    avg_month: float | None,
    top_bucket: str | None,
    avg_interval: timedelta | None,
    last_ago: timedelta | None,
) -> str:
    lines = [f"<b>{title}</b>", f"• 总次数：{total}"]
    if avg_week is not None:
        lines.append(f"• 平均每周：{avg_week:.1f}")
    if avg_month is not None:
        lines.append(f"• 平均每月：{avg_month:.1f}")
    if top_bucket:
        lines.append(f"• 高频时段：{top_bucket}")
    if avg_interval is not None:
        lines.append(f"• 平均间隔：{format_timedelta(avg_interval)}")
    if last_ago is not None:
        lines.append(f"• 最近一次：{format_timedelta(last_ago)} 前")
    return "\n".join(lines)


def pick_top_bucket(bucket_counts: dict[str, int]) -> str | None:
    if not bucket_counts:
        return None
    max_count = max(bucket_counts.values())
    top = [name for name, count in bucket_counts.items() if count == max_count]
    return " / ".join(top)


def bucketize_hours(hours: Iterable[int]) -> dict[str, int]:
    buckets = {
        "深夜(00-06)": 0,
        "上午(06-12)": 0,
        "下午(12-18)": 0,
        "晚上(18-24)": 0,
    }
    for hour in hours:
        if 0 <= hour < 6:
            buckets["深夜(00-06)"] += 1
        elif 6 <= hour < 12:
            buckets["上午(06-12)"] += 1
        elif 12 <= hour < 18:
            buckets["下午(12-18)"] += 1
        else:
            buckets["晚上(18-24)"] += 1
    return {name: count for name, count in buckets.items() if count}
