import os
import sys
import getpass
import pymysql

print("Starting direct migration from Aiven MySQL to Alwaysdata MySQL...")

aiven_pwd = os.getenv("AIVEN_PASSWORD") or getpass.getpass("Enter your Aiven MySQL password: ")
alwaysdata_pwd = os.getenv("ALWAYSDATA_PASSWORD") or getpass.getpass("Enter your Alwaysdata MySQL password: ")

aiven_config = {
    'host': 'mysql-2899bd7a-qrioustechacademy.i.aivencloud.com',
    'port': 18581,
    'user': 'avnadmin',
    'password': aiven_pwd,
    'database': 'defaultdb',
    'ssl': {'ssl_mode': 'REQUIRED'},
    'charset': 'utf8mb4',
    'autocommit': True,
    'read_timeout': 300,
    'write_timeout': 300,
    'connect_timeout': 60
}

alwaysdata_config = {
    'host': 'mysql-qrioustech.alwaysdata.net',
    'port': 3306,
    'user': 'qrioustech',
    'password': alwaysdata_pwd,
    'database': 'qrioustech_db',
    'charset': 'utf8mb4',
    'autocommit': True,
    'read_timeout': 300,
    'write_timeout': 300,
    'connect_timeout': 60
}

aiven_conn = None
always_conn = None

try:
    print("Connecting to Alwaysdata MySQL...")
    always_conn = pymysql.connect(**alwaysdata_config)
    print("Connected to Alwaysdata MySQL!")

    print("Connecting to Aiven MySQL...")
    aiven_conn = pymysql.connect(**aiven_config)
    print("Connected to Aiven MySQL!")

    aiven_cur = aiven_conn.cursor()
    always_cur = always_conn.cursor()

    always_cur.execute("SET FOREIGN_KEY_CHECKS=0;")
    always_cur.execute("SET SQL_MODE='ANSI_QUOTES';")

    # Fetch tables
    aiven_cur.execute("SHOW FULL TABLES WHERE Table_type = 'BASE TABLE';")
    tables = [row[0] for row in aiven_cur.fetchall()]
    print(f"\nFound {len(tables)} tables to migrate from Aiven.\n")

    for idx, table in enumerate(tables, 1):
        print(f"[{idx}/{len(tables)}] Migrating table: {table}...")
        
        # Ensure connections are active
        try:
            aiven_conn.ping(reconnect=True)
            always_conn.ping(reconnect=True)
        except Exception:
            aiven_conn = pymysql.connect(**aiven_config)
            always_conn = pymysql.connect(**alwaysdata_config)
            aiven_cur = aiven_conn.cursor()
            always_cur = always_conn.cursor()

        aiven_cur.execute(f'SHOW CREATE TABLE "{table}";')
        create_stmt = aiven_cur.fetchone()[1]

        always_cur.execute(f'DROP TABLE IF EXISTS "{table}";')
        always_cur.execute(create_stmt)

        aiven_cur.execute(f'SELECT * FROM "{table}";')
        rows = aiven_cur.fetchall()
        if not rows:
            print("   -> 0 rows.")
            continue

        aiven_cur.execute(f'SHOW COLUMNS FROM "{table}";')
        columns = [row[0] for row in aiven_cur.fetchall()]
        col_names = ", ".join([f'"{c}"' for c in columns])
        placeholders = ", ".join(["%s"] * len(columns))
        insert_sql = f'INSERT INTO "{table}" ({col_names}) VALUES ({placeholders})'

        # Batch insert
        batch_size = 20
        for i in range(0, len(rows), batch_size):
            batch = rows[i:i + batch_size]
            always_cur.executemany(insert_sql, batch)

        print(f"   -> Inserted {len(rows)} rows.")

    always_cur.execute("SET FOREIGN_KEY_CHECKS=1;")
    print("\nSUCCESS! ALL TABLES AND DATA MIGRATED FROM AIVEN TO ALWAYSDATA!")

except Exception as e:
    print(f"\nError during migration: {e}")
    sys.exit(1)
finally:
    if aiven_conn:
        try:
            aiven_conn.close()
        except Exception:
            pass
    if always_conn:
        try:
            always_conn.close()
        except Exception:
            pass
