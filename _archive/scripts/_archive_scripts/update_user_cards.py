def update_user_cards():
    with open('app/templates/components/mod_user_cards.html', 'r', encoding='utf-8') as f:
        content = f.read()

    # Update logic for SQL / MQL
    content = content.replace("user.interactions > 8", "user.interactions >= 5")
    content = content.replace("user.interactions > 3", "user.interactions >= 2")
    content = content.replace("Cold Lead", "Cold Prospect")

    with open('app/templates/components/mod_user_cards.html', 'w', encoding='utf-8') as f:
        f.write(content)

update_user_cards()
