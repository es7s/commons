# ------------------------------------------------------------------------------
#  es7s/core
#  (c) 2023 A. Shavykin <0.delameter@gmail.com>
# ------------------------------------------------------------------------------

import datetime
from dataclasses import dataclass

import pytermor as pt

WWO_CODE = {
    "113": "Sunny",
    "116": "PartlyCloudy",
    "119": "Cloudy",
    "122": "VeryCloudy",
    "143": "Fog",
    "176": "LightShowers",
    "179": "LightSleetShowers",
    "182": "LightSleet",
    "185": "LightSleet",
    "200": "ThunderyShowers",
    "227": "LightSnow",
    "230": "HeavySnow",
    "248": "Fog",
    "260": "Fog",
    "263": "LightShowers",
    "266": "LightRain",
    "281": "LightSleet",
    "284": "LightSleet",
    "293": "LightRain",
    "296": "LightRain",
    "299": "HeavyShowers",
    "302": "HeavyRain",
    "305": "HeavyShowers",
    "308": "HeavyRain",
    "311": "LightSleet",
    "314": "LightSleet",
    "317": "LightSleet",
    "320": "LightSnow",
    "323": "LightSnowShowers",
    "326": "LightSnowShowers",
    "329": "HeavySnow",
    "332": "HeavySnow",
    "335": "HeavySnowShowers",
    "338": "HeavySnow",
    "350": "LightSleet",
    "353": "LightShowers",
    "356": "HeavyShowers",
    "359": "HeavyRain",
    "362": "LightSleetShowers",
    "365": "LightSleetShowers",
    "368": "LightSnowShowers",
    "371": "HeavySnowShowers",
    "374": "LightSleetShowers",
    "377": "LightSleet",
    "386": "ThunderyShowers",
    "389": "ThunderyHeavyRain",
    "392": "ThunderySnowShowers",
    "395": "HeavySnowShowers",
}


@dataclass
class DynamicIcon:
    day_icon: str
    night_icon: str
    extra_icon: str | None = None

    def select(self, override_hour: int = None) -> str:  # @fixme use sun calc
        eff_hour = override_hour or datetime.datetime.now().hour
        if eff_hour == 0:
            return self.extra_icon or self.night_icon
        if eff_hour >= 22 or eff_hour <= 6:
            return self.night_icon
        return self.day_icon

    def get_raw(self) -> tuple[str, ...]:
        return tuple(filter(None, (self.day_icon, self.night_icon, self.extra_icon)))


class WeatherIconSet:
    NO_COLOR_SET_IDS = [0]
    MAX_SET_ID = 0

    def __init__(self, color_code: int, *icons: str | tuple[str, ...], wwo_codes: list[str]):
        self._style: pt.Style = pt.Style(fg=pt.Color256.get_by_code(color_code))
        self._icons: list[str | DynamicIcon] = [
            s if isinstance(s, str) else DynamicIcon(*s) for s in icons
        ]
        self._wwo_codes: list[str] = wwo_codes
        WeatherIconSet.MAX_SET_ID = max(WeatherIconSet.MAX_SET_ID, len(self._icons) - 1)

    def get_icon(self, set_id: int, override_hour: int = None) -> tuple[str, str, pt.Style]:
        """
        :return: (icon, terminator, style)
        """
        if set_id < 0 or set_id >= WeatherIconSet.MAX_SET_ID:
            raise IndexError(f"Set #{set_id} is undefined")

        icon = self._icons[set_id]
        if isinstance(icon, DynamicIcon):
            icon = icon.select(override_hour)
        icon = ljust_unicode_aware(icon)

        if set_id in self.NO_COLOR_SET_IDS:
            return icon, WEATHER_ICON_TERMINATOR, pt.NOOP_STYLE
        return icon, WEATHER_ICON_TERMINATOR, self._style

    def get_raw(self, set_id: int) -> tuple[str]:
        if set_id < 0 or set_id >= WeatherIconSet.MAX_SET_ID:
            raise IndexError(f"Set #{set_id} is undefined")
        icon = self._icons[set_id]
        if isinstance(icon, DynamicIcon):
            return icon.get_raw()
        return icon,


# fmt: off
WEATHER_ICON_SETS: dict[str, WeatherIconSet] = {
    "✨": WeatherIconSet(248,	"✨️",	"",	"",	"",	("",	"",	""),	wwo_codes=["Unknown"]),
    "☀": WeatherIconSet(248,	"☀️",	"滛",	"滛",	"",	("",	"望",	""),	wwo_codes=["Sunny"]),
    "☁":  WeatherIconSet(248,	"☁️",	"摒",	"摒",	"",	("",	""),			wwo_codes=["Cloudy", "VeryCloudy"]),
    "⛅": WeatherIconSet(248,	"⛅️",	"杖",	"杖",	"",	("",	""), 			wwo_codes=["PartlyCloudy"]),
    "🌫": WeatherIconSet(248,	"🌫️",	"敖",	"敖",	"",	("",	""), 			wwo_codes=["Fog"]),
    "🌦": WeatherIconSet( 27,	"🌦️",	"",	"殺",	"",	("",	""), 			wwo_codes=["LightRain", "LightShowers"]),
    "🌧": WeatherIconSet( 27,	"🌧️",	"",	"殺",	"",	("",	""), 			wwo_codes=["HeavyRain", "HeavyShowers", "LightSleet", "LightSleetShowers"]),
    "⛈": WeatherIconSet(229,	"⛈️",	"",	"ﭼ",	"",	("",	""), 			wwo_codes=["ThunderyShowers", "ThunderySnowShowers"]),
    "🌩": WeatherIconSet(229,	"🌩️",	"",	"朗",	"",	("",	""),			wwo_codes=["ThunderyHeavyRain"]),
    "🌨": WeatherIconSet(153,	"🌨️",	"ﰕ",	"流",	"",	("",	""),			wwo_codes=["LightSnow", "LightSnowShowers"]),
    "❄": WeatherIconSet(153,	"❄️",	"",	"",	"",	("",	""),			wwo_codes=["HeavySnow", "HeavySnowShowers"]),
}

WEATHER_ICON_WIDTH = {
    "✨": 2,
    "✨️": 3,
    "": 2,
    "☀": 2,
    "☀️": 3,
    "滛": 3,
    "": 2,
    "☁": 2,
    "☁️": 3,
    "摒": 3,
    "": 2,
    "⛅": 2,
    "⛅️": 3,
    "杖": 3,
    "": 2,
    "🌫": 3,
    "🌫️": 4,
    "敖": 3,
    "": 2,
    "🌦": 3,
    "🌦️": 4,
    "": 2,
    "": 2,
    "🌧": 3,
    "🌧️": 4,
    "": 2,
    "殺": 3,
    "": 2,
    "⛈": 2,
    "⛈️": 3,
    "ﭼ": 2,
    "": 2,
    "🌩": 3,
    "🌩️": 4,
    "": 2,
    "朗": 3,
    "": 2,
    "🌨": 3,
    "🌨️": 4,
    "ﰕ": 2,
    "流": 3,
    "": 2,
    "❄": 2,
    "❄️": 3,
    "": 2,
}

WEATHER_ICON_TERMINATOR = '\u200e'
# Unicode LRM to force disable right-to-left
# mode after some icons getting printed

WIND_DIRECTION = ["↓", "↙", "←", "↖", "↑", "↗", "→", "↘"]

WEATHER_SYMBOL_PLAIN = {
    "Unknown":				"?",
    "Cloudy":				"mm",
    "Fog":					"=",
    "HeavyRain":			"///",
    "HeavyShowers":			"//",
    "HeavySnow":			"**",
    "HeavySnowShowers":		"*/*",
    "LightRain":			"/",
    "LightShowers":			".",
    "LightSleet":			"x",
    "LightSleetShowers":	"x/",
    "LightSnow":			"*",
    "LightSnowShowers":		"*/",
    "PartlyCloudy":			"m",
    "Sunny":				"o",
    "ThunderyHeavyRain":	"/!/",
    "ThunderyShowers":		"!/",
    "ThunderySnowShowers":	"*!*",
    "VeryCloudy":			"mmm",
}
# fmt: on


def format_weather_icon(origin: str, set_id: int = 0) -> tuple[str, str, pt.Style]:
    """
    :param set_id:
    :param origin: initial icon (wttr.in)
    :return: (updated-icon, string terminator, style)
    """
    if icon_set := WEATHER_ICON_SETS.get(origin, None):
        try:
            return icon_set.get_icon(set_id)
        except IndexError:
            pass
    return ljust_unicode_aware(origin), "", pt.NOOP_STYLE


def get_raw_weather_icons(origin: str, set_id: int = 0) -> tuple[str]:
    if icon_set := WEATHER_ICON_SETS.get(origin, None):
        try:
            return icon_set.get_raw(set_id)
        except IndexError:
            pass
    return origin,


def ljust_unicode_aware(icon: str) -> str:
    max_icon_width = max(WEATHER_ICON_WIDTH.values())
    if icon in WEATHER_ICON_WIDTH.keys():
        return icon + ' '*(max_icon_width - WEATHER_ICON_WIDTH[icon])
    return icon + ' '*(max_icon_width - 1)
