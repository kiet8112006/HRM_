from database import get_connection

def create_notification(
        title,
        message,
        type="Info",
        receiver_role=None,
        receiver_id=None,
        url=None):

    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        INSERT INTO Notifications
        (
            Title,
            Message,
            Type,
            ReceiverRole,
            ReceiverID,
            Url
        )
        VALUES (?, ?, ?, ?, ?, ?)
    """,
    title,
    message,
    type,
    receiver_role,
    receiver_id,
    url)

    conn.commit()
    conn.close()