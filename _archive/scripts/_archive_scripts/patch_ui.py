import re

def patch_timeline_ui():
    with open('app/templates/components/timeline.html', 'r', encoding='utf-8') as f:
        content = f.read()

    # We need to replace the entire section from 
    # <h4 class="text-xs font-bold text-slate-500 uppercase tracking-wider mb-6">Omnichannel Asset Impact Matrix</h4>
    # to just before the row rendering.
    
    # Wait, the best way to do this is to use `replace` on specific HTML blocks.
    
    # 1. Add Tabs and x-data
    old_header = '<h4 class="text-xs font-bold text-slate-500 uppercase tracking-wider mb-6">Omnichannel Asset Impact Matrix</h4>\\n            <div class="space-y-4">'
    
    new_header = """<div x-data="{ currentTab: 'Web' }">
                <div class="flex flex-col md:flex-row justify-between items-start md:items-center mb-6 border-b border-dark-700 pb-2">
                    <h4 class="text-xs font-bold text-slate-500 uppercase tracking-wider mb-4 md:mb-0">Omnichannel Asset Impact Matrix</h4>
                    
                    <!-- Tabs -->
                    <div class="flex gap-6">
                        <button @click="currentTab = 'Web'" :class="currentTab === 'Web' ? 'border-slate-300 text-slate-200' : 'border-transparent text-slate-500 hover:text-slate-400'" class="border-b-2 pb-1 text-sm font-bold uppercase tracking-wider transition">Web Pages</button>
                        <button @click="currentTab = 'LinkedIn'" :class="currentTab === 'LinkedIn' ? 'border-slate-300 text-slate-200' : 'border-transparent text-slate-500 hover:text-slate-400'" class="border-b-2 pb-1 text-sm font-bold uppercase tracking-wider transition">Social Ads</button>
                        <button @click="currentTab = 'Email'" :class="currentTab === 'Email' ? 'border-slate-300 text-slate-200' : 'border-transparent text-slate-500 hover:text-slate-400'" class="border-b-2 pb-1 text-sm font-bold uppercase tracking-wider transition">Email</button>
                    </div>
                </div>
                
                <div class="space-y-4">"""
                
    content = content.replace(old_header, new_header)

    # 2. Modify the Row Container
    # Find the row container: <div class="relative bg-dark-800/40 border-l-4 {% if m.type == 'Web' %}border-l-fuchsia-500{% elif m.type == 'LinkedIn' %}border-l-brand-500{% else %}border-l-indigo-500{% endif %} rounded-r-xl rounded-l-sm p-5 hover:bg-dark-800/60 transition shadow-[0_4px_20px_rgba(0,0,0,0.2)] overflow-hidden group flex flex-col justify-between"
    
    old_row_div = """<div class="relative bg-dark-800/40 border-l-4 {% if m.type == 'Web' %}border-l-fuchsia-500{% elif m.type == 'LinkedIn' %}border-l-brand-500{% else %}border-l-indigo-500{% endif %} rounded-r-xl rounded-l-sm p-5 hover:bg-dark-800/60 transition shadow-[0_4px_20px_rgba(0,0,0,0.2)] overflow-hidden group flex flex-col justify-between\""""
    new_row_div = """<div x-show="currentTab === '{{ m.type }}'" x-transition:enter="transition ease-out duration-200" x-transition:enter-start="opacity-0 translate-y-2" x-transition:enter-end="opacity-100 translate-y-0" style="display: none;" class="relative bg-dark-800/40 border-l-4 border-l-dark-700 rounded-xl p-5 hover:bg-dark-800/60 transition shadow-[0_4px_20px_rgba(0,0,0,0.2)] overflow-hidden group flex flex-col justify-between\""""
    
    content = content.replace(old_row_div, new_row_div)
    
    # 3. Fix the Sparkline Chart logic
    # Find the initSparkline() method
    
    old_init = """                        initSparkline() {
                            if (!this.$refs.canvas || this.sparkline.length === 0) return;
                            const ctx = this.$refs.canvas.getContext('2d');
                            new Chart(ctx, {"""
                            
    new_init = """                        chartInstance: null,
                        initSparkline() {
                            this.$watch('currentTab', (val) => {
                                if (val === '{{ m.type }}') {
                                    this.$nextTick(() => { this.renderChart(); });
                                }
                            });
                            // Initial render if active
                            if (this.currentTab === '{{ m.type }}') {
                                this.$nextTick(() => { this.renderChart(); });
                            }
                        },
                        renderChart() {
                            if (!this.$refs.canvas || this.sparkline.length === 0) return;
                            if (this.chartInstance) { this.chartInstance.destroy(); }
                            const ctx = this.$refs.canvas.getContext('2d');
                            this.chartInstance = new Chart(ctx, {"""
    
    content = content.replace(old_init, new_init)
    
    # 4. Close the x-data div at the end of the loop
    # Find:
    #                 </div>
    #             {% endfor %}
    #         </div>
    #     </div>
    # </div>
    # <!-- END OF MATRIX -->
    
    content = content.replace("{% endfor %}\\n            </div>\\n        </div>", "{% endfor %}\\n            </div>\\n            </div>\\n        </div>")

    with open('app/templates/components/timeline.html', 'w', encoding='utf-8') as f:
        f.write(content)
        
    print("UI Overhaul complete.")

patch_timeline_ui()
