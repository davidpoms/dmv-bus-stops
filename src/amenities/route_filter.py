import re


def extract_wmata_routes(route_string):
    """
    Extract WMATA Metrobus routes from Montgomery ROUTES field.

    WMATA routes after Better Bus redesign use
    letter-number identifiers:
    M83, C83, P30, D10, etc.
    """

    if not route_string:
        return []

    matches = re.findall(
        r"\b[A-Z][0-9]+\b",
        route_string.upper()
    )

    return sorted(set(matches))


def has_wmata_route(route_string):

    return len(
        extract_wmata_routes(route_string)
    ) > 0