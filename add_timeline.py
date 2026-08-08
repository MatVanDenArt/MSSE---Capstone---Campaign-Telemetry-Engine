with open('app/templates/components/overview.html', 'r', encoding='utf-8') as f:
    content = f.read()

if 'mod_asset_timeline' not in content:
    content = content.replace("{% include 'components/mod_persona_matrix.html' %}", "{% include 'components/mod_persona_matrix.html' %}\n{% include 'components/mod_asset_timeline.html' %}")

    with open('app/templates/components/overview.html', 'w', encoding='utf-8') as f:
        f.write(content)
