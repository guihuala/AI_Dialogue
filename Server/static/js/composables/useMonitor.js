// useMonitor.js
import { ref } from 'vue';

export function useMonitor(showToast) {
    const resultViewMode = ref('story');
    // 初始化时包含所有 HTML 引用的字段
    const monitor = ref({
        san: 100, money: 2000, gpa: 4.0,
        hygiene: 100, reputation: 100, // 新增
        chapter: 1, turn: 0,
        reflection_progress: 0, reflection_logs: [], // 新增
        evt_id: '', last_action: '无', affinity: '{}',
        display_text: '', sys_prompt: '', user_prompt: '',
        raw_json: '', memory: '', relationships: '', tools: ''
    });

    const fetchMonitorData = async () => {
        try {
            const res = await fetch('/api/game/monitor');
            const data = await res.json();

            if (data.status === 'success') {
                // 注意这里是 engine_stats (蛇形)，对应 app.py
                const eStats = data.engine_stats || { event_completion_count: 0 };

                if (data.data && data.data.response) {
                    const rsp = data.data.response;
                    const req = data.data.request || {};

                    // 覆写所有字段
                    monitor.value = {
                        san: rsp.san ?? 100,
                        money: rsp.money ?? 2000,
                        gpa: rsp.gpa ?? 4.0,
                        hygiene: rsp.hygiene ?? 100,      // 映射新字段
                        reputation: rsp.reputation ?? 100, // 映射新字段
                        chapter: rsp.chapter ?? 1,
                        turn: rsp.turn ?? 0,
                        reflection_progress: eStats.event_completion_count || 0, // 映射进度
                        reflection_logs: rsp.reflection_logs || [],              // 映射日志
                        evt_id: rsp.current_evt_id || '',
                        last_action: req.choice || '无',
                        affinity: JSON.stringify(rsp.affinity || {}, null, 2),
                        display_text: `【事件回传】\n${rsp.narrator_transition || ''}\n\n${rsp.display_text || ''}`,
                        sys_prompt: rsp.sys_prompt || '',
                        user_prompt: rsp.user_prompt || '',
                        raw_json: JSON.stringify(rsp, null, 2),
                        memory: rsp.memory || '',
                        relationships: rsp.relationships || '',
                        tools: rsp.tools || ''
                    };
                }
            }
        } catch (e) {
            console.error("Monitor fetch error:", e);
        }
    };
    return { resultViewMode, monitor, fetchMonitorData };
}