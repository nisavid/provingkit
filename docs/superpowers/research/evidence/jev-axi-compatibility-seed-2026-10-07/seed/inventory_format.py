HEADER = "sku\twarehouse\ton_hand\n"


def render_text(items):
    return HEADER + "".join(f"{item['sku']}\t{item['warehouse']}\t{item['on_hand']}\n" for item in items)
