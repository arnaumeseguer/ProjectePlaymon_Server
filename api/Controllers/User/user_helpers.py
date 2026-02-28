USER_SELECT = """
    id, username, name, email, role, is_active, created_at, updated_at, avatar
"""
def row_to_user(r):
    return {
        "id": r[0],
        "username": r[1],
        "name": r[2],
        "email": r[3],
        "role": r[4],
        "is_active": r[5],
        "created_at": r[6].isoformat() if r[6] else None,
        "updated_at": r[7].isoformat() if r[7] else None,
        "avatar": r[8],
    }