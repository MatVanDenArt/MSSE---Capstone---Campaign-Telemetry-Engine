def format_date_analytics():
    with open('app/services/analytics.py', 'r', encoding='utf-8') as f:
        content = f.read()

    old_str = "a['date'] = str(a['release_date']).split(\" \")[0]"
    new_str = """a['date'] = str(a['release_date']).split(" ")[0]
            import datetime
            try:
                dt_obj = datetime.datetime.strptime(a['date'], '%Y-%m-%d')
                a['formatted_date'] = dt_obj.strftime('%d %B %Y')
            except:
                a['formatted_date'] = a['date']"""

    if old_str in content:
        content = content.replace(old_str, new_str)
        with open('app/services/analytics.py', 'w', encoding='utf-8') as f:
            f.write(content)
        print("Patched analytics.py")
    else:
        print("String not found")

format_date_analytics()
