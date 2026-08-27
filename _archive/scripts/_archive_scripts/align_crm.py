import sqlite3

def align_crm_opps():
    conn = sqlite3.connect('capstone.db')
    cursor = conn.cursor()
    cursor.execute("UPDATE crm_opps SET timestamp = datetime(timestamp, '-36 days')")
    conn.commit()
    conn.close()
    print("CRM opps aligned.")

align_crm_opps()
