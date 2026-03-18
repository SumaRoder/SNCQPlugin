from __future__ import annotations

import calendar
from datetime import datetime
from pathlib import Path
from typing import Dict, Iterable, Tuple

from PIL import Image, ImageDraw, ImageFont

ROOT_DIR = Path(__file__).resolve().parents[3]
RES_DIR = ROOT_DIR / "res"


class CheckInCalendar:
    def __init__(
        self,
        sign_days: Dict[str, int] | None = None,
        year: int | None = None,
        month: int | None = None,
        deer_image_path: str | None = None,
        check_image_path: str | None = None,
        name: str = "deer_check_in",
    ):
        self.year = year or datetime.now().year
        self.month = month or datetime.now().month
        self.sign_days = sign_days or {}
        self.name = name

        self.deer_image = self._load_image(deer_image_path) if deer_image_path else None
        self.check_image = self._load_image(check_image_path) if check_image_path else None

        self.width = 1080
        self.padding = 30
        self.header_height = 120
        self.weekday_height = 50

        available_width = self.width - 2 * self.padding
        self.cell_size = (available_width - 6 * 10) // 7
        self.gap = 10

        self.grid_top = self.header_height + self.weekday_height + 20

        self.bg_color = (255, 255, 255)
        self.border_color = (204, 204, 204)
        self.header_color = (0, 0, 0)
        self.subheader_color = (102, 102, 102)
        self.weekday_color = (153, 153, 153)
        self.day_number_color = (0, 0, 0)
        self.multiple_sign_color = (255, 0, 0)

        self._load_fonts()

    def _load_image(self, path: str):
        try:
            img = Image.open(path)
            return img.convert("RGBA")
        except Exception as exc:
            raise NotImplementedError from exc

    def _load_fonts(self):
        font_paths = [
            str(RES_DIR / "font.ttf"),
        ]

        self.font_header = None
        self.font_subheader = None
        self.font_weekday = None
        self.font_day = None
        self.font_multiple = None

        for font_path in font_paths:
            try:
                self.font_header = ImageFont.truetype(font_path, 48)
                self.font_subheader = ImageFont.truetype(font_path, 32)
                self.font_weekday = ImageFont.truetype(font_path, 28)
                self.font_day = ImageFont.truetype(font_path, 32)
                self.font_multiple = ImageFont.truetype(font_path, 28)
                break
            except Exception:
                continue

        if self.font_header is None:
            self.font_header = ImageFont.load_default()
            self.font_subheader = ImageFont.load_default()
            self.font_weekday = ImageFont.load_default()
            self.font_day = ImageFont.load_default()
            self.font_multiple = ImageFont.load_default()

    def _get_cell_image(self, size: int, is_checked: bool):
        if is_checked:
            base_img = Image.new("RGBA", (size, size), (255, 255, 255, 255))

            if self.deer_image:
                deer = self.deer_image.resize((size - 4, size - 4), Image.Resampling.LANCZOS)
                base_img.paste(deer, (2, 2), deer)
            else:
                raise NotImplementedError

            if self.check_image:
                check = self.check_image.resize((size - 4, size - 4), Image.Resampling.LANCZOS)
                base_img.paste(check, (2, 2), check)
            else:
                raise NotImplementedError

            return base_img
        if self.deer_image:
            img = Image.new("RGBA", (size, size), (255, 255, 255, 255))
            deer = self.deer_image.resize((size - 4, size - 4), Image.Resampling.LANCZOS)
            img.paste(deer, (2, 2), deer)
            return img
        raise NotImplementedError

    def generate(self) -> Image.Image:
        cal = calendar.Calendar(firstweekday=6)
        month_days = cal.monthdayscalendar(self.year, self.month)
        rows = len(month_days)

        actual_grid_width = 7 * self.cell_size + 6 * self.gap
        grid_offset_x = (self.width - 2 * self.padding - actual_grid_width) // 2

        height = self.grid_top + rows * self.cell_size + (rows - 1) * self.gap + self.padding

        img = Image.new("RGB", (self.width, height), self.bg_color)
        draw = ImageDraw.Draw(img)

        header_x = self.padding + grid_offset_x
        header_y = self.padding

        month_names = [
            "",
            "1月",
            "2月",
            "3月",
            "4月",
            "5月",
            "6月",
            "7月",
            "8月",
            "9月",
            "10月",
            "11月",
            "12月",
        ]
        header_text = f"{self.year}年{month_names[self.month]} - 签到"
        draw.text((header_x, header_y), header_text, fill=self.header_color, font=self.font_header)

        subheader_text = self.name
        draw.text((header_x, header_y + 60), subheader_text, fill=self.subheader_color, font=self.font_subheader)

        weekdays = ["日", "一", "二", "三", "四", "五", "六"]
        weekday_y = self.grid_top - self.weekday_height

        for i, day in enumerate(weekdays):
            bbox = draw.textbbox((0, 0), day, font=self.font_weekday)
            text_width = bbox[2] - bbox[0]
            x = self.padding + grid_offset_x + i * (self.cell_size + self.gap) + (self.cell_size - text_width) // 2
            draw.text((x, weekday_y), day, fill=self.weekday_color, font=self.font_weekday)

        for week_idx, week in enumerate(month_days):
            for day_idx, day in enumerate(week):
                if day == 0:
                    continue

                x = self.padding + grid_offset_x + day_idx * (self.cell_size + self.gap)
                y = self.grid_top + week_idx * (self.cell_size + self.gap)

                day_str = str(day)
                is_checked = day_str in self.sign_days

                cell_img = self._get_cell_image(self.cell_size, is_checked)
                img.paste(cell_img, (x, y), cell_img)

                shadow_offset = 2
                for dx in range(-shadow_offset, shadow_offset + 1):
                    for dy in range(-shadow_offset, shadow_offset + 1):
                        if dx != 0 or dy != 0:
                            draw.text(
                                (x + 6 + dx, y + self.cell_size - 40 + dy),
                                day_str,
                                fill=(255, 255, 255),
                                font=self.font_day,
                            )
                draw.text(
                    (x + 6, y + self.cell_size - 40),
                    day_str,
                    fill=self.day_number_color,
                    font=self.font_day,
                )

                if is_checked:
                    count = self.sign_days[day_str]
                    sign_text = f"×{count}"
                    for dx in range(-2, 3):
                        for dy in range(-2, 3):
                            if dx != 0 or dy != 0:
                                draw.text(
                                    (x + self.cell_size - 50, y + self.cell_size - 40),
                                    sign_text,
                                    fill=self.multiple_sign_color,
                                    font=self.font_multiple,
                                )

        return img


def create_calendar(
    year: int | None = None,
    month: int | None = None,
    sign_days: Dict[str, int] | None = None,
    deer_image_path: str | None = None,
    check_image_path: str | None = None,
    name: str = "deer_check_in",
) -> Image.Image:
    cal = CheckInCalendar(sign_days, year, month, deer_image_path, check_image_path, name)
    return cal.generate()


def create_leaderboard_image(
    data_dict: Iterable[Tuple[str, dict]],
    output_path: str = "leaderboard.png",
    width: int = 800,
    option: bool = False,
    fixed: int | None = None,
) -> Image.Image:
    sorted_items = list(data_dict)

    bg_color = (30, 30, 40)
    img = Image.new("RGB", (width, 125 + 100 * len(sorted_items)), bg_color)
    draw = ImageDraw.Draw(img)

    try:
        title_font = ImageFont.truetype(str(RES_DIR / "font.ttf"), 36)
        header_font = ImageFont.truetype(str(RES_DIR / "font.ttf"), 24)
        text_font = ImageFont.truetype(str(RES_DIR / "font.ttf"), 20)
        rank_font = ImageFont.truetype(str(RES_DIR / "font.ttf"), 28)
    except Exception:
        title_font = ImageFont.load_default()
        header_font = ImageFont.load_default()
        text_font = ImageFont.load_default()
        rank_font = ImageFont.load_default()

    gold_color = (255, 215, 0)
    silver_color = (192, 192, 192)
    bronze_color = (205, 127, 50)
    text_color = (240, 240, 240)
    sub_text_color = (180, 180, 180)
    accent_color = (100, 150, 255)

    title = "排行榜"
    bbox = draw.textbbox((0, 0), title, font=title_font)
    title_width = bbox[2] - bbox[0]
    draw.text(((width - title_width) // 2, 30), title, fill=text_color, font=title_font)

    header_y = 100
    draw.text((80, header_y), "排名", fill=sub_text_color, font=header_font)
    draw.text((200, header_y), "用户", fill=sub_text_color, font=header_font)
    draw.text((450, header_y), "今日总计" if not option else "当前时长", fill=sub_text_color, font=header_font)
    draw.text((600, header_y), "本月总计" if not option else "历史最高", fill=sub_text_color, font=header_font)

    draw.line([(50, 140), (width - 50, 140)], fill=(60, 60, 80), width=2)

    start_y = 160
    row_height = 70

    for idx, (user_id, data) in enumerate(sorted_items):
        y = start_y + idx * row_height

        center_x = 100
        center_y = y + 25
        radius = 25

        bbox = draw.textbbox((0, 0), str(idx + 1), font=rank_font)
        rank_w = bbox[2] - bbox[0]
        draw.text((center_x - rank_w // 2, center_y - 15), str(idx + 1), fill=text_color, font=rank_font)

        if "name" not in data:
            data["name"] = user_id
        display_id = data["name"][:9] + "..." if len(data["name"]) > 9 else data["name"]
        draw.text((200, y + 15), display_id, fill=text_color, font=text_font)

        nowday = data["nowday"]
        nowday_str = str(nowday)
        if not option:
            nowday_str += " 次"
        else:
            nowday_str = data["nowdayl"]
        if fixed:
            nowday = fixed // 86400
        nowday_color = (100, 255, 150) if nowday >= 7 else accent_color
        bbox = draw.textbbox((0, 0), nowday_str, font=text_font)
        nowday_w = bbox[2] - bbox[0]
        draw.text((480 - nowday_w // 2, y + 15), nowday_str, fill=nowday_color, font=text_font)

        total_str = str(data["total"])
        if not option:
            total_str += " 次"
        else:
            total_str = data["totall"]
        draw.text((620, y + 15), total_str, fill=sub_text_color, font=text_font)

        if idx < len(sorted_items) - 1:
            draw.line([(150, y + 60), (width - 50, y + 60)], fill=(50, 50, 60), width=1)

    img.save(output_path)
    return img
