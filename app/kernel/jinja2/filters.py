from datetime import date, datetime


def dmy(value):
    """
    Форматирует value (дата в формат dd.mm.YYYY
    """
    if isinstance(value, (date, datetime)):
        return value.strftime('%d.%m.%Y')
    else:
        return value


def dmyt(value):
    """
    Форматирует value (дата и время) в формате dd.mm.YYYY HH:MM:SS
    """
    if isinstance(value, (date, datetime)):
        return value.strftime('%d.%m.%Y %H:%M:%S')
    else:
        return value


def zfill(value, zlen):
    """
    Добавляет в начале строки нули, пока длина value не дойдет до zlen
    """
    return str(value).zfill(zlen)


def get_filters():
    return {
        'dmy': dmy,
        'dmyt': dmyt,
        'zfill': zfill,
    }
