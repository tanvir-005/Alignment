def display_name(user) -> str:
    if user is None:
        return "Someone"
    full = user.get_full_name().strip()
    return full or user.username
