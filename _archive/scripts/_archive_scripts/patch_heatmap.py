def update_heatmap():
    with open('app/templates/components/mod_activity_pulse.html', 'r', encoding='utf-8') as f:
        content = f.read()

    start_marker = "// Find the date range"
    end_marker = "const container = document.getElementById('heatmap-container');"

    start_idx = content.find(start_marker)
    end_idx = content.find(end_marker)

    if start_idx == -1 or end_idx == -1:
        print("Markers not found!")
        return

    new_js = """// Dynamically determine the campaign date boundaries
                            let startD = new Date('2026-01-01');
                            let endD = new Date('2026-12-31');
                            
                            if (dates.length > 0) {
                                startD = new Date(dates[0]);
                                endD = new Date(dates[dates.length-1]);
                            }
                            
                            // If duration is less than 3 months, pad the endD so the graph doesn't look completely empty
                            let monthDiff = (endD.getFullYear() - startD.getFullYear()) * 12 + (endD.getMonth() - startD.getMonth());
                            if (monthDiff < 3) {
                                endD = new Date(startD);
                                endD.setMonth(startD.getMonth() + 3);
                            }
                            // Limit to 12 months max to avoid horizontal overflow
                            if (monthDiff > 12) {
                                startD = new Date(endD);
                                startD.setMonth(endD.getMonth() - 11);
                            }
                            
                            const colors = ['bg-dark-800', 'bg-[#0e4429]', 'bg-[#006d32]', 'bg-[#26a641]', 'bg-[#39d353]'];
                            const months = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'];
                            
                            let html = '';
                            let currD = new Date(startD.getFullYear(), startD.getMonth(), 1);
                            let finalD = new Date(endD.getFullYear(), endD.getMonth(), 1);
                            
                            while(currD <= finalD) {
                                let m = currD.getMonth();
                                let y = currD.getFullYear();
                                
                                html += '<div class="flex flex-col gap-2">';
                                html += `<div class="text-[11px] text-slate-400 font-medium text-left pl-1">${months[m]} ${y !== startD.getFullYear() ? y : ''}</div>`;
                                html += '<div class="flex gap-[3px]">';
                                
                                let days = new Date(y, m + 1, 0).getDate();
                                let startDay = new Date(y, m, 1).getDay();
                                startDay = startDay === 0 ? 6 : startDay - 1; // 0=Mon, 6=Sun
                                
                                let numWeeks = Math.ceil((days + startDay) / 7);
                                let dayCounter = 0;
                                let currentDayOfWeek = startDay;
                                
                                for(let w=0; w<numWeeks; w++) {
                                    html += '<div class="flex flex-col gap-[3px]">';
                                    for(let row=0; row<7; row++) {
                                        let isActualDay = false;
                                        if (w === 0 && row < startDay) {
                                            isActualDay = false;
                                        } else if (dayCounter >= days) {
                                            isActualDay = false;
                                        } else {
                                            isActualDay = true;
                                            dayCounter++;
                                            currentDayOfWeek = (currentDayOfWeek + 1) % 7;
                                        }
                                        
                                        if (isActualDay) {
                                            const monthStr = (m + 1).toString().padStart(2, '0');
                                            const dayStr = dayCounter.toString().padStart(2, '0');
                                            const dateKey = `${y}-${monthStr}-${dayStr}`;
                                            
                                            const interactions = heatmapData[dateKey] || 0;
                                            
                                            let intensity = 0;
                                            if (interactions > 50) intensity = 4;
                                            else if (interactions > 20) intensity = 3;
                                            else if (interactions > 5) intensity = 2;
                                            else if (interactions > 0) intensity = 1;
                                            
                                            let color = colors[intensity];
                                            let border = intensity === 0 ? 'border border-dark-700/50' : '';
                                            
                                            let tooltip = `${months[m]} ${dayCounter}, ${y}: ${interactions} interactions`;
                                            if (interactions > 20) tooltip += ` \\n🔥 High Engagement! Driven by asset releases.`;
                                            
                                            html += `<div title="${tooltip}" class="w-4 h-4 ${color} ${border} rounded-[3px] transition-colors hover:ring-1 hover:ring-slate-300 cursor-pointer"></div>`;
                                        } else {
                                            html += `<div class="w-4 h-4 rounded-[3px]"></div>`;
                                        }
                                    }
                                    html += '</div>';
                                }
                                html += '</div></div>';
                                
                                currD.setMonth(currD.getMonth() + 1);
                            }
                            
                            """

    content = content[:start_idx] + new_js + content[end_idx:]

    with open('app/templates/components/mod_activity_pulse.html', 'w', encoding='utf-8') as f:
        f.write(content)

    print('Updated mod_activity_pulse.html')

update_heatmap()
