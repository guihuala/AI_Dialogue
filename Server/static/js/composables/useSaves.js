import { ref } from 'vue';

export function useSaves(showToast) {
    const saveSlots = ref([]);
    const saveDetailData = ref('');
    const currentViewSlotId = ref(0);

    const openSaves = () => { fetchSaves(); };

    const fetchSaves = async () => {
        try {
            const res = await fetch('/api/game/saves_info');
            const data = await res.json();
            if (data.status === 'success') saveSlots.value = data.slots;
        } catch (e) { showToast("无法获取存档列表"); }
    };

    const viewSave = async (slotId) => {
        try {
            const res = await fetch(`/api/game/load/${slotId}`);
            const data = await res.json();
            if (data.status === 'success') {
                currentViewSlotId.value = slotId;
                saveDetailData.value = JSON.stringify(data.data, null, 2);
            }
        } catch (e) { showToast("读取底层数据失败"); }
    };

    const deleteSave = async (slotId) => {
        if (!confirm(`⚠️ 警告：确定要彻底清空槽位 ${slotId} 吗？玩家将会丢失此记录。`)) return;
        try {
            const res = await fetch(`/api/game/save/${slotId}`, { method: 'DELETE' });
            const data = await res.json();
            if (data.status === 'success') {
                showToast(`已强制清空槽位 ${slotId}`);
                if (currentViewSlotId.value === slotId) saveDetailData.value = '';
                fetchSaves();
            }
        } catch (e) { showToast("清空失败"); }
    };

    return { saveSlots, saveDetailData, currentViewSlotId, openSaves, fetchSaves, viewSave, deleteSave };
}