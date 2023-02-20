import dataclasses

BASE_URLS = ("https://if192.aca.ntu.edu.tw/", "https://if177.aca.ntu.edu.tw/")


@dataclasses.dataclass
class SessionInfo:
    regno: str
    lang: str
    extid: str


SESSION_INFO_LANG_CHINESE = "tw"
SESSION_INFO_LANG_ENGLISH = "en"
