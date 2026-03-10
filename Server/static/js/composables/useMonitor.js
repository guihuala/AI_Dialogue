import { ref } from 'vue';

export function useMonitor(showToast) {
    const resultViewMode = ref('story');
    const monitor = ref({ san: 100, money: 2000, gpa: 4.0, chapter: 1, turn: 0, evt_id: '', last_action: '无', affinity: '{}', display_text: '', sys_prompt: '', user_prompt: '', raw_json: '', memory: '', relationships: '', tools: '' });

    const fetchMonitorData = async () => {
        try {
            const res = await fetch('/api/game/monitor');
            const data = await res.json();
            if (data.status === 'success' && data.data.response) {
                const rsp = data.data.response;
                const req = data.data.request || {};
                monitor.value = {
                    san: rsp.san || 100, money: rsp.money || 2000, gpa: rsp.gpa || 4.0, chapter: rsp.chapter || 1, turn: rsp.turn || 0,
                    evt_id: rsp.current_evt_id || '', last_action: req.choice || '无',
                    affinity: JSON.stringify(rsp.affinity || {}, null, 2),
                    display_text: `【事件回传】\n${rsp.narrator_transition || ''}\n\n${rsp.display_text || ''}`,
                    sys_prompt: rsp.sys_prompt || '', user_prompt: rsp.user_prompt || '', raw_json: JSON.stringify(rsp, null, 2),
                    memory: rsp.memory || '', relationships: rsp.relationships || '', tools: rsp.tools || ''
                };
            }
        } catch (e) { }
    };
    return { resultViewMode, monitor, fetchMonitorData };
}