# from datetime import datetime
#
# import pymysql.cursors
#
# from credentials import db_config as db
#
# current_date = str(datetime.now().strftime("%Y-%m-%d"))
# con = db.get_db_connection()
# cur = con.cursor(pymysql.cursors.DictCursor)
# cur.execute(f"select * from {db.project_data} where status='pending' and ")
# all_projects = cur.fetchall()
#
