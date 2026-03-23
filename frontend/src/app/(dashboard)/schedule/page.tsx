"use client";

import { useEffect, useState } from "react";
import { GlassCard } from "@/components/GlassCard";
import { api } from "@/lib/api";
import Link from "next/link";

const colorMap: Record<string, string> = {
  queued: "text-on-surface-variant bg-surface-container",
  scheduled: "text-secondary bg-secondary-container/20",
  in_progress: "text-primary bg-primary-container/20",
  completed: "text-green-500 bg-green-500/10",
  published: "text-green-500 bg-green-500/10",
  failed: "text-error bg-error/10",
};

export default function GlobalScheduleView() {
  const [topics, setTopics] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);

  // For a simple custom calendar view, we will group by YYYY-MM
  const [currentMonth, setCurrentMonth] = useState(() => {
    const d = new Date();
    return new Date(d.getFullYear(), d.getMonth(), 1);
  });

  useEffect(() => {
    async function loadSchedule() {
      try {
        const data = await api.calendar.list();
        setTopics(data || []);
      } catch (err) {
        console.error("Failed to load global schedule:", err);
      } finally {
        setLoading(false);
      }
    }
    loadSchedule();
  }, []);

  const getDaysInMonth = (date: Date) => {
    return new Date(date.getFullYear(), date.getMonth() + 1, 0).getDate();
  };

  const getFirstDayOfMonth = (date: Date) => {
    return new Date(date.getFullYear(), date.getMonth(), 1).getDay();
  };

  const changeMonth = (offset: number) => {
    setCurrentMonth(new Date(currentMonth.getFullYear(), currentMonth.getMonth() + offset, 1));
  };

  if (loading) {
    return (
      <div className="flex justify-center p-12">
        <span className="material-symbols-outlined animate-spin text-primary text-4xl">refresh</span>
      </div>
    );
  }

  const daysInMonth = getDaysInMonth(currentMonth);
  const firstDay = getFirstDayOfMonth(currentMonth); // 0 = Sun, 1 = Mon...
  const blanks = Array.from({ length: firstDay }).map((_, i) => i);
  const days = Array.from({ length: daysInMonth }).map((_, i) => i + 1);

  const monthName = currentMonth.toLocaleString("default", { month: "long", year: "numeric" });

  const isToday = (day: number) => {
    const today = new Date();
    return day === today.getDate() && currentMonth.getMonth() === today.getMonth() && currentMonth.getFullYear() === today.getFullYear();
  };

  return (
    <div className="space-y-8">
      <header className="flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div>
          <h1 className="text-4xl font-display font-medium tracking-tight mb-2">Content Schedule</h1>
          <p className="text-on-surface-variant text-lg max-w-2xl leading-relaxed">
            Global view of all scheduled publications across your projects.
          </p>
        </div>
        <div className="flex space-x-2">
           <button 
             onClick={() => changeMonth(-1)}
             className="w-10 h-10 rounded-full bg-surface-container hover:bg-surface-container-high flex items-center justify-center transition-colors"
           >
             <span className="material-symbols-outlined">chevron_left</span>
           </button>
           <div className="px-6 py-2 bg-surface-container-low rounded-full font-bold flex items-center justify-center min-w-[160px]">
             {monthName}
           </div>
           <button 
             onClick={() => changeMonth(1)}
             className="w-10 h-10 rounded-full bg-surface-container hover:bg-surface-container-high flex items-center justify-center transition-colors"
           >
             <span className="material-symbols-outlined">chevron_right</span>
           </button>
        </div>
      </header>
      
      <GlassCard className="p-6">
         <div className="grid grid-cols-7 gap-px bg-surface-container-high/30 rounded-xl overflow-hidden border border-surface-container-high/30">
            {["Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"].map(day => (
              <div key={day} className="bg-surface-container-lowest py-3 text-center text-xs font-semibold uppercase tracking-wider text-on-surface-variant">
                 {day}
              </div>
            ))}
            
            {blanks.map(blank => (
              <div key={`blank-${blank}`} className="bg-surface-container-lowest/50 min-h-[120px] p-2"></div>
            ))}
            
            {days.map(day => {
               const cellDateStr = `${currentMonth.getFullYear()}-${String(currentMonth.getMonth() + 1).padStart(2, '0')}-${String(day).padStart(2, '0')}`;
               const dayTopics = topics.filter(t => t.scheduled_date === cellDateStr);
               
               return (
                 <div key={`day-${day}`} className={`bg-surface-container-lowest min-h-[120px] p-2 border-t border-l border-surface-container-high/30 transition-colors hover:bg-surface-container/20 group`}>
                    <div className="flex justify-between items-start mb-2">
                       <span className={`w-7 h-7 flex items-center justify-center rounded-full text-sm font-medium ${isToday(day) ? 'bg-primary text-on-primary' : 'text-on-surface-variant group-hover:text-on-surface'}`}>
                         {day}
                       </span>
                    </div>
                    
                    <div className="space-y-1">
                      {dayTopics.map((topic, i) => (
                        <Link href={`/projects/${topic.project_id}/topics/${topic.id}`} key={`${topic.id}-${i}`}>
                           <div className={`text-[10px] p-1.5 rounded-md truncate cursor-pointer transition-all hover:brightness-110 mb-1 ${colorMap[topic.status] || colorMap.queued}`}>
                              <span className="font-semibold">{topic.project_name}</span>: {topic.title}
                           </div>
                        </Link>
                      ))}
                    </div>
                 </div>
               );
            })}
         </div>
      </GlassCard>

      <div className="flex flex-col sm:flex-row items-center justify-center gap-4 text-xs font-medium uppercase tracking-wider mt-8 border-t border-surface-container-high/30 pt-6">
         {Object.entries({
           queued: "Queued",
           scheduled: "Scheduled",
           in_progress: "Generating",
           completed: "Completed"
         }).map(([status, label]) => (
            <div key={status} className="flex items-center text-on-surface-variant">
               <div className={`w-3 h-3 rounded-full mr-2 ${colorMap[status]?.split(' ')[1] || 'bg-surface-container'}`}></div>
               {label}
            </div>
         ))}
      </div>
    </div>
  );
}
