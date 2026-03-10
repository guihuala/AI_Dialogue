import { ref } from 'vue';

export function useIntervention(showToast, monitorRef) {
    const ivTab = ref('memory');
    const memoryList = ref([]);
    const newMemoryContent = ref('');
    const editableAffinity = ref({});
    const toolList = ref([]);
    const selectedTool = ref('');
    const toolArgsStr = ref('{\n  "author": "测试账户",\n  "content": "测试内容"\n}');

    const openIntervention = () => {
        fetchMemories();
        fetchTools();
        try {
            const affObj = typeof monitorRef.value.affinity === 'string' ? JSON.parse(monitorRef.value.affinity) : monitorRef.value.affinity;
            editableAffinity.value = { ...affObj };
        } catch (e) { editableAffinity.value = {}; }
    };

    const fetchMemories = async () => {
        try {
            const res = await fetch('/api/intervention/memory');
            const data = await res.json();
            if (data.status === 'success') memoryList.value = data.data;
        } catch (e) { }
    };

    const injectMemory = async () => {
        if (!newMemoryContent.value) return showToast("执行拒绝：载荷不可为空");
        try {
            const res = await fetch('/api/intervention/memory', {
                method: 'POST', headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ content: newMemoryContent.value })
            });
            const data = await res.json();
            if (data.status === 'success') {
                showToast(data.message);
                newMemoryContent.value = '';
                fetchMemories();
            }
        } catch (e) { showToast("接口异常"); }
    };

    const deleteMemory = async (id) => {
        try {
            await fetch(`/api/intervention/memory/${id}`, { method: 'DELETE' });
            fetchMemories();
        } catch (e) { }
    };

    const applyAffinity = async (charName) => {
        try {
            const res = await fetch('/api/intervention/affinity', {
                method: 'POST', headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ char_name: charName, value: editableAffinity.value[charName] })
            });
            if ((await res.json()).status === 'success') showToast(`已强制覆写 ${charName} 的好感锚点`);
        } catch (e) { showToast("覆写失败"); }
    };

    const fetchTools = async () => {
        try {
            const res = await fetch('/api/intervention/tools');
            const data = await res.json();
            if (data.status === 'success') toolList.value = data.data;
        } catch (e) { }
    };

    const triggerGodTool = async () => {
        let parsedArgs = {};
        try { parsedArgs = JSON.parse(toolArgsStr.value); } catch (e) { return showToast("执行拒绝：JSON 格式不合法"); }
        try {
            const res = await fetch('/api/intervention/tool', {
                method: 'POST', headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ tool_name: selectedTool.value, args: parsedArgs })
            });
            const data = await res.json();
            if (data.status === 'success') showToast("指令强制执行完毕，请回监视器查看结果！");
        } catch (e) { showToast("指令发送失败"); }
    };

    return { ivTab, memoryList, newMemoryContent, editableAffinity, toolList, selectedTool, toolArgsStr, openIntervention, deleteMemory, injectMemory, applyAffinity, triggerGodTool };
}