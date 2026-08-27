import re

def update_timeline_again():
    with open('app/templates/components/timeline.html', 'r', encoding='utf-8') as f:
        content = f.read()

    new_loop = """                {% for m in matrix %}
                <div class="relative bg-dark-800/40 border-l-4 {% if m.type == 'Web' %}border-l-fuchsia-500{% elif m.type == 'LinkedIn' %}border-l-brand-500{% else %}border-l-indigo-500{% endif %} rounded-r-xl rounded-l-sm p-5 hover:bg-dark-800/60 transition shadow-[0_4px_20px_rgba(0,0,0,0.2)] overflow-hidden group flex flex-col justify-between"
                     x-data="{
                        sparkline: {{ m.sparkline | default([]) | tojson | safe }},
                        initSparkline() {
                            if (!this.$refs.canvas || this.sparkline.length === 0) return;
                            const ctx = this.$refs.canvas.getContext('2d');
                            new Chart(ctx, {
                                type: 'line',
                                data: {
                                    labels: Array.from({length: this.sparkline.length}, (_, i) => i + 1),
                                    datasets: [{
                                        data: this.sparkline,
                                        borderColor: '{{ m.sparkline_color | default('#10b981') }}',
                                        backgroundColor: '{{ m.sparkline_color | default('#10b981') }}33',
                                        borderWidth: 3,
                                        tension: 0.4,
                                        fill: true,
                                        pointRadius: 0
                                    }]
                                },
                                options: {
                                    responsive: true,
                                    maintainAspectRatio: false,
                                    plugins: { legend: { display: false }, tooltip: { enabled: false } },
                                    scales: {
                                        x: { display: false },
                                        y: { display: false, min: -1 }
                                    },
                                    layout: { padding: { top: 10, bottom: -5 } }
                                }
                            });
                        }
                     }" x-init="initSparkline()">
                    
                    <!-- Background Sparkline Chart -->
                    <div class="absolute inset-0 w-full h-full opacity-40 pointer-events-none z-0">
                        <canvas x-ref="canvas"></canvas>
                    </div>

                    <div class="flex flex-col md:flex-row justify-between items-start md:items-center gap-4 relative z-10">
                        
                        <!-- Left: Asset Info -->
                        <div class="flex flex-col gap-1">
                            <div class="flex items-center gap-3 mb-1">
                                <span class="text-[10px] uppercase font-bold tracking-wider px-2 py-0.5 rounded-full {% if m.type == 'Web' %}bg-fuchsia-500/20 text-fuchsia-300{% elif m.type == 'LinkedIn' %}bg-brand-500/20 text-brand-300{% else %}bg-indigo-500/20 text-indigo-300{% endif %}">
                                    {{ m.type }} ASSET
                                </span>
                                <span class="text-[10px] px-2 py-0.5 font-bold rounded border {{ m.badge_class | default('bg-slate-800 text-slate-400 border-slate-700') }}">
                                    {% if m.health == 'Action Required' %}Fatigued{% else %}{{ m.health | default('Unknown') }}{% endif %}
                                </span>
                            </div>
                            
                            <h5 class="text-base font-bold text-slate-100">{{ m.asset_name }}</h5>
                            <div class="flex items-center gap-3 mt-0.5 text-xs">
                                <span class="text-slate-500 font-mono"><i class="fa-regular fa-calendar mr-1"></i>{{ m.date }}</span>
                            </div>
                        </div>

                        <!-- Right: Performance Metrics -->
                        <div class="flex items-center gap-6 w-full md:w-auto justify-between md:justify-end bg-dark-900/40 px-4 py-2 rounded-lg backdrop-blur-sm border border-dark-700/50">
                            
                            <!-- Engagement -->
                            <div class="text-center">
                                <div class="text-[10px] uppercase font-bold text-slate-500 tracking-wider mb-0.5">{% if m.type == 'Web' %}Views{% elif m.type == 'LinkedIn' %}Clicks{% else %}Opens{% endif %}</div>
                                <div class="text-xl font-bold text-slate-100">{{ "{:,}".format(m.engagement) }}</div>
                            </div>
                            <div class="w-px h-8 bg-dark-700/50"></div>
                            
                            <!-- Individuals -->
                            <div class="text-center">
                                <div class="text-[10px] uppercase font-bold text-slate-500 tracking-wider mb-0.5">Individuals</div>
                                <div class="text-xl font-bold text-slate-100">{{ m.individuals_engaged }}</div>
                            </div>
                            <div class="w-px h-8 bg-dark-700/50"></div>
                            
                            <!-- Accounts -->
                            <div class="text-center">
                                <div class="text-[10px] uppercase font-bold text-slate-500 tracking-wider mb-0.5">Accounts</div>
                                <div class="text-xl font-bold text-slate-100">{{ m.accounts_activated }}</div>
                            </div>
                            <div class="w-px h-8 bg-dark-700/50"></div>
                            
                            <!-- Pipeline Influenced -->
                            <div class="text-right min-w-[100px]">
                                <div class="text-[10px] uppercase font-bold text-slate-500 tracking-wider mb-0.5">Pipeline</div>
                                <div class="text-2xl font-black text-white">{{ m.pipeline_formatted }}</div>
                            </div>

                        </div>
                    </div>
                    
                    <!-- AI Recommendation (Pillar 3) -->
                    {% if m.ai_recommendation %}
                    <div class="relative z-10 mt-5 pt-3 border-t border-dark-700/50 flex flex-col md:flex-row md:items-center justify-between gap-4">
                        <div class="flex items-center gap-3">
                            <div class="w-6 h-6 rounded-full bg-brand-500/10 flex items-center justify-center flex-shrink-0">
                                <i class="fa-solid fa-wand-magic-sparkles text-brand-400 text-[10px]"></i>
                            </div>
                            <p class="text-xs font-medium text-slate-400">{{ m.ai_recommendation }}</p>
                        </div>
                        <button class="px-4 py-1.5 rounded-lg bg-dark-700 hover:bg-dark-600 text-[10px] font-bold tracking-wider text-slate-300 uppercase transition border border-dark-600 whitespace-nowrap">
                            Take Action <i class="fa-solid fa-arrow-right ml-1"></i>
                        </button>
                    </div>
                    {% endif %}
                </div>
                {% endfor %}"""

    start_tag = "{% for m in matrix %}"
    end_tag = "{% endfor %}"
    
    start_idx = content.find(start_tag)
    end_idx = content.find(end_tag, start_idx) + len(end_tag)
    
    if start_idx != -1 and end_idx != -1:
        new_content = content[:start_idx] + new_loop + content[end_idx:]
        with open('app/templates/components/timeline.html', 'w', encoding='utf-8') as f:
            f.write(new_content)
        print("Updated timeline.html with new fixes!")
    else:
        print("Could not find loop to replace!")

update_timeline_again()
