def revert_thresholds():
    with open('app/templates/components/mod_user_cards.html', 'r', encoding='utf-8') as f:
        content = f.read()

    # Revert logic for SQL / MQL
    content = content.replace("user.interactions >= 5", "user.interactions > 8")
    content = content.replace("user.interactions >= 2", "user.interactions > 3")
    content = content.replace("Cold Prospect", "Cold Lead")

    with open('app/templates/components/mod_user_cards.html', 'w', encoding='utf-8') as f:
        f.write(content)

revert_thresholds()
