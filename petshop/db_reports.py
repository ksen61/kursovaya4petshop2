from django.db import connection

def get_orders_report(product_id=None, category_id=None, brand_id=None, user_id=None):
    with connection.cursor() as cursor:
        cursor.execute("""
            SELECT * FROM get_orders_report(%s, %s, %s, %s);
        """, [product_id, category_id, brand_id, user_id])
        columns = [col[0] for col in cursor.description]
        results = [dict(zip(columns, row)) for row in cursor.fetchall()]
    return results

def get_orders_by_day(date):
    with connection.cursor() as cursor:
        cursor.execute("SELECT * FROM get_orders_by_day(%s);", [date])
        columns = [col[0] for col in cursor.description]
        return [dict(zip(columns, row)) for row in cursor.fetchall()]

def get_orders_by_week(date):
    with connection.cursor() as cursor:
        cursor.execute("SELECT * FROM get_orders_by_week(%s);", [date])
        columns = [col[0] for col in cursor.description]
        return [dict(zip(columns, row)) for row in cursor.fetchall()]

def get_orders_by_month(date):
    with connection.cursor() as cursor:
        cursor.execute("SELECT * FROM get_orders_by_month(%s);", [date])
        columns = [col[0] for col in cursor.description]
        return [dict(zip(columns, row)) for row in cursor.fetchall()]