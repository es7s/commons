import datetime
from dataclasses import dataclass
from time import sleep

import pytermor as pt
from pytermor import wait_key

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

    def select(self) -> str:  # @fixme use sun calc
        now = datetime.datetime.now()
        if now.hour == 0:
            return self.extra_icon or self.night_icon
        if now.hour >= 22 or now.hour <= 6:
            return self.night_icon
        return self.day_icon

    def get_raw(self) -> tuple[str, ...]:
        return self.day_icon, self.night_icon, self.extra_icon



class WeatherIconSet:
    NO_COLOR_SET_IDS = [0]

    def __init__(self, color_code: int, *icons: str | tuple[str, ...], wwo_codes: list[str]):
        self._style: pt.Style = pt.Style(fg=pt.Color256.get_by_code(color_code))
        self._icons: list[str | DynamicIcon] = [
            s if isinstance(s, str) else DynamicIcon(*s) for s in icons
        ]
        self._wwo_codes: list[str] = wwo_codes

    def get_icon(self, set_id: int) -> tuple[str, pt.Style]:
        if set_id >= len(self._icons):
            raise IndexError(f"Set #{set_id} is undefined")

        icon = self._icons[set_id]
        if isinstance(icon, DynamicIcon):
            icon = icon.select()

        if set_id in self.NO_COLOR_SET_IDS:
            return icon, pt.NOOP_STYLE
        return icon, self._style

    def get_raw(self, set_id: int) -> str|tuple[str]:
        if set_id >= len(self._icons):
            raise IndexError(f"Set #{set_id} is undefined")
        icon = self._icons[set_id]
        if isinstance(icon, DynamicIcon):
            return icon.get_raw()
        return icon


# fmt: off
WEATHER_ICON_SETS: dict[str, WeatherIconSet] = {  # @FIXME compensate various width
     "✨": WeatherIconSet(248,	"✨️",	"",	"",	"",	("",	"",	""),	wwo_codes=["Unknown"]),
    "☀": WeatherIconSet(248,	"☀️",	"滛",	"滛",	"",	("",	"望",	""),	wwo_codes=["Sunny"]),
     "☁": WeatherIconSet(248,	"☁️",	"摒",	"摒",	"",	("",	""),			wwo_codes=["Cloudy", "VeryCloudy"]),
    "⛅": WeatherIconSet(248,	"⛅️",	"杖",	"杖",	"",	("",	""), 			wwo_codes=["PartlyCloudy"]),
    "🌫": WeatherIconSet(248,	"🌫️",	"敖",	"敖",	"",	("",	""), 			wwo_codes=["Fog"]),
    "🌦": WeatherIconSet( 27,	"🌦️",	"",	"殺",	"",	("",	""), 			wwo_codes=["LightRain", "LightShowers"]),
    "🌧": WeatherIconSet( 27,	"🌧️",	"",	"殺",	"",	("",	""), 			wwo_codes=["HeavyRain", "HeavyShowers", "LightSleet", "LightSleetShowers"]),
    "⛈": WeatherIconSet(229,	"⛈️",	"",	"ﭼ",	"",	("",	""), 			wwo_codes=["ThunderyShowers", "ThunderySnowShowers"]),
    "🌩": WeatherIconSet(229,	"🌩️",	"",	"朗",	"",	("",	""),			wwo_codes=["ThunderyHeavyRain"]),
    "🌨": WeatherIconSet(153,	"🌨️",	"ﰕ",	"流",	"",	("",	""),			wwo_codes=["LightSnow", "LightSnowShowers"]),
     "❄": WeatherIconSet(153,	"❄️",	"",	"",	"",	("",	""),			wwo_codes=["HeavySnow", "HeavySnowShowers"]),
}

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


def format_weather_icon(origin: str, set_id: int = 0) -> tuple[str, pt.Style]:
    for key, icon_set in WEATHER_ICON_SETS.items():
        if key == origin:
            return icon_set.get_icon(set_id)
    return origin, pt.NOOP_STYLE



import sys, unicodedata


def measure(icon: str):
    response = ""
    print("\x1b[32m"+icon+"\x1b[6n", end='\x1b[34m')
    sleep(.2)
    while not response.endswith('R'):
        response += sys.stdin.read(1) #wait_key()
    print(pt.ansi.make_erase_in_line(2).assemble()+pt.ansi.make_set_cursor_x_abs(1).assemble(), end='\x1b[m')
    print(f"{ord(icon):6x}" + '| ' + response.split(';')[1].removesuffix('R').strip()+ ' |'+pt.render(icon, pt.Style(fg='green', bg='black'))+'|', end='\n', file=sys.stderr)

def iterate():
    for weather_icon, weather_icon_set in WEATHER_ICON_SETS.items():
        for icon_set_id in range(0, 5):
            icons = weather_icon_set.get_raw(icon_set_id)
            for icon in icons:
                if not icon: continue
                measure(icon)
