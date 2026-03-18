from __future__ import annotations

from datetime import datetime
from typing import Dict, Tuple

from src.core.plugin import Plugin
from src.core.messenger import Messenger

from .render import create_calendar, create_leaderboard_image
from .storage import get_user_dir, load_user_data, save_user_data, list_member_dirs, ROOT_DIR
from .utils import format_duration_precise

RES_DEER_DIR = ROOT_DIR / "res" / "deer_check_in"
TEMP_DIR = ROOT_DIR / "temp"


def _get_account_id(messenger: Messenger) -> str:
    return str(messenger.self_id or "unknown")


def _get_group_key(messenger: Messenger) -> str:
    if messenger.group_id is not None:
        return str(messenger.group_id)
    return f"private_{messenger.user_id}"


def _get_target_uin(messenger: Messenger) -> Tuple[int, bool]:
    at_list = messenger.extract_at_qq()
    if at_list:
        return at_list[0], True
    return messenger.user_id, False


async def _resolve_display_name(plugin: Plugin, messenger: Messenger, uin: int, is_at: bool) -> str:
    if uin == messenger.user_id and messenger.nickname:
        return messenger.nickname
    if messenger.group_id is not None:
        try:
            resp = await plugin.api.get_group_member_info(messenger.group_id, uin)
            if isinstance(resp, dict) and resp.get("retcode", 0) == 0:
                data = resp.get("data", {})
                name = data.get("card") or data.get("nickname")
                if name:
                    return name
        except Exception:
            pass
    return str(uin)


def _ensure_abstinence(data: Dict) -> Dict:
    data["abstinence"] = data.get("abstinence", {})
    return data["abstinence"]


def _get_sign_days(data: Dict, year: int, month: int) -> Dict[str, int]:
    return data.get(str(year), {}).get(str(month), {})


def _update_sign_day(data: Dict, year: int, month: int, day: int) -> None:
    data[str(year)] = data.get(str(year), {})
    data[str(year)][str(month)] = data[str(year)].get(str(month), {})
    data[str(year)][str(month)][str(day)] = data[str(year)][str(month)].get(str(day), 0) + 1


async def _get_member_checkin_number(account_id: str, group_id: str, uin: int) -> Tuple[int, int, str]:
    user_dir = get_user_dir(account_id, group_id, uin)
    data = load_user_data(user_dir)

    now = datetime.now()
    month_l = data.get(str(now.year), {}).get(str(now.month), {})
    day_str = str(now.day)
    name = data.get("name", str(uin))

    total = 0
    nowday = 0
    for day, num in month_l.items():
        total += num
        if day_str == day:
            nowday = num

    return nowday, total, name


async def _get_abstinence_status(account_id: str, group_id: str, uin: int):
    user_dir = get_user_dir(account_id, group_id, uin)
    data = load_user_data(user_dir)
    name = data.get("name", str(uin))
    if "abstinence" not in data:
        return 0, (0, 0), name
    abstinence = data.get("abstinence", {})
    timestamp = abstinence.get("timestamp", 0)
    history = abstinence.get("history", {})
    history_start, history_end = history.get("start", 0), history.get("end", 0)
    return timestamp, (history_start, history_end), name


def register(plugin: Plugin) -> None:
    sender = plugin.get_sender()

    @plugin.on_msg(r"^(((🦌|鹿|撸|录|炉)(管|关|官)?)|(扣(扣)?|自(慰|摸|薇)|紫薇)|(舔|口(角|交)?))(签到)?(@.*)?$")
    async def deer_check_in(messenger: Messenger, matches):
        account_id = _get_account_id(messenger)
        group_id = _get_group_key(messenger)
        uin, is_at = _get_target_uin(messenger)
        user_dir = get_user_dir(account_id, group_id, uin)
        data = load_user_data(user_dir)

        abstinence = _ensure_abstinence(data)
        if abstinence.get("status"):
            nick = "对方" if is_at else "你"
            await sender.reply(messenger, f"{nick}在禁欲中，禁止{matches.group(1)}")
            return

        now = datetime.now()
        _update_sign_day(data, now.year, now.month, now.day)
        data["name"] = await _resolve_display_name(plugin, messenger, uin, is_at)
        save_user_data(user_dir, data)

        deer_img = "kou.png" if any(x in matches.group(1) for x in ("扣", "薇", "慰", "摸", "舔")) else "deer.png"
        check_img = "koub.png" if any(x in matches.group(1) for x in ("扣", "薇", "慰", "摸", "舔")) else "check.png"

        img = create_calendar(
            year=now.year,
            month=now.month,
            sign_days=_get_sign_days(data, now.year, now.month),
            deer_image_path=str(RES_DEER_DIR / deer_img),
            check_image_path=str(RES_DEER_DIR / check_img),
            name=data["name"],
        )
        timestamp_ms = int(now.timestamp() * 1000 + now.microsecond / 1000)

        TEMP_DIR.mkdir(parents=True, exist_ok=True)
        path = TEMP_DIR / f"{timestamp_ms}.png"
        img.save(str(path.resolve()), "PNG")

        if is_at:
            await sender.reply(messenger, "你成功帮对方签到了")

        await sender.reply_with_image(messenger, str(path.resolve()))

    @plugin.on_msg(r"^(鹿|撸|录|炉)(管|关|官)?补签(\d{1,2})月(\d{1,2})日?(@.*)?$")
    async def deer_check_in_patch(messenger: Messenger, matches):
        account_id = _get_account_id(messenger)
        group_id = _get_group_key(messenger)
        uin, is_at = _get_target_uin(messenger)
        user_dir = get_user_dir(account_id, group_id, uin)
        data = load_user_data(user_dir)

        abstinence = _ensure_abstinence(data)
        if abstinence.get("status"):
            nick = "对方" if is_at else "你"
            await sender.reply(messenger, f"{nick}在禁欲中，禁止补签")
            return

        now = datetime.now()
        patch_month = int(matches.group(3))
        patch_day = int(matches.group(4))

        if patch_month > now.month or (patch_month == now.month and patch_day > now.day):
            await sender.reply(messenger, "日期非法")
            return

        _update_sign_day(data, now.year, patch_month, patch_day)
        data["name"] = await _resolve_display_name(plugin, messenger, uin, is_at)
        save_user_data(user_dir, data)

        img = create_calendar(
            year=now.year,
            month=patch_month,
            sign_days=_get_sign_days(data, now.year, patch_month),
            deer_image_path=str(RES_DEER_DIR / ("kou.png" if "扣" in matches.group(1) else "deer.png")),
            check_image_path=str(RES_DEER_DIR / ("koub.png" if "扣" in matches.group(1) else "check.png")),
            name=data["name"],
        )
        timestamp_ms = int(now.timestamp() * 1000 + now.microsecond / 1000)

        TEMP_DIR.mkdir(parents=True, exist_ok=True)
        path = TEMP_DIR / f"{timestamp_ms}.png"
        img.save(str(path.resolve()), "PNG")

        if is_at:
            await sender.reply(messenger, f"你成功帮对方补签了{patch_month}月{patch_day}日")
        else:
            await sender.reply(messenger, f"成功补签{patch_month}月{patch_day}日")

        await sender.reply_with_image(messenger, str(path.resolve()))

    @plugin.on_msg(r"^(((🦌|鹿|撸|录|炉)(管|关|官)?)|(扣(扣)?|自(慰|摸|薇)|紫薇)|(舔|口(角|交)?))(签到)?(次数|成绩)(@.*)?$")
    async def deer_check_in_member_number(messenger: Messenger, matches):
        account_id = _get_account_id(messenger)
        group_id = _get_group_key(messenger)
        uin, is_at = _get_target_uin(messenger)
        nick = "对方" if is_at else "你"
        nowday, total, name = await _get_member_checkin_number(account_id, group_id, uin)
        await sender.reply(messenger, f"{name}\n{nick}今日已{matches.group(1)}{nowday}次\n本月已{matches.group(1)}{total}次")

    @plugin.on_msg(r"^(((🦌|鹿|撸|录|炉)(管|关|官)?)|(扣(扣)?|自(慰|摸|薇)|紫薇)|(舔|口(角|交)?))(签到)?(排(名|行(榜)?))$")
    async def deer_check_in_members_list(messenger: Messenger, matches):
        account_id = _get_account_id(messenger)
        group_id = _get_group_key(messenger)
        members_list = {}
        for member_dir in list_member_dirs(account_id, group_id):
            try:
                uin = int(member_dir.name)
            except ValueError:
                continue
            nowday, total, name = await _get_member_checkin_number(account_id, group_id, uin)
            if total:
                members_list[uin] = {"nowday": nowday, "total": total, "name": name}

        now = datetime.now()
        timestamp_ms = int(now.timestamp() * 1000 + now.microsecond / 1000)

        TEMP_DIR.mkdir(parents=True, exist_ok=True)
        path = TEMP_DIR / f"{timestamp_ms}tcilb.png"
        members_sorted = sorted(members_list.items(), key=lambda x: (x[1]["nowday"], x[1]["total"]), reverse=True)
        create_leaderboard_image(members_sorted, output_path=str(path.resolve()))
        await sender.reply_with_image(messenger, str(path.resolve()))

    @plugin.on_msg(r"^开始禁欲(@.*)?$")
    async def start_abstinence(messenger: Messenger, matches):
        account_id = _get_account_id(messenger)
        group_id = _get_group_key(messenger)
        uin, is_at = _get_target_uin(messenger)
        user_dir = get_user_dir(account_id, group_id, uin)
        data = load_user_data(user_dir)

        abstinence = _ensure_abstinence(data)
        if abstinence.get("status"):
            nick = "对方" if is_at else "你"
            await sender.reply(messenger, f"{nick}已在禁欲状态中")
            return

        now = datetime.now()
        abstinence["status"] = True
        abstinence["timestamp"] = now.timestamp()
        data["name"] = await _resolve_display_name(plugin, messenger, uin, is_at)
        save_user_data(user_dir, data)

        await sender.reply(messenger, "你已开始禁欲")

    @plugin.on_msg(r"^结束禁欲$")
    async def end_abstinence(messenger: Messenger, matches):
        account_id = _get_account_id(messenger)
        group_id = _get_group_key(messenger)
        uin = messenger.user_id
        user_dir = get_user_dir(account_id, group_id, uin)
        data = load_user_data(user_dir)

        abstinence = _ensure_abstinence(data)
        if not abstinence.get("status"):
            await sender.reply(messenger, "你尚未开始禁欲")
            return

        now = datetime.now()
        abstinence["status"] = False
        start = datetime.fromtimestamp(abstinence.get("timestamp", 0))
        abstinence["timestamp"] = 0
        data["name"] = await _resolve_display_name(plugin, messenger, uin, False)

        msg = f"你已结束禁欲，本次时长{format_duration_precise(start, now)}"
        abstinence["history"] = abstinence.get("history", {})
        history = abstinence["history"]
        if "start" not in history or history.get("end", 0) - history.get("start", 0) < now.timestamp() - start.timestamp():
            msg += "，超越你的前历史最高禁欲时长"
            if "start" not in history:
                msg += "(此前你还没有禁欲过)"
            else:
                msg += format_duration_precise(
                    datetime.fromtimestamp(history.get("start", 0)),
                    datetime.fromtimestamp(history.get("end", 0)),
                )
            history["start"] = start.timestamp()
            history["end"] = now.timestamp()

        save_user_data(user_dir, data)
        await sender.reply(messenger, msg)

    @plugin.on_msg(r"^禁欲(情况|状态|成绩)(@.*)?$")
    async def abstinence_status(messenger: Messenger, matches):
        account_id = _get_account_id(messenger)
        group_id = _get_group_key(messenger)
        uin, is_at = _get_target_uin(messenger)
        nick = "对方" if is_at else "你"

        timestamp, (history_start, history_end), name = await _get_abstinence_status(account_id, group_id, uin)
        msg = f"{nick}尚未在禁欲"
        f = True if history_start else False

        start = datetime.fromtimestamp(timestamp) if timestamp else datetime.now()
        end = datetime.now()
        if timestamp:
            msg = f"{nick}已禁欲{format_duration_precise(start, end)}"

        history_start_dt = start if not history_start else datetime.fromtimestamp(history_start)
        history_end_dt = end if not history_end else datetime.fromtimestamp(history_end)
        if f:
            msg += f"\n{nick}的历史最高禁欲时长为{format_duration_precise(history_start_dt, history_end_dt)}"

        await sender.reply(messenger, f"{name}\n{msg}")

    @plugin.on_msg(r"^禁欲(排(名|行(榜)?))$")
    async def abstinence_score_board(messenger: Messenger, matches):
        account_id = _get_account_id(messenger)
        group_id = _get_group_key(messenger)
        members_list = {}

        now = datetime.now()
        for member_dir in list_member_dirs(account_id, group_id):
            try:
                uin = int(member_dir.name)
            except ValueError:
                continue
            timestamp, (history_start, history_end), name = await _get_abstinence_status(account_id, group_id, uin)
            hs1, hs2 = history_start, history_end
            if timestamp or history_start:
                start = datetime.fromtimestamp(timestamp) if timestamp else now
                history_start_dt = start if not history_start else datetime.fromtimestamp(history_start)
                history_end_dt = now if not history_end else datetime.fromtimestamp(history_end)
                members_list[uin] = {
                    "nowday": now.timestamp() - timestamp if timestamp else 0,
                    "nowdayl": format_duration_precise(start, now) if timestamp else "未禁欲",
                    "total": hs2 - hs1,
                    "totall": format_duration_precise(history_start_dt, history_end_dt),
                    "name": name,
                }

        timestamp_ms = int(now.timestamp() * 1000 + now.microsecond / 1000)
        TEMP_DIR.mkdir(parents=True, exist_ok=True)
        path = TEMP_DIR / f"{timestamp_ms}abssb.png"
        temp = sorted(members_list.items(), key=lambda x: x[1]["total"], reverse=True)
        members_sorted = sorted(temp, key=lambda x: x[1]["nowday"], reverse=True)
        create_leaderboard_image(members_sorted, output_path=str(path.resolve()), option=True, fixed=timestamp_ms)
        await sender.reply_with_image(messenger, str(path.resolve()))

    @plugin.on_msg(r"^测试$")
    async def test(messenger: Messenger, matches):
        await sender.reply(messenger, "Ok")
