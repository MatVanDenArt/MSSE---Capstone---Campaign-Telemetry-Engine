def update_overview():
    with open('app/templates/components/overview.html', 'r', encoding='utf-8') as f:
        content = f.read()

    content = content.replace("{% include 'components/mod_audience_journey.html' %}", "{% include 'components/mod_user_cards.html' %}")

    with open('app/templates/components/overview.html', 'w', encoding='utf-8') as f:
        f.write(content)

update_overview()
