def text(element):
    return element.get_text(" ", strip=True) if element else None


def attr(element, name):
    return element.get(name) if element else None


def parse_detail(doc):
    rows = doc.select(".detail-parameters tr")
    schedule = doc.select(".detail-schedule-row")
    return {
        "description": text(doc.select_one(".detail-parameters + .mb-10 .position-relative > div")),
        "availability": text(doc.select_one(".detail-availability-status")),
        "phone": attr(doc.select_one(".card-contact a[href^='tel:']"), "href"),
        "parameters": [
            {"label": text(row.select_one("th")), "value": text(row.select_one("td"))}
            for row in rows
        ],
        "services": [text(element) for element in doc.select(".detail-label")],
        "schedule": [
            {"day": text(row.select_one(".detail-schedule-day")),
             "hours": text(row.select_one(".detail-schedule-hours"))}
            for row in schedule
        ],
        "images": [element.get("data-src") for element in doc.select(".detail-swiper-item")],
    }
