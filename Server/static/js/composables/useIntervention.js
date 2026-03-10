import { ref } from 'vue';

export function useIntervention(showToast, monitorData) {
    const ivTab = ref('memory');
    const memoryList = ref([]);
    const newMemoryContent = ref('');
    const editableAffinity = ref({});
    const toolList = ref([]);
    const selectedTool = ref('');
    const toolArgsStr = ref('{\n  "target": "林飒"\n}');

    const interventionStats = ref({
        hygiene: 100,
        reputation: 50,
        san: 100,
        money: 1500,
        gpa: 3.0
    });

    const openIntervention = () => {
        fetchMemories();
        fetchTools();
        if (monitorData.value && monitorData.value.affinity) {
            editableAffinity.value = JSON.parse(JSON.stringify(monitorData.value.affinity));
        }

        // 可选：打开干预面板时，自动同步当前监视器里的最新主角数据
        if (monitorData.value) {
            if (monitorData.value.san !== undefined) interventionStats.value.san = monitorData.value.san;
            if (monitorData.value.money !== undefined) interventionStats.value.money = monitorData.value.money;
            if (monitorData.value.gpa !== undefined) interventionStats.value.gpa = monitorData.value.gpa;
            // 注意：监视器里如果没有 hygiene 和 reputation，会保持上面的默认值
        }
    };

    const fetchMemories = async () => {
        try {
            const res = await fetch('/api/intervention/memory');
            const data = await res.json();
            if (data.status === 'success') memoryList.value = data.data;
        } catch (e) { showToast("记忆抓取失败"); }
    };

    const deleteMemory = async (id) => {
        try {
            await fetch(`/api/intervention/memory/${id}`, { method: 'DELETE' });
            showToast("记忆已抹除");
            fetchMemories();
        } catch (e) { showToast("操作失败"); }
    };

    const injectMemory = async () => {
        if (!newMemoryContent.value) return;
        try {
            const res = await fetch('/api/intervention/memory', {
                method: 'POST', headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ content: newMemoryContent.value })
            });
            if ((await res.json()).status === 'success') {
                showToast("思想钢印注入成功");
                newMemoryContent.value = '';
                fetchMemories();
            }
        } catch (e) { showToast("注入失败"); }
    };

    const fetchTools = async () => {
        try {
            const res = await fetch('/api/intervention/tools');
            const data = await res.json();
            if (data.status === 'success') toolList.value = data.data;
        } catch (e) { showToast("工具列表抓取失败"); }
    };

    const triggerGodTool = async () => {
        if (!selectedTool.value) return;
        let args = {};
        try { args = JSON.parse(toolArgsStr.value); } catch (e) { return showToast("JSON 解析失败，请检查格式"); }
        try {
            const res = await fetch('/api/intervention/tool', {
                method: 'POST', headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ tool_name: selectedTool.value, args })
            });
            if ((await res.json()).status === 'success') {
                showToast(`已强制执行工具: ${selectedTool.value}`);
            }
        } catch (e) { showToast("越权指令执行失败"); }
    };

    const applyAffinity = async (charName) => {
        try {
            const res = await fetch('/api/intervention/affinity', {
                method: 'POST', headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ char_name: charName, value: editableAffinity.value[charName] })
            });
            if ((await res.json()).status === 'success') showToast(`${charName} 好感度已被篡改`);
        } catch (e) { showToast("情感锚点篡改失败"); }
    };

    // ==========================================
    // 🌟 新增：提交主角属性修改的核心方法
    // ==========================================
    const applyStats = async () => {
        try {
            const response = await fetch('/api/admin/intervention', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(interventionStats.value)
            });
            const result = await response.json();
            if (result.success) {
                showToast('🌟 主角基础属性覆写成功！');
            } else {
                showToast('❌ 覆写失败: ' + (result.error || '未知错误'));
            }
        } catch (err) {
            console.error(err);
            showToast('❌ 网络错误，请检查后端状态');
        }
    };

    return {
        ivTab, memoryList, newMemoryContent, editableAffinity, toolList, selectedTool, toolArgsStr,
        interventionStats,
        openIntervention, fetchMemories, deleteMemory, injectMemory, fetchTools, triggerGodTool, applyAffinity,
        applyStats
    };
}