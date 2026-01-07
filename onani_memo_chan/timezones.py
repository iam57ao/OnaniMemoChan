from dataclasses import dataclass


@dataclass(frozen=True)
class TimezoneOption:
    label: str
    iana: str


TIMEZONE_PAGES: list[list[TimezoneOption]] = [
    [
        TimezoneOption("UTC-12", "Etc/GMT+12"),
        TimezoneOption("UTC-11", "Etc/GMT+11"),
        TimezoneOption("UTC-10", "Etc/GMT+10"),
        TimezoneOption("UTC-9", "Etc/GMT+9"),
        TimezoneOption("UTC-8", "Etc/GMT+8"),
        TimezoneOption("UTC-7", "Etc/GMT+7"),
        TimezoneOption("UTC-6", "Etc/GMT+6"),
        TimezoneOption("UTC-5", "Etc/GMT+5"),
    ],
    [
        TimezoneOption("UTC-4", "Etc/GMT+4"),
        TimezoneOption("UTC-3", "Etc/GMT+3"),
        TimezoneOption("UTC-2", "Etc/GMT+2"),
        TimezoneOption("UTC-1", "Etc/GMT+1"),
        TimezoneOption("UTC+0", "Etc/GMT"),
        TimezoneOption("UTC+1", "Etc/GMT-1"),
        TimezoneOption("UTC+2", "Etc/GMT-2"),
        TimezoneOption("UTC+3", "Etc/GMT-3"),
    ],
    [
        TimezoneOption("UTC+4", "Etc/GMT-4"),
        TimezoneOption("UTC+5", "Etc/GMT-5"),
        TimezoneOption("UTC+6", "Etc/GMT-6"),
        TimezoneOption("UTC+7", "Etc/GMT-7"),
        TimezoneOption("UTC+8", "Etc/GMT-8"),
        TimezoneOption("UTC+9", "Etc/GMT-9"),
        TimezoneOption("UTC+10", "Etc/GMT-10"),
        TimezoneOption("UTC+11", "Etc/GMT-11"),
    ],
    [
        TimezoneOption("UTC+12", "Etc/GMT-12"),
        TimezoneOption("UTC+13", "Etc/GMT-13"),
        TimezoneOption("UTC+14", "Etc/GMT-14"),
    ],
]

DEFAULT_TIMEZONE_PAGE = 2

TIMEZONE_LABEL_BY_IANA = {
    option.iana: option.label for page in TIMEZONE_PAGES for option in page
}
