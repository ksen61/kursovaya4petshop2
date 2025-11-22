import os
import time
import json
import zipfile
import tempfile
from datetime import datetime, date
from decimal import Decimal
from django.core.management.base import BaseCommand
from django.conf import settings
from django.db import connection

BACKUP_DIR = os.path.join(settings.MEDIA_ROOT, 'backups')
MAX_AGE_DAYS = 7  

TABLES_TO_BACKUP = [
    'petshop_role', 'petshop_user', 'petshop_userprofile',
    'petshop_category', 'petshop_brand', 'petshop_agecategory',
    'petshop_species', 'petshop_producttype', 'petshop_purpose',
    'petshop_product', 'petshop_productpurpose', 'petshop_pickuppoint',
    'petshop_productstock', 'petshop_cart', 'petshop_order',
    'petshop_orderitem', 'petshop_review', 'petshop_auditlog'
]

class Command(BaseCommand):
    def handle(self, *args, **options):
        os.makedirs(BACKUP_DIR, exist_ok=True)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        zip_filename = f'backup_{timestamp}.zip'
        zip_filepath = os.path.join(BACKUP_DIR, zip_filename)

        backup_data = {
            'metadata': {'created_at': datetime.now().isoformat()},
            'tables': {}
        }

        with connection.cursor() as cursor:
            for table in TABLES_TO_BACKUP:
                cursor.execute(f"SELECT * FROM {table}")
                columns = [col[0] for col in cursor.description]
                rows = cursor.fetchall()
                table_data = []

                for row in rows:
                    row_dict = {}
                    for i, col in enumerate(columns):
                        value = row[i]
                        if isinstance(value, (datetime, date)):
                            row_dict[col] = value.isoformat()
                        elif isinstance(value, Decimal):
                            row_dict[col] = float(value)
                        else:
                            row_dict[col] = value
                    table_data.append(row_dict)

                backup_data['tables'][table] = {
                    'columns': columns,
                    'data': table_data,
                    'count': len(table_data)
                }

        backup_data['metadata']['total_tables'] = len(backup_data['tables'])

        with tempfile.TemporaryDirectory() as temp_dir:
            json_path = os.path.join(temp_dir, f'backup_{timestamp}.json')
            with open(json_path, 'w', encoding='utf-8') as f:
                json.dump(backup_data, f, ensure_ascii=False, indent=2)

            sql_path = os.path.join(temp_dir, f'backup_{timestamp}.sql')
            db_settings = settings.DATABASES['default']
            pg_dump_path = "/opt/homebrew/opt/postgresql@17/bin/pg_dump"
            dump_command = (
                f'{pg_dump_path} -h {db_settings["HOST"]} -p {db_settings["PORT"]} '
                f'-U {db_settings["USER"]} -F p -b -v -f "{sql_path}" {db_settings["NAME"]}'
            )
            result = os.system(dump_command)
            if result != 0:
                self.stdout.write(self.style.ERROR("❌ Ошибка при создании SQL дампа"))
                return

            with zipfile.ZipFile(zip_filepath, 'w', zipfile.ZIP_DEFLATED) as zf:
                zf.write(json_path, os.path.basename(json_path))
                zf.write(sql_path, os.path.basename(sql_path))

        self.stdout.write(self.style.SUCCESS(f"✅ Бэкап успешно создан: {zip_filepath}"))

        self.clean_old_backups()

    def clean_old_backups(self):
        for filename in os.listdir(BACKUP_DIR):
            file_path = os.path.join(BACKUP_DIR, filename)
            if os.path.isfile(file_path):
                file_age_days = (time.time() - os.path.getmtime(file_path)) / 86400
                if file_age_days > MAX_AGE_DAYS:
                    os.remove(file_path)
                    self.stdout.write(f"🗑️ Удалён старый бэкап: {filename}")