with open('app/templates/components/overview.html', 'r', encoding='utf-8') as f:
    content = f.read()

# Insert the missing modules before the timeline
insertion = """
    <div class="grid grid-cols-1 lg:grid-cols-2 gap-6 mt-6">
        {% include 'components/mod_channel_roi.html' %}
        {% include 'components/mod_velocity_funnel.html' %}
    </div>
    {% include 'components/mod_activity_pulse.html' %}
"""

content = content.replace("<!-- Interactive Timeline -->", insertion + "\n    <!-- Interactive Timeline -->")

with open('app/templates/components/overview.html', 'w', encoding='utf-8') as f:
    f.write(content)
